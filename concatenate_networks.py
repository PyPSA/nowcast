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



def concatenate(n,ni):

    n.set_snapshots(n.snapshots.union(ni.snapshots))

    for c in n.iterate_components():
        for attr in c.pnl:
            if not c.pnl[attr].empty:
                #print(c.name,attr)
                c.pnl[attr].loc[ni.snapshots] = getattr(ni,c.list_name + "_t")[attr]

    return n


def concatenate_all(config):

    ct = "DE"

    extended_hours = config["extended_hours"]

    results_dir = f"{config['results_dir']}/{config['scenario']}"

    end_date = config["end_date"]

    if end_date == "today":
        end_date = datetime.date.today()
    elif end_date == "yesterday":
        end_date = datetime.date.today() - datetime.timedelta(days=1)

    date_index = pd.date_range(start=config["start_date"],
                               end=end_date,
                               tz=pytz.timezone(config["time_zone"][ct]))


    print(date_index)

    if os.path.isfile(full_fn):
        print("full file already exists")
        n = pypsa.Network(full_fn)

    for i,date in enumerate(date_index):

        print(i)

        date_string = str(date.date())
        print(date_string)

        if "n" in locals() and date_string in n.snapshots:
            print(f"{date_string} already in full network, skipping")
            continue

        fn = f"{results_dir}/{ct}-day-{date_string}.nc"

        ni = pypsa.Network(fn)

        #truncate overlap
        ni.set_snapshots(ni.snapshots[:-extended_hours])

        if i == 0:
            n = ni
        else:
            n = concatenate(n,ni)

    return n

if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    print(config)

    results_dir = f"{config['results_dir']}/{config['scenario']}"

    ct = "DE"

    full_fn = f"{results_dir}/{ct}-full.nc"

    n = concatenate_all(config)

    n.export_to_netcdf(full_fn,
                       float32=True, compression={'zlib': True, "complevel":9, "least_significant_digit":5})
