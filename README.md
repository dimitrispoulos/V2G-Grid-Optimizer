# **V2G Grid Optimizer**

V2G Grid Optimizer is a Python package for simulating and optimizing the charging and discharging of Electric Vehicles (EVs) on a residential grid. It uses the Pandapower library for power flow simulations and CVXPY for convex optimization to balance economic incentives with strict grid limitations.

-----
-----


## Key Features & Functionality
*   **Scenario Simulation:** Simulates uncontrolled (baseline) and optimized (V2G) charging scenarios for a fleet of EVs.
*   **Cost Minimization:** Uses Day-Ahead Market (DAM) prices to determine the optimal charging/discharging schedule.
*   **Constraint Management:** Takes into account per-EV battery/charger limits and a fleet-wide transformer power limit.
*   **Grid Stability Validation:** Validates the charging table against the power flow simulation using Pandapower.
*   **Visual Analytics:** Generates a 6-panel visual summary of the impact of the EV fleet on the residential grid.

-----


## Data Sources & APIs
*   **Synthetic Fleet Data:** EV fleet data is generated using the `data_generation.py` script, which creates synthetic parameters and charging constraints for the EV fleet.
*   **Market Data:** DAM prices are read from the `dam_forecast.csv` file. These 24-hour predictions are generated dynamically by my custom DAM Forecaster machine learning pipeline. The external script uses a LightGBM Regressor trained on real-time ENTSO-E grid data and Yahoo Finance natural gas (TTF) prices.

-----


## Mathematical Logic
$$
\text{Total Cost} = \sum_{t=1}^{T} \sum_{e=1}^{E} \text{Power}_{e,t} \times \text{Price}_{t}
$$

where $Power_{e,t}$ is the net power exchange between the EV $e$ and the grid at time step $t$, and $Price_{t}$ is the DAM price at time step $t$.

-----


## Software
*   Python 3.8+
*   Pandapower 2.5+
*   CVXPY 1.2+
*   NumPy 1.20+
*   Pandas 1.3+

-----


## Libraries & Frameworks
| Package | Purpose |
|---------|---------|
| `pandapower` | Power flow simulations |
| `cvxpy` | Convex optimization |
| `numpy` | Numerical computations |
| `pandas` | Data manipulation and analysis |
| `matplotlib` | Generates the multi-panel visual dashboard for end-to-end results analysis |
| `tabulate` | Formats and prints clean, readable summary comparison tables directly in the terminal |

-----


## Installation Guide
### Requirements
- Python 3.8+
### Setup
In your IDE's terminal please enter the following:
```bash
pip install cvxpy matplotlib numpy pandapower pandas tabulate
python data_generation.py
python main.py
```

-----


## Technical Limitations
*   The package assumes a residential grid with a single transformer and a fixed fleet of EVs
*   The optimization problem is solved using CVXPY, which may not be suitable for large-scale problems
*   The package does not account for other grid constraints, such as voltage limits and line flow limits


-----


## License
MIT License: Free to use, modify, and distribute with attribution.


-----
-----


## **Developer**
**Dimitrios Poulos** <br>
*Electrical \& Computer Engineering Student*
* **Release Date:** October 2026
