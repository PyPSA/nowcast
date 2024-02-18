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

import pandas as pd, yaml, os

def build_cop(config):


    ct = config["countries"][0]

    dir_name = config["weather_dir"]

    fn = os.path.join(dir_name,
                      f"{ct}-temperature.csv")

    temperature = pd.read_csv(fn,
                              index_col=0,
                              parse_dates=True)

    locations = pd.read_csv("DE-bundesländer.csv",
                            header=None,
                            index_col=0)
    locations.columns = ["population","latitude","longitude"]
    locations["population"] = locations["population"].astype(int)

    mean_t = temperature.multiply(locations["population"]).sum(axis=1)/locations["population"].sum()

    delta_t = config['heat_pump_supply_temperature'] - mean_t

    cop = 6.81 - 0.121 * delta_t + 0.000630 * delta_t**2

    cop.to_csv(os.path.join(dir_name,
                            f"{ct}-heat_pump_cop.csv"))

if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    build_cop(config)
