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


def concatenate_week(date_strings, week_fn, config):

    print(f"concatenating {date_strings} to {week_fn}")

    ct = config["countries"][0]

    extended_hours = config["extended_hours"]

    results_dir = f"{config['results_dir']}/{config['scenario']}"

    for i,date_string in enumerate(date_strings):

        fn = f"{results_dir}/{ct}-day-{date_string}.nc"

        ni = safe_pypsa_import(fn)

        #truncate overlap
        ni.set_snapshots(ni.snapshots[:-extended_hours])

        if i == 0:
            n = ni
        else:
            n = concatenate(n,ni)
    n.export_to_netcdf(week_fn)

def concatenate_weeks(config):

    print("concatenating all day networks to week networks")

    ct = config["countries"][0]

    results_dir = f"{config['results_dir']}/{config['scenario']}"

    end_date = config["end_date"]

    if end_date == "today":
        end_date = datetime.date.today()
    elif end_date == "yesterday":
        end_date = datetime.date.today() - datetime.timedelta(days=1)

    date_index = pd.date_range(start=config["start_date"],
                               end=end_date)

    isocalendar = date_index.isocalendar()

    for year in isocalendar.year.unique():

        for week in isocalendar[isocalendar.year == year].week.unique():
            dates = date_index[(isocalendar.week == week) & (isocalendar.year == year)]
            date_strings = [str(date.date()) for date in dates]

            week_fn = f"{results_dir}/{ct}-week-{year}-{week}.nc"
            date_fns = [f"{results_dir}/{ct}-day-{ds}.nc" for ds in date_strings]

            if os.path.isfile(week_fn):
                if pd.Index([os.path.getmtime(week_fn) > os.path.getmtime(date_fn) for date_fn in date_fns]).all():
                    continue
            concatenate_week(date_strings,week_fn,config)


if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    scenario_fn = sys.argv[1]

    with open(scenario_fn, 'r') as file:
        config.update(yaml.safe_load(file))

    config["scenario"] = scenario_fn[scenario_fn.find("-")+1:-5]

    concatenate_weeks(config)
