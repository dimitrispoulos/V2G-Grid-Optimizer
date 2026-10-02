"""
grid_simulation.py: Evaluates the grid impact of the EV fleet using Pandapower,
simulates power flow on the CIGRE Low Voltage (LV) network for both the uncoordinated (baseline) and optimized (V2G) charging scenarios,extracting transformer loading and voltage profiles.
Author: Dimitrios Poulos
"""



import pandas as pd
import pandapower as pdp
import pandapower.networks as pn



HOURS = 24


def create_grid_network(ev_fleet_df):
    """
    Loads the CIGRE LV network and attaches EV nodes as loads.
    Initializes EVs with 0 MW active and reactive power.
    Returns:
            net (pandapowerNet): The LV grid network.
    """
    net = pn.create_cigre_network_lv()
    for index, row in ev_fleet_df.iterrows():
        ev_name = f"EV_{int(row['ev_id'])}"
        bus_id = int(row['bus'])
        pdp.create_load(net, bus=bus_id, p_mw=0.0, q_mvar=0.0, name=ev_name)    # Connects EV to the network bus with initial power set to 0
    return net



def simulate_grid_impact(net, charging_table):
    """
    Runs a 24-hour time-series power flow simulation.
    Updates EV active power hourly (MW) to simulate charging or V2G discharge and records the maximum transformer loading percentage along with the worst-case minimum bus voltage (p.u.) at every hour.
    Returns:
            trafo_loads (list of float): residential transformer loadings (%) per hour
            min_voltages (list of float): minimum residential bus voltages (p.u.) per hour.
    """
    trafo_loads = []
    min_voltages = []
    for hour in range(HOURS):
        hour_col = f"Hour_{hour}"
        for ev_name in charging_table.index:
            p_kw = charging_table.loc[ev_name, hour_col]
            mask = net.load.name == ev_name    # Finds the specific EV row in the Pandapower load table using a boolean mask
            net.load.loc[mask, 'p_mw'] = p_kw / 1000    # kW is converted to MW because Pandapower uses MW for standard load inputs
        pdp.runpp(net, numba=False)    # Runs simulation
        trafo_loads.append(net.res_trafo.loading_percent.iloc[0])    # Records the loading percentage specifically for the residential transformer (Trafo 0)
        min_voltages.append(net.res_bus.vm_pu.loc[range(2, 20)].min())    # Records the worst-case voltage strictly across the residential buses (Indices 2 to 19)
    return trafo_loads, min_voltages



if __name__ == "__main__":
    ev_fleet_df = pd.read_csv("ev_fleet_data.csv")
    baseline_df = pd.read_csv("baseline_charging_table.csv", sep=";", index_col="EV_ID")
    optimized_df = pd.read_csv("optimized_charging_table.csv", sep=";", index_col="EV_ID")

    # Uncontrolled Charging Simulation (Baseline)
    print("Running Baseline simulation...")
    net_baseline = create_grid_network(ev_fleet_df)
    trafo_baseline, min_voltage_baseline = simulate_grid_impact(net_baseline, baseline_df)

    # Optimized V2G Charging Simulation
    print("Running Optimized V2G simulation...")
    net_optimized = create_grid_network(ev_fleet_df)
    trafo_optimized, min_voltage_optimized = simulate_grid_impact(net_optimized, optimized_df)

    # Results for both scenarios
    print("\n--- SIMULATION RESULTS ---")
    grid_simulation_results_df = pd.DataFrame({"Hour": range(HOURS), "Trafo_Baseline": trafo_baseline, "Trafo_Optimized": trafo_optimized, "Min_Voltage_Baseline": min_voltage_baseline, "Min_Voltage_Optimized": min_voltage_optimized})
    grid_simulation_results_df.to_csv("grid_simulation_results.csv", index=False, sep=";")
    print(f"BASELINE  -> Peak Transformer Loading: {max(trafo_baseline):.2f}% | Minimum Voltage: {min(min_voltage_baseline):.4f} p.u.")
    print(f"OPTIMIZED -> Peak Transformer Loading: {max(trafo_optimized):.2f}% | Minimum Voltage: {min(min_voltage_optimized):.4f} p.u.")