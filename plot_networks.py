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

from concatenate_networks import safe_pypsa_import

import matplotlib.pyplot as plt

plt.style.use('ggplot')


def get_supply(n, buses):

    supply = pd.DataFrame(index=n.snapshots)

    for c in n.iterate_components(n.one_port_components):
        items = c.df.index[c.df.bus.isin(buses)]
        if len(items) == 0:
            continue

        s = (
            c.pnl.p[items]
            .multiply(n.snapshot_weightings.generators, axis=0)
            .multiply(c.df.loc[items, "sign"])
           .groupby(c.df.loc[items, "carrier"],axis=1)
            .sum()
            )
        #s = pd.concat([s], keys=[c.list_name], axis=1)

        if supply.empty:
            supply = s
        else:
            supply = pd.concat([supply,s], axis=1)


    for c in n.iterate_components(n.branch_components):
        for end in [col[3:] for col in c.df.columns if col[:3] == "bus"]:
            items = c.df.index[c.df[f"bus{str(end)}"].isin(buses)]

            if len(items) == 0:
                continue

            s = (-1) * c.pnl["p" + end][items].multiply(
                n.snapshot_weightings.generators, axis=0
            ).groupby(c.df.loc[items, "carrier"], axis=1).sum()
            s.columns = s.columns# + end
            #s = pd.concat([s], keys=[c.list_name], axis =1)
            if supply.empty:
                supply = s
            else:
                supply = pd.concat([supply,s], axis=1)


    return supply


def test_truncate(fn):
    if "-day-" in fn:
        return True
    else:
        return False


def plot_supplydemand(n, fn):

    fig, axes = plt.subplots(2)
    fig.set_size_inches((10, 8))

    truncate = test_truncate(fn)

    tz = config["time_zone"][ct]

    color = config["color"]

    supply = get_supply(n,[f"{ct}-electricity"])/1e3

    if supply.sum(axis=1).abs().max() > 1e-3:
        print("Demand-supply is violated!")
        sys.exit()

    supply.index = supply.index.tz_localize("UTC").tz_convert(tz)

    if truncate:
        supply = supply.iloc[:-config["extended_hours"]]

    threshold = config["numerical_threshold"]/1e3

    positive_columns = supply.columns[(supply.min() >= -threshold) & (supply > threshold).any()]
    negative_columns = supply.columns[(supply.max() <= threshold)  & (supply < -threshold).any()]

    positive = supply[positive_columns]
    positive = positive.where(positive >= 0, 0)

    negative = -supply[negative_columns]
    negative = negative.where(negative >= 0, 0)

    if "-full.nc" in fn:
        positive = positive.resample("W").mean()
        negative = negative.resample("W").mean()

    to_plot = [negative,positive]
    title = ["demand","supply"]
    for i,ax in enumerate(axes):
        to_plot[i].plot.area(stacked=True,linewidth=0,color=color,ax=axes[i])
        ax.set_ylabel("power [GW]")
        ax.set_xlabel("")
        ax.set_title(title[i])

    graphic_fn = f"{results_dir}/{fn[:-3]}-supplydemand"

    supply.to_csv(f"{graphic_fn}.csv")
    fig.savefig(f"{graphic_fn}.pdf",
                transparent=True,
                bbox_inches='tight')
    fig.savefig(f"{graphic_fn}.png",
                transparent=True,
                bbox_inches='tight')
    plt.close(fig)

def plot_state_of_charge(n, fn):

    truncate = test_truncate(fn)

    fig, axes = plt.subplots(2)
    fig.set_size_inches((10,7))

    tz = config["time_zone"][ct]

    color = config["color"]

    to_plot = n.stores_t.e.groupby(n.stores.carrier, axis=1).sum()

    if truncate:
        to_plot = to_plot.iloc[:-config["extended_hours"]]

    if "-full.nc" in fn:
        to_plot = to_plot.resample("W").mean()

    to_plot.index = to_plot.index.tz_localize("UTC").tz_convert(tz)

    factor = {"hydrogen_energy" : 1e6,
              "battery_energy" : 1e3}
    unit = {"hydrogen_energy" : "TWh",
            "battery_energy" : "GWh"}

    for i,col in enumerate(["hydrogen_energy","battery_energy"]):
        ax = axes[i]
        (to_plot[col]/factor[col]).plot(ax=ax,color=color)

        ax.set_ylabel(f"energy [{unit[col]}]")
        ax.set_xlabel("")
        ax.set_ylim([0.,1.05*to_plot[col].max()/factor[col]])
        ax.set_title(f"{col[:-7]} storage state of charge")

    graphic_fn = f"{results_dir}/{fn[:-3]}-state_of_charge"

    to_plot.to_csv(f"{graphic_fn}.csv")
    fig.savefig(f"{graphic_fn}.pdf",
                transparent=True,
                bbox_inches='tight')
    fig.savefig(f"{graphic_fn}.png",
                transparent=True,
                bbox_inches='tight')
    plt.close(fig)

def plot_price(n, fn):

    truncate = test_truncate(fn)

    fig, ax = plt.subplots()

    fig.set_size_inches((10,4))

    tz = config["time_zone"][ct]

    color = config["color"]

    to_plot = n.buses_t.marginal_price["DE-electricity"].copy()

    if truncate:
        to_plot = to_plot.iloc[:-config["extended_hours"]]

    if "-full.nc" in fn:
        to_plot = to_plot.resample("W").mean()

    to_plot.index = to_plot.index.tz_localize("UTC").tz_convert(tz)

    to_plot.plot(ax=ax)

    ax.set_ylabel("electricity price [€/MWh]")
    ax.set_xlabel("")
    ax.set_ylim([-0.5,1.05*to_plot.max()])
    ax.set_title(f"electricity price")

    graphic_fn = f"{results_dir}/{fn[:-3]}-price"

    to_plot.to_csv(f"{graphic_fn}.csv")
    fig.savefig(f"{graphic_fn}.pdf",
                transparent=True,
                bbox_inches='tight')
    fig.savefig(f"{graphic_fn}.png",
                transparent=True,
                bbox_inches='tight')

    plt.close(fig)

def plot_network(n, fn):

    plot_supplydemand(n, fn)
    plot_state_of_charge(n, fn)
    plot_price(n, fn)

def plot_all_networks(results_dir):

    for fn in os.listdir(results_dir):
        if fn[-3:] == ".nc":

            if "-day-" in fn:
                continue
            pdf_fn = f"{results_dir}/{fn[:-3]}-supplydemand.pdf"
            if os.path.isfile(pdf_fn) and (os.path.getmtime(pdf_fn) > os.path.getmtime(os.path.join(results_dir,fn))):
                continue
            else:
                print(f"calculating new plots for {fn}")
                n = safe_pypsa_import(f"{results_dir}/{fn}")
                plot_network(n, fn)

if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    scenario_fn = sys.argv[1]

    with open(scenario_fn, 'r') as file:
        config.update(yaml.safe_load(file))

    config["scenario"] = scenario_fn[scenario_fn.find("-")+1:-5]

    ct = config["countries"][0]

    results_dir = f"{config['results_dir']}/{config['scenario']}"

    plot_all_networks(results_dir)
