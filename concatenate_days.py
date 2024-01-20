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


import pypsa, yaml, pandas as pd, os, datetime, sys

from concatenate_networks import concatenate, safe_pypsa_import


def concatenate_days(config):

    print(f"concatenating past {config['days_to_plot']} day networks to days network")

    ct = config["countries"][0]

    results_dir = f"{config['results_dir']}/{config['scenario']}"

    end_date = config["end_date"]

    if end_date == "today":
        end_date = datetime.date.today()
    elif end_date == "yesterday":
        end_date = datetime.date.today() - datetime.timedelta(days=1)

    start_date = end_date - datetime.timedelta(days=config['days_to_plot']-1)

    date_index = pd.date_range(start=start_date,
                               end=end_date)

    date_strings = date_index.astype(str)
    print(date_strings)
    #date_strings = [str(date.date()) for date in dates]

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

    days_fn = f"{results_dir}/{ct}-days-{str(start_date)}-{str(end_date)}.nc"

    n.export_to_netcdf(days_fn)


if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    scenario_fn = sys.argv[1]

    with open(scenario_fn, 'r') as file:
        config.update(yaml.safe_load(file))

    config["scenario"] = scenario_fn[scenario_fn.find("-")+1:-5]

    concatenate_days(config)
