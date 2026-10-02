"""
data_generation.py: Generates data of EV fleet (arrival, departure, battery capacity, initial/target State of Charge and charger's max power)
Author: Dimitrios Poulos
"""



import numpy as np
import pandas as pd



HOURS = 24
EVS_NUMBER = 10
RANDOM_SEED = 42


def generate_ev_fleet():
    """
    Generates synthetic parameters and charging constraints for the EV fleet.
    Departure hour is expressed on a scale of 24 + next-day hour so the
    fleet simulation scripts can detect overnight charging sessions that span midnight.
    Returns:
            ev_fleet_df (pd.DataFrame): DataFrame containing the fleet attributes with columns: ev_id, bus, arrival_hour, departure_hour, battery_capacity, initial_soc, target_soc, max_power.
    """
    np.random.seed(RANDOM_SEED)
    ev_fleet = []
    for ev in range(EVS_NUMBER):
        arrival_hour = np.random.randint(16, 22)    # Random arrival hour at home (16:00 to 21:00)
        departure_hour = np.random.randint(6, 9) + 24    # Departure hour the next morning (06:00 to 08:00) - plus 24 hours to handle the continuous 24-hour horizon properly
        battery_capacity = np.random.choice([40, 60, 80])    # Choice of battery capacity from typical market sizes (kWh)
        initial_soc = round(np.random.uniform(0.2, 0.6), 2)    # Initial State of Charge (SoC) upon arrival (20% to 60%)
        target_soc = round(np.random.uniform(0.8, 1.0), 2)    # Target State of Charge (SoC) upon departure (80% to 100%)
        max_power_charger = np.random.choice([7.4, 11.0])    # Maximum charger power (7.4 kW single-phase or 11 kW three-phase)

        # All generated attributes are gathered and appended to the main fleet list
        ev_fleet.append({
            'ev_id': ev,
            'bus': ev + 2,    # Assigned to CIGRE LV grid buses (starting from bus 2)
            'arrival_hour': arrival_hour,
            'departure_hour': departure_hour,
            'battery_capacity': battery_capacity,
            'initial_soc': initial_soc,
            'target_soc': target_soc,
            'max_power': max_power_charger
        })

    ev_fleet_df = pd.DataFrame(ev_fleet)    # Conversion of the list into a Pandas DataFrame for easy handling
    return ev_fleet_df



if __name__ == "__main__":
    print("Generating fleet data...")
    ev_fleet_df = generate_ev_fleet()

    # Fleet data is saved in csv file in order to be used in the other scripts
    ev_fleet_df.to_csv('ev_fleet_data.csv', index=False)
    print("EV fleet data saved successfully to 'ev_fleet_data.csv'.")