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


import pypsa, yaml, pandas as pd, os, pytz, datetime


from concatenate_networks import concatenate


def concatenate_week(date_strings,week_fn):

    for i,date_string in enumerate(date_strings):

        fn = f"{results_dir}/{ct}-day-{date_string}.nc"

        ni = pypsa.Network(fn)

        #truncate overlap
        ni.set_snapshots(ni.snapshots[:-extended_hours])

        if i == 0:
            n = ni
        else:
            n = concatenate(n,ni)
    n.export_to_netcdf(week_fn)

def concatenate_weeks(config):

    end_date = config["end_date"]

    if end_date == "today":
        end_date = datetime.date.today()
    elif end_date == "yesterday":
        end_date = datetime.date.today() - datetime.timedelta(days=1)

    date_index = pd.date_range(start=config["start_date"],
                               end=end_date,
                               tz=pytz.timezone(config["time_zone"][ct]))

    isocalendar = date_index.isocalendar()

    for year in isocalendar.year.unique():

        for week in isocalendar[isocalendar.year == year].week.unique():
            print(year,week)
            dates = date_index[(isocalendar.week == week) & (isocalendar.year == year)]
            date_strings = [str(date.date()) for date in dates]
            print(date_strings)

            week_fn = f"{results_dir}/{ct}-week-{year}-{week}.nc"

            if os.path.isfile(week_fn):
                n = pypsa.Network(week_fn)
                if pd.Index([date_string in n.snapshots for date_string in date_strings]).all():
                    print("all dates are in existing file, skipping")
                    continue
            concatenate_week(date_strings,week_fn)


if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)


    ct = "DE"

    extended_hours = config["extended_hours"]

    results_dir = f"{config['results_dir']}/{config['scenario']}"

    concatenate_weeks(config)
