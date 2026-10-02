"""
optimization.py: Uses convex optimization (CVXPY) to determine the optimal charging and V2G discharging schedule for the EV fleet.
Minimizes total electricity cost by charging when Day-Ahead Market (DAM) prices are low and discharging (V2G) when prices are high,
while taking into account per-EV battery/charger limits and a fleet-wide transformer power limit.
Author: Dimitrios Poulos
"""



import numpy as np
import pandas as pd
import cvxpy as cp



HOURS = 24
FLEET_TRAFO_LIMIT_KW = 70    # Fleet-wide power limit (kW) of transformer, calibrated with AC power flow (see grid_simulation.py) so that residential transformer loading stays below 100


def generate_availability_table(ev_fleet_df):
    """
    Generates a binary matrix (EV x Hour) indicating when each EV is plugged in.
    Returns:
            availability_table (np.ndarray): A 2D array (binary) representing plug-in status per EV per hour.
    """
    evs_number = len(ev_fleet_df)
    availability_table = np.zeros((evs_number, HOURS))
    
    for index, row in ev_fleet_df.iterrows():
        ev_id = int(row['ev_id'])
        arrival_hour = int(row['arrival_hour'])
        departure_hour = int(row['departure_hour']) % 24    # Modulo 24 maps any hour strictly to the 0-23 clock format

        for hour in range(HOURS):
            if arrival_hour < departure_hour:
                # Daytime charging
                if arrival_hour <= hour and hour < departure_hour:
                    availability_table[ev_id, hour] = 1
            else:
                # Nighttime charging
                if hour >= arrival_hour or hour < departure_hour:    # The 'or' condition handles overnight charging across midnight
                    availability_table[ev_id, hour] = 1

    return availability_table



def get_hour_order(arrival_hour):
    """
    Returns the hours 0-23 reordered to start from arrival_hour, e.g. for arrival_hour = 18:00: [18, 19, ..., 23, 0, 1, ..., 17].
    This sequence must be done in order for charging to start from the arrival hour and not from the hour 0
    """
    return list(range(arrival_hour, HOURS)) + list(range(0, arrival_hour))



def charging_optimization(ev_fleet_df, availability_table, prices):
    """
    Executes the linear programming optimization to find the lowest-cost charging/discharging schedule.
    Returns:
        kw_charge (np.ndarray): 2D array of charging power (kW) per EV per hour.
        kw_discharge (np.ndarray): 2D array of V2G discharging power (kW) per EV per hour.
        soc (np.ndarray): 2D array of State of Charge progression.
        total_cost (float): The minimized total cost in EUR.
    """
    evs_number = len(ev_fleet_df)

    # Definition of optimization variables
    kw_charge = cp.Variable((evs_number, HOURS), nonneg=True)
    kw_discharge = cp.Variable((evs_number, HOURS), nonneg=True)
    soc = cp.Variable((evs_number, HOURS + 1))    # SoC has HOURS + 1 steps to account for the initial state (t=0) plus 24 hourly transitions

    constraints = []

    for index, row in ev_fleet_df.iterrows():
        ev_id = int(row['ev_id'])
        battery_capacity = row['battery_capacity']
        max_power = row['max_power']
        current_soc = row['initial_soc']
        target_soc = row['target_soc']
        arrival_hour = int(row['arrival_hour'])
        departure_hour = int(row['departure_hour']) % 24

        hour_order = get_hour_order(arrival_hour)

        constraints.append(soc[ev_id, 0] == current_soc)    # Initial State of Charge Constraint

        for i, hour in enumerate(hour_order):
            if availability_table[ev_id, hour] == 1:
                # Maximum Charger Power Constraints (when plugged in)
                constraints.append(kw_charge[ev_id, hour] <= max_power)
                constraints.append(kw_discharge[ev_id, hour] <= max_power)
            else:
                # Isolation Constraints (when not plugged in, power exchange is exactly 0)
                constraints.append(kw_charge[ev_id, hour] == 0)
                constraints.append(kw_discharge[ev_id, hour] == 0)

            # Battery SoC Evolution
            constraints.append(soc[ev_id, i + 1] == soc[ev_id, i] + (kw_charge[ev_id, hour] - kw_discharge[ev_id, hour]) / battery_capacity)    # Next SoC = Current SoC + Net Energy / Capacity

        # Battery Health Limits (SoC must be between 10% and 100% to protect battery lifespan)
        constraints.append(soc[ev_id, :] >= 0.1)
        constraints.append(soc[ev_id, :] <= 1)

        # Target SoC upon Departure constraint
        if departure_hour >= 0:
            departure_wrapped = departure_hour
        else:
            departure_wrapped = departure_hour + 24
        departure_i = hour_order.index(departure_wrapped)    # Locates the departure time step in hour_order in order to apply the target SoC constraint at that exact moment
        constraints.append(soc[ev_id, departure_i] >= target_soc)

    # Sum of all fleet net power must not exceed transformer limits (Constraint for grid)
    total_power_per_hour = cp.sum(kw_charge - kw_discharge, axis=0)
    constraints.append(total_power_per_hour <= FLEET_TRAFO_LIMIT_KW)
    constraints.append(total_power_per_hour >= -FLEET_TRAFO_LIMIT_KW)

    total_cost = cp.sum(cp.multiply(total_power_per_hour, prices / 1000))    # Prices are EUR/MWh - power (kW) over a 1-hour step equals energy (kWh), so dividing by 1000 gives EUR


    objective = cp.Minimize(total_cost)    # Sets the objective of the optimization problem to minimize the total cost
    problem = cp.Problem(objective, constraints)    # Sets the complete optimization problem combining the objective and all the constraints
    print("Solving the optimization problem...")
    problem.solve(verbose=False)    # CVXPY selects an available solver automatically (verbose=False hides mathematical logs)
    # Checks if the solver successfully found a valid and optimal solution
    if problem.status not in ["infeasible", "unbounded"]:
        print("Optimization problem solved successfully.")
        return kw_charge.value, kw_discharge.value, soc.value, total_cost.value    # Returns the values extracted from the CVXPY variables
    else:
        print("Optimization problem is infeasible or unbounded.")
        return None, None, None, None



if __name__ == "__main__":
    ev_fleet_df = pd.read_csv('ev_fleet_data.csv')
    prices_df = pd.read_csv('dam_forecast.csv')
    prices = prices_df['predicted_price'].values
    availability_table = generate_availability_table(ev_fleet_df)
    print("Starting optimization...")
    kw_charge, kw_discharge, soc, total_cost = charging_optimization(ev_fleet_df, availability_table, prices)
    if kw_charge is not None:
        print(f"Total cost of charging: {total_cost:.2f} €")
        net_power = kw_charge - kw_discharge    # Calculation of net grid exchange (Positive = Charging, Negative = Discharging/V2G)
        optimized_charging_table_df = pd.DataFrame(
            net_power,
            index=[f"EV_{i}" for i in range(len(ev_fleet_df))],
            columns=[f"Hour_{h}" for h in range(HOURS)]
        )
        optimized_charging_table_df.to_csv('optimized_charging_table.csv', sep=';', index_label='EV_ID', float_format='%.2f')

        soc_table = np.zeros((len(ev_fleet_df), HOURS))
        for index, row in ev_fleet_df.iterrows():
            ev_id = int(row['ev_id'])
            arrival_hour = int(row['arrival_hour'])
            hour_order = get_hour_order(arrival_hour)
            for step, clock_hour in enumerate(hour_order):
                soc_table[ev_id, clock_hour] = soc[ev_id, step + 1]

        soc_df = pd.DataFrame(soc_table * 100, index=[f"EV_{i}" for i in range(len(ev_fleet_df))], columns=[f"Hour_{h}" for h in range(HOURS)])
        soc_df.to_csv('optimized_soc_table.csv', sep=';', index_label='EV_ID', float_format='%.1f')
        
        print("Optimization results saved successfully (.csv).")