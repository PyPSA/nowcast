
# Nowcast: Tomorrow's energy system with today's weather

Uses today's weather to show how the dispatch of tomorrow's energy
system works.

At the moment only works for Germany.

Takes day-ahead forecasts for wind, solar and load.

Dispatched a future energy system with wind, solar, batteries and
hydrogen storage to meet today's load.

Future plans:

- Extend to other countries with interconnectors
- Include newly-electrified loads (electric vehicles, heat pumps, industry electrification, P2X)
- Include demand-side management

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



## License

Copyright 2018-2023 Tom Brown <https://nworbmot.org/>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation; either [version 3 of the
License](LICENSE.txt), or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the [GNU
Affero General Public License](LICENSE.txt) for more details.
