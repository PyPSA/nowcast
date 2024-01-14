
# Nowcast: Tomorrow's power system with today's weather

Uses today's weather to show how the dispatch of tomorrow's power
system works.

<https://model.energy/nowcast/>

At the moment only works for Germany.

Takes daily data for wind, solar, hydro and load.

Dispatches a future energy system with wind, solar, hydroelectricity,
batteries and hydrogen storage to meet today's load. Capacities for
the future are fixed in advance.

The dispatch is myopic over the next 24 hours. The long-term hydrogen
storage is dispatched using a constant hydrogen value (e.g. 80 €/MWh).

Outputs include:

- Dispatch
- States of charge for battery and hydrogen storage
- Prices
- Bidding curves

There are some strong assumptions and limitations:

- Germany is an island system with no connection to neighbours
- Balancing reserves are ignored
- Internal grid constraints and redispatch is ignored
- Future climate change is ignored
- Biomass is not modelled


Future plans:

- Extend to other countries with interconnectors
- Include newly-electrified loads (electric vehicles, heat pumps, industry electrification, P2X)
- Include demand-side management
- Include other storage technologies (iron-air batteries, methanol, ammonia, etc.)

## Live website

<https://model.energy/nowcast/>

## Installation

You will need PyPSA and pandas.

The solver defaults to gurobi, but other solvers can be used (see the
settings in the `config.yaml`).

## Running

All parameters are controlled from the `config.yaml` file.

Running

	python execute_all.py

will run all scripts in the necessary sequence.

`download_data_smard.py` downloads the wind, solar, hydro and load data from the
[SMARD](https://www.smard.de/) platform.

`correct_data_smard.py` corrects the wind, solar and hydro data using
yearly correction factors based on the net generation statistics from
[AG Energiebilanzen
e.V.](https://ag-energiebilanzen.de/daten-und-fakten/zusatzinformationen/).

`solve_myopic.py scenario-default.yaml` optimises each day myopically in sequence, passing
on the state of charge of all storage units.

`concatenate_networks.py scenario-default.yaml` builds a single PyPSA network out of all day
networks (for plotting later).

`concatenate_weeks scenario-default.yaml` builds weekly PyPSA networks out of all day
networks (for plotting later).

`plot_networks.py scenario-default.yaml` generates the graphics.

`generate_html.py scenario-default.yaml` makes a webpage for each scenario.


## Other websites that served as an inspiration

- [David Osmond simulations for Australia](https://reneweconomy.com.au/a-near-100-per-cent-renewables-grid-is-well-within-reach-and-with-little-storage/)
- [Agora future-o-meter for Germany](https://www.agora-energiewende.de/service/agorameter)
- [energy-charts REMod scenarios](https://www.energy-charts.info/charts/remod_installed_power/chart.htm?l=en&c=DE) (not live)


## License

Copyright 2023-4 Tom Brown <https://nworbmot.org/>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation; either [version 3 of the
License](LICENSE.txt), or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the [GNU
Affero General Public License](LICENSE.txt) for more details.
