"""
Project: V2G Grid Optimizer
Description: Runs the complete end-to-end V2G simulation pipeline. It computes an uncontrolled charging baseline, uses convex optimization (CVXPY) to minimize electricity costs via DAM price arbitrage and V2G discharging, validates the physical constraints on a CIGRE LV network using Pandapower, and generates comparative analytics and visual dashboards.
main.py: Runs the full V2G Grid Optimizer pipeline end-to-end:
baseline charging -> cvxpy optimization -> pandapower grid validation -> comparison table -> dashboard.
Prerequisites: ev_fleet_data.csv and dam_forecast.csv must already exist (see data_generation.py).
Author: Dimitrios Poulos
"""


import warnings
warnings.filterwarnings("ignore")

import pandas as pd
from tabulate import tabulate


import baseline
import optimization
import grid_simulation
import plots


HOURS = 24



def run_baseline_charging(ev_fleet_df, prices):
    """
    Runs the baseline charging scenario and saves its results to CSV.
    Returns:
            baseline_charging_table_df (pd.DataFrame): The charging schedule for the baseline scenario
            cost (float): The total calculated cost of the baseline charging scenario.
    """
    availability_table = baseline.generate_availability_table(ev_fleet_df)
    baseline_charging_table = baseline.simulate_simple_charging(ev_fleet_df, availability_table)
    baseline_cost = baseline.compute_cost(baseline_charging_table, prices)
    baseline_charging_table_df = pd.DataFrame(baseline_charging_table, index=[f"EV_{i}" for i in range(len(ev_fleet_df))], columns=[f"Hour_{h}" for h in range(HOURS)])
    baseline_charging_table_df.to_csv('baseline_charging_table.csv', index_label='EV_ID', float_format='%.2f', sep=';')
    return baseline_charging_table_df, baseline_cost



def run_optimized_charging(ev_fleet_df, prices):
    """
    Runs the optimized charging scenario and saves its results to CSV.
    It also records and saves the State of Charge (SoC)
    Returns:
        optimized_charging_table_df (pd.DataFrame): The net power schedule (charge/discharge) for the optimized scenario.
        cost (float): The minimized total cost achieved by the optimized charging schedule.
    """
    availability_table = optimization.generate_availability_table(ev_fleet_df)
    kw_charge, kw_discharge, soc, optimized_cost = optimization.charging_optimization(ev_fleet_df, availability_table, prices)
    net_power = kw_charge - kw_discharge
    optimized_charging_table_df = pd.DataFrame(
        net_power,
        index=[f"EV_{i}" for i in range(len(ev_fleet_df))],
        columns=[f"Hour_{h}" for h in range(HOURS)]
    )
    optimized_charging_table_df.to_csv('optimized_charging_table.csv', sep=';', index_label='EV_ID', float_format='%.2f')

    # Realigning the battery SoC to the actual 24-hour clock.
    soc_table = pd.DataFrame(0.0, index=range(len(ev_fleet_df)), columns=range(HOURS))
    for index, row in ev_fleet_df.iterrows():
        ev_id = int(row['ev_id'])
        arrival_hour = int(row['arrival_hour'])
        hour_order = optimization.get_hour_order(arrival_hour)
        for step, clock_hour in enumerate(hour_order):
            soc_table.loc[ev_id, clock_hour] = soc[ev_id, step + 1]
    
    soc_df = pd.DataFrame(soc_table.values * 100, index=[f"EV_{i}" for i in range(len(ev_fleet_df))], columns=[f"Hour_{h}" for h in range(HOURS)])
    soc_df.to_csv('optimized_soc_table.csv', sep=';', index_label='EV_ID', float_format='%.1f')
    return optimized_charging_table_df, optimized_cost



def run_grid_check(ev_fleet_df,charging_table):
    """
    Validates the charging table against the power flow simulation.
    Returns:
        trafo_loads (list of float): The transformer loading percentages during the simulation for each hour.
        min_voltages (list of float): The bus voltages (in p.u.) during the simulation for each hour.
    """
    net = grid_simulation.create_grid_network(ev_fleet_df)
    trafo_loads, min_voltages = grid_simulation.simulate_grid_impact(net, charging_table)
    return trafo_loads, min_voltages



def print_summary_table(baseline_cost, optimized_cost, baseline_max_trafo_loading, optimized_max_trafo_loading, baseline_min_voltage, optimized_min_voltage):
    """
    Prints the final comparison table (baseline vs optimized) to the terminal.
    """
    voltage_limit = 0.95
    loading_limit = 100.0

    rows = [
        ["Charging Cost (EUR)", f"{baseline_cost:.2f}", f"{optimized_cost:.2f}"],
        ["Max Transformer Loading (%)", f"{baseline_max_trafo_loading:.2f}", f"{optimized_max_trafo_loading:.2f}"],
        ["Min Grid Voltage (p.u.)", f"{baseline_min_voltage:.4f}", f"{optimized_min_voltage:.4f}"],
        ["Transformer loading <= 100% ?", "Yes" if baseline_max_trafo_loading <= loading_limit else "NO",
         "Yes" if optimized_max_trafo_loading <= loading_limit else "NO"],
        ["Voltage >= 0.95 p.u. ?", "Yes" if baseline_min_voltage >= voltage_limit else "NO",
         "Yes" if optimized_min_voltage >= voltage_limit else "NO"],
    ]

    print("\n" + "=" * 60)
    print("FINAL COMPARISON TABLE: Baseline vs Optimized (V2G)")
    print("=" * 60)
    print(tabulate(rows, headers=["Data", "Baseline (uncontrolled)", "Optimized (cvxpy)"], tablefmt="grid"))

    savings = baseline_cost - optimized_cost
    if baseline_cost != 0:
        savings_percentage = (savings / abs(baseline_cost)) * 100
    else:
        savings_percentage = 0
    print(f"\nCost Savings: {savings:.2f} EUR ({savings_percentage:.1f}%)")



if __name__ == "__main__":
    ev_fleet_df = pd.read_csv("ev_fleet_data.csv")
    prices = pd.read_csv("dam_forecast.csv")['predicted_price'].values

    print("[1/4] Baseline (uncontrolled charging)...")
    baseline_schedule_df, baseline_cost = run_baseline_charging(ev_fleet_df, prices)

    print("\n[2/4] Optimizer (cvxpy, price arbitrage + V2G)...")
    optimized_schedule_df, optimized_cost = run_optimized_charging(ev_fleet_df, prices)

    print("\n[3/4] Grid validation (pandapower, AC power flow)...")
    baseline_trafo_loads, baseline_min_voltages = run_grid_check(ev_fleet_df, baseline_schedule_df)
    optimized_trafo_loads, optimized_min_voltages = run_grid_check(ev_fleet_df, optimized_schedule_df)

    # Saves both scenarios' hourly series so plots.py can read them
    grid_simulation_results_df = pd.DataFrame({"Hour": range(HOURS), "Trafo_Baseline": baseline_trafo_loads, "Trafo_Optimized": optimized_trafo_loads, "Min_Voltage_Baseline": baseline_min_voltages, "Min_Voltage_Optimized": optimized_min_voltages})
    grid_simulation_results_df.to_csv("grid_simulation_results.csv", index=False, sep=";")

    print_summary_table(
        baseline_cost, optimized_cost,
        max(baseline_trafo_loads), max(optimized_trafo_loads),
        min(baseline_min_voltages), min(optimized_min_voltages),
    )

    print("\n[4/4] Generating Visual Dashboard...")
    plots.main()