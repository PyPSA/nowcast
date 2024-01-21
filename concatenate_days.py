## Copyright 2024 Tom Brown

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


import pypsa, yaml, pandas as pd, os, datetime, sys

from helpers import concatenate, safe_pypsa_import, get_last_days


def concatenate_days(config):

    print(f"concatenating past {config['days_to_plot']} day networks to days network")

    ct = config["countries"][0]

    results_dir = f"{config['results_dir']}/{config['scenario']}"

    date_strings = get_last_days(config).astype(str)

    extended_hours = config["extended_hours"]

    for i,date_string in enumerate(date_strings):

        fn = f"{results_dir}/{ct}-day-{date_string}.nc"

        ni = safe_pypsa_import(fn)

        #truncate overlap
        ni.set_snapshots(ni.snapshots[:-extended_hours])

        if i == 0:
            n = ni
        else:
            n = concatenate(n,ni)

    days_fn = f"{results_dir}/{ct}-days-{date_strings[0]}-{date_strings[-1]}.nc"

    n.export_to_netcdf(days_fn)


if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    scenario_fn = sys.argv[1]

    with open(scenario_fn, 'r') as file:
        config.update(yaml.safe_load(file))

    config["scenario"] = scenario_fn[scenario_fn.find("-")+1:-5]

    concatenate_days(config)
