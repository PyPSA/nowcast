## Copyright 2023-4 Tom Brown

## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU Affero General Public License as
## published by the Free Software Foundation; either version 3 of the
## License, or (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Affero General Public License for more details.

## License and more information at:
## https://github.com/PyPSA/nowcast



import os, sys

scripts_generic = [
    "download_data_smard.py",
]

scripts_scenario = [
    "solve_myopic.py",
    "concatenate_networks.py",
    "concatenate_weeks.py",
    "plot_networks.py",
    "generate_html.py",
    ]


scenario_fns = []

for fn in os.listdir("./"):
    if fn[:9] == "scenario-" and fn[-5:] == ".yaml":
        scenario_fns.append(fn)

print(scenario_fns)

for script in scripts_generic:
    command = f"{sys.executable} {script}"
    print(f"executing {command}")
    os.system(command)

for scenario_fn in scenario_fns:
    for script in scripts_scenario:
        command = f"{sys.executable} {script} {scenario_fn}"
        print(f"executing {command}")
        os.system(command)
