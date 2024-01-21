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

from helpers import get_last_days

import matplotlib.pyplot as plt

plt.style.use('ggplot')

def concatenate_data(date_strings, ct):

    for i,date_string in enumerate(date_strings):

        weather_fn = f"{config['weather_dir']}/{ct}-day-{date_string}-corrected.csv"

        df = pd.read_csv(weather_fn,
                         parse_dates=True,
                         index_col=0)

        if i == 0:
            full = df
        else:
            full = pd.concat([full,df])

    return full

#modelled on plot_networks.plot_supply()
def plot(config):
    date_strings = get_last_days(config).astype(str)

    ct = config["countries"][0]

    df = concatenate_data(date_strings, ct)

    fig, ax = plt.subplots()
    fig.set_size_inches((10, 2))

    tz = config["time_zone"][ct]

    color = config["color"]

    supply = df/1e3

    supply.index = supply.index.tz_convert(tz)

    supply.columns = supply.columns.str[3:]

    supply["conventional"] = supply["load"] - supply[config["vre_techs"]].sum(axis=1)

    supply.drop(["load"],axis=1,inplace=True)

    supply = supply.where(supply >= 0, 0)

    supply.plot.area(stacked=True,linewidth=0,color=color,ax=ax)

    ax.set_ylabel("power [GW]")
    ax.set_xlabel("")
    ax.set_title("")
    ax.get_legend().remove()

    graphic_fn = f"{config['results_dir']}/today/{ct}-days-{date_strings[0]}-{date_strings[-1]}-today"

    supply.to_csv(f"{graphic_fn}.csv")
    fig.savefig(f"{graphic_fn}.pdf",
                transparent=True,
                bbox_inches='tight')
    fig.savefig(f"{graphic_fn}.png",
                dpi=200,
                transparent=True,
                bbox_inches='tight')
    plt.close(fig)

if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    results_dir = f"{config['results_dir']}/today"

    if not os.path.isdir(results_dir):
        os.mkdir(results_dir)

    df = plot(config)
