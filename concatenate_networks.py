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


import pypsa, yaml, pandas as pd, os, pytz, datetime, sys


def safe_pypsa_import(filename):
    """If time series are all empty, fill with zeros."""

    n = pypsa.Network(filename)


    list_attrs = {"Link" : ["p0","p1"],
                                "Store" : ["e","p"]}

    for c in n.iterate_components(list_attrs.keys()):
        for attr in list_attrs[c.name]:
            if c.pnl[attr].empty:
                print(f"Since {attr} is empty for {c.list_name}, filling with zeros")
                c.pnl[attr] = c.pnl[attr].reindex(c.df.index, axis=1).fillna(0.)

    return n

def concatenate(n,ni):

    for c in n.iterate_components():
        for attr in c.pnl:
            if not c.pnl[attr].empty:
                c.pnl[attr] = pd.concat([c.pnl[attr],getattr(ni,c.list_name + "_t")[attr]])

    n.set_snapshots(n.snapshots.union(ni.snapshots))

    return n


def concatenate_all(config):

    print("concatenating all day networks to a full network")

    ct = config["countries"][0]

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

    if os.path.isfile(full_fn):
        print("full network already exists")
        n = pypsa.Network(full_fn)

    for i,date in enumerate(date_index):

        date_string = str(date.date())

        if "n" in locals() and date_string in n.snapshots:
            continue

        print(f"{date_string} not yet in full network, adding")

        fn = f"{results_dir}/{ct}-day-{date_string}.nc"

        ni = safe_pypsa_import(fn)

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

    scenario_fn = sys.argv[1]

    with open(scenario_fn, 'r') as file:
        config.update(yaml.safe_load(file))

    config["scenario"] = scenario_fn[scenario_fn.find("-")+1:-5]

    results_dir = f"{config['results_dir']}/{config['scenario']}"

    ct = config["countries"][0]

    full_fn = f"{results_dir}/{ct}-full.nc"

    n = concatenate_all(config)

    n.export_to_netcdf(full_fn,
                       float32=True, compression={'zlib': True, "complevel":9, "least_significant_digit":5})
