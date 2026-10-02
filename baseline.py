"""
baseline.py: Simulates the uncontrolled (baseline) charging of the EV fleet.
In this scenario, EVs plug in and charge at maximum power immediately upon arrival until their target SoC is reached or run out of available hours. This scenario is used as the reference scenario against which the optimized scenario is compared.
Author: Dimitrios Poulos
"""



import numpy as np
import pandas as pd



HOURS = 24


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
        departure_hour = int(row['departure_hour']) % 24    # Convert next-day departure back to clock hour (e.g., 31 -> 07:00)

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


def simulate_simple_charging(ev_fleet_df, availability_table):
    """
    Simulates uncontrolled charging for every EV, starting at each EV's arrival hour.
    Returns:
            baseline_charging_table (np.ndarray): A 2D array containing the charging power (kW) for each EV per hour.
    """
    evs_number = len(ev_fleet_df)
    baseline_charging_table = np.zeros((evs_number, HOURS))

    for index, row in ev_fleet_df.iterrows():
        ev_id = int(row['ev_id'])
        battery_capacity_kwh = row['battery_capacity']
        max_power_kw = row['max_power']
        current_soc = row['initial_soc']
        target_soc = row['target_soc']
        arrival_hour = int(row['arrival_hour'])
        departure_hour = int(row['departure_hour']) - 24

        hour_order = get_hour_order(arrival_hour)

        for hour in hour_order:
            # Charging only while EV is plugged in and its SoC is below target
            if availability_table[ev_id, hour] == 1 and current_soc < target_soc:
                energy_needed_kwh = (target_soc - current_soc) * battery_capacity_kwh    # Energy needed (kWh) is equivalent to kW over a 1 hour step
                power_to_charge_kw = min(max_power_kw, energy_needed_kwh)    # Charging rate limit so the charger's capacity isn't exceeded
                baseline_charging_table[ev_id, hour] = power_to_charge_kw
                current_soc += power_to_charge_kw / battery_capacity_kwh    # Updates battery State of Charge based on nominal pack capacity

        if current_soc < target_soc:
            print(f"Warning: EV {ev_id} did not reach target SOC. Final SOC: {current_soc:.2f}")

    return baseline_charging_table


def compute_cost(baseline_charging_table, prices):
    """
    Computes total charging cost of all EVs in Euros.
    Prices are in EUR/MWh, power is in kW over 1-hour steps (= kWh), so they are divided by 1000 to convert EUR/MWh to EUR/kWh.
    Returns:
            total_cost (float): The total charging cost in EUR (float).
    """
    total_power_per_hour_kw = baseline_charging_table.sum(axis=0)
    total_cost = float(np.sum(total_power_per_hour_kw * prices / 1000))
    return total_cost



if __name__ == "__main__":
    ev_fleet_df = pd.read_csv("ev_fleet_data.csv")
    prices_df = pd.read_csv("dam_forecast.csv")
    prices = prices_df['predicted_price'].values
    availability_table = generate_availability_table(ev_fleet_df)
    print("Baseline simulation started...")
    baseline_charging_table = simulate_simple_charging(ev_fleet_df, availability_table)
    total_cost = compute_cost(baseline_charging_table, prices)

    print(f"Total cost of baseline charging: {total_cost:.2f} €")

    baseline_charging_df = pd.DataFrame(baseline_charging_table, index=[f"EV_{i}" for i in range(len(ev_fleet_df))], columns=[f"Hour_{i}" for i in range(HOURS)])
    baseline_charging_df.to_csv('baseline_charging_table.csv', index_label='EV_ID', float_format='%.2f', sep=';')

    print("Baseline charging schedule saved successfully to 'baseline_charging_table.csv'.")
    print("Baseline simulation completed successfully.")