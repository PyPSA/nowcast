
# Nowcast: Tomorrow's power system with today's weather

Uses today's weather to show how the dispatch of tomorrow's power
system works.

<https://model.energy/nowcast/>

At the moment only works for Germany.

Takes day-ahead forecasts for wind, solar and load.

Dispatches a future energy system with wind, solar, batteries and
hydrogen storage to meet today's load. Capacities for the future are
fixed in advance.

The dispatch is myopic over the next 24 hours. The long-term hydrogen
storage is dispatched using a constant hydrogen value (e.g. 70 €/MWh).

Outputs include:

- Dispatch
- States of charge for battery and hydrogen storage
- Prices
- Bidding curves

There are some strong assumptions and limitations:

- Germany is an island system with no connection to neighbours
- Hydro and biomass are not yet modelled
- Balancing reserves are ignored
- Internal grid constraints and redispatch is ignored
- Future climate change is ignored


Future plans:

- Extend to other countries with interconnectors
- Include newly-electrified loads (electric vehicles, heat pumps, industry electrification, P2X)
- Include demand-side management
- Include existing hydroelectricity
- Include other storage technologies (iron-air batteries, methanol, ammonia, etc.)

## Live website

<https://model.energy/nowcast/>

## Installation

You will need PyPSA and pandas.

The solver defaults to gurobi, but other solvers can be used (see the
settings in the `config.yaml`).

## Running

All parameters are controlled from the `config.yaml` file.

First download the wind, solar and load data from the
[SMARD](https://www.smard.de/) platform by running

	python download_data_smard.py

Then run

	python solve_myopic.py


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
