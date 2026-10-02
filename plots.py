"""
plots.py: Visualizes the impact of the EV fleet on the residential grid (6-panel visual summary) and compares the uncontrolled (baseline) vs. optimized (V2G) charging scenarios.
Prerequisites: run baseline.py, optimization.py and grid_simulation.py first, so that baseline_charging_table.csv, optimized_charging_table.csv, optimized_soc_table.csv and grid_simulation_results.csv all exist.
Author: Dimitrios Poulos
"""



import pandas as pd
import numpy as np
import matplotlib.pyplot as plt



HOURS = 24
VOLTAGE_MIN_LIMIT_PU = 0.95     # Requirement for net: V >= 0.95 p.u.
TRAFO_LOADING_LIMIT_PERCENTAGE = 100
FLEET_MAX_POWER_LIMIT_KW = 70


def main():
    print("Plots are loading...")

    # Pre-computed data loading
    ev_fleet_df = pd.read_csv('ev_fleet_data.csv')
    baseline_charging_table = pd.read_csv('baseline_charging_table.csv', sep=';', index_col='EV_ID')
    optimized_charging_table = pd.read_csv('optimized_charging_table.csv', sep=';', index_col='EV_ID')
    prices_df = pd.read_csv('dam_forecast.csv')
    soc_df = pd.read_csv('optimized_soc_table.csv', sep=';', index_col='EV_ID')
    grid_simulation_results_df = pd.read_csv('grid_simulation_results.csv', sep=';')

    hours_cols = [f"Hour_{h}" for h in range(HOURS)]    # Column names ('Hour_0' to 'Hour_23') for DataFrame
    x_hours = np.arange(HOURS)    # Array [0, 1, ..., 23] for the x-axis of the plots

    prices = prices_df['predicted_price'].values

    # Total EV fleet power per hour (baseline and optimized scenarios)
    baseline_total_power_hourly = baseline_charging_table[hours_cols].sum()
    optimized_total_power_hourly = optimized_charging_table[hours_cols].sum()

    # Hourly costs
    baseline_total_cost_hourly = (baseline_total_power_hourly * prices) / 1000
    optimized_total_cost_hourly = (optimized_total_power_hourly * prices) / 1000

    # Cumulative costs
    baseline_cumulative_cost = baseline_total_cost_hourly.cumsum()
    optimized_cumulative_cost = optimized_total_cost_hourly.cumsum()

    # Grid impact (residential feeder)
    baseline_trafo_load = grid_simulation_results_df['Trafo_Baseline']
    optimized_trafo_load = grid_simulation_results_df['Trafo_Optimized']
    baseline_min_voltage = grid_simulation_results_df['Min_Voltage_Baseline']
    optimized_min_voltage = grid_simulation_results_df['Min_Voltage_Optimized']


    fig, axs = plt.subplots(3, 2, figsize=(15, 9), sharex=True)
    fig.suptitle('V2G System Analysis: Baseline vs Grid-Aware Optimized', fontsize=18, fontweight='bold', y=0.97)

    # Total charging and discharging power
    axs[0, 0].plot(x_hours, baseline_total_power_hourly.values, label='Baseline', color='red', linestyle='--')
    axs[0, 0].plot(x_hours, optimized_total_power_hourly.values, label='Optimized', color='green', linewidth=2.5)
    axs[0, 0].axhline(FLEET_MAX_POWER_LIMIT_KW, color='black', linestyle=':', label=f'Grid Limit ({FLEET_MAX_POWER_LIMIT_KW} kW)')
    axs[0, 0].axhline(-FLEET_MAX_POWER_LIMIT_KW, color='black', linestyle=':')
    axs[0, 0].axhline(0, color='gray', alpha=0.5)
    axs[0, 0].set_title('1. Total Charging/Discharging Power', fontweight='bold')
    axs[0, 0].set_ylabel('Power (kW)')
    axs[0, 0].legend()
    axs[0, 0].grid(True, alpha=0.3)

    # Cumulative charging cost
    axs[0, 1].plot(x_hours, baseline_cumulative_cost.values, label='Baseline Cost', color='red', linestyle='--')
    axs[0, 1].plot(x_hours, optimized_cumulative_cost.values, label='Optimized Cost', color='green', linewidth=2.5)
    axs[0, 1].set_title('2. Cumulative Charging Cost (EUR)', fontweight='bold')
    axs[0, 1].set_ylabel('Cost (EUR)')
    axs[0, 1].legend()
    axs[0, 1].grid(True, alpha=0.3)

    # Transformer loading (residential feeder)
    axs[1, 0].plot(x_hours, baseline_trafo_load, label='Baseline', color='red', linestyle='--')
    axs[1, 0].plot(x_hours, optimized_trafo_load, label='Optimized', color='green', linewidth=2)
    axs[1, 0].axhline(TRAFO_LOADING_LIMIT_PERCENTAGE, color='darkred', linestyle=':', label=f'Safety Limit ({TRAFO_LOADING_LIMIT_PERCENTAGE}%)')
    axs[1, 0].set_title('3. Transformer Loading (%)', fontweight='bold')
    axs[1, 0].set_ylabel('Loading (%)')
    axs[1, 0].legend()
    axs[1, 0].grid(True, alpha=0.3)

    # Minimum grid voltage (residential feeder)
    axs[1, 1].plot(x_hours, baseline_min_voltage, label='Baseline', color='red', linestyle='--')
    axs[1, 1].plot(x_hours, optimized_min_voltage, label='Optimized', color='green', linewidth=2)
    axs[1, 1].axhline(VOLTAGE_MIN_LIMIT_PU, color='darkred', linestyle=':', label=f'Project Limit ({VOLTAGE_MIN_LIMIT_PU} p.u.)')
    axs[1, 1].set_title('4. Minimum Grid Voltage (p.u.)', fontweight='bold')
    axs[1, 1].set_ylabel('Voltage (p.u.)')
    axs[1, 1].legend()
    axs[1, 1].grid(True, alpha=0.3)

    # Day-Ahead Market (DAM) Prices
    axs[2, 0].plot(x_hours, prices, color='blue', marker='d', markersize=4)
    axs[2, 0].set_title('5. Day-Ahead Market Prices (EUR/MWh)', fontweight='bold')
    axs[2, 0].set_xlabel('Hour (0-23)')
    axs[2, 0].set_ylabel('Price (EUR)')
    axs[2, 0].set_xticks(x_hours)
    axs[2, 0].grid(True, alpha=0.3)

    # State of Charge (SoC) for all EVs (for optimized charging scenario)
    soc_df = soc_df.replace('%', '', regex=True).astype(float)
    for ev_label in soc_df.index:
        axs[2, 1].plot(x_hours, soc_df.loc[ev_label, hours_cols], marker='.', linewidth=1.5, alpha=0.7, label=ev_label)
    axs[2, 1].axhline(10, color='red', linestyle=':', label='BMS Limit (10%)')
    axs[2, 1].set_title('6. State of Charge (SoC) - All 10 EVs', fontweight='bold')
    axs[2, 1].set_xlabel('Hour (0-23)')
    axs[2, 1].set_ylabel('SoC (%)')
    axs[2, 1].legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize='small')
    axs[2, 1].grid(True, alpha=0.3)


    plt.tight_layout()
    plt.subplots_adjust(right=0.90, top=0.90)
    plt.savefig('plots.png', dpi=300, bbox_inches='tight')
    print("Dashboard saved succesfully as 'plots.png'.")
    plt.show()


if __name__ == "__main__":
    main()
