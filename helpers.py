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

import datetime, pandas as pd, os, re, pypsa


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

def get_end_date(config):

    end_date = config["end_date"]

    if end_date == "today":
        end_date = datetime.date.today()
    elif end_date == "yesterday":
        end_date = datetime.date.today() - datetime.timedelta(days=1)

    return end_date


def get_last_days(config):

    end_date = get_end_date(config)

    start_date = end_date - datetime.timedelta(days=config['days_to_plot']-1)

    return pd.date_range(start=start_date, end=end_date)


def get_date_index(config):

    end_date = get_end_date(config)

    return pd.date_range(start=config["start_date"],
                         end=end_date)



def get_existing_dates(dir_name, pattern):

    date_strings = []

    for filename in os.listdir(dir_name):
        match = re.match(pattern, filename)
        if match:
            date_strings.append(match.group(1))

    return pd.to_datetime(sorted(date_strings))
