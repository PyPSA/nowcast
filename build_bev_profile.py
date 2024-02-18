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

import pandas as pd, yaml, os, datetime
from helpers import get_date_index

def build_bev_profile(config):

    ct = config["countries"][0]

    dir_name = config["weather_dir"]

    date_index = get_date_index(config)

    snapshots = pd.date_range(date_index[0],
                              date_index[-1]+datetime.timedelta(hours=23),
                              freq="h")

    df = pd.DataFrame(dtype=float,
                      index=snapshots)

    df["bev_demand"] = 1/8766

    df["bev_availability"] = 1.

    df.loc[df.index[(df.index.hour > config['bev_charge_end_hour']) & (df.index.hour < config['bev_charge_start_hour'])], "bev_availability"] = 0.

    df.to_csv(os.path.join(dir_name,
                           f"{ct}-bev_profile.csv"))

if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    build_bev_profile(config)
