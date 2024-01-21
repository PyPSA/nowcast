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


import pypsa, yaml, pandas as pd, os, pytz, datetime, sys, numpy as np

from helpers import safe_pypsa_import

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
                dpi=200,
                transparent=True,
                bbox_inches='tight')
    plt.close(fig)


def plot_supply(n, fn):

    fig, ax = plt.subplots()
    fig.set_size_inches((10, 2))

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

    positive.plot.area(stacked=True,linewidth=0,color=color,ax=ax)
    ax.set_ylabel("power [GW]")
    ax.set_xlabel("")
    ax.set_title("")
    ax.get_legend().remove()

    graphic_fn = f"{results_dir}/{fn[:-3]}-supply"

    supply.to_csv(f"{graphic_fn}.csv")
    fig.savefig(f"{graphic_fn}.pdf",
                transparent=True,
                bbox_inches='tight')
    fig.savefig(f"{graphic_fn}.png",
                dpi=200,
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
                dpi=200,
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
                dpi=200,
                transparent=True,
                bbox_inches='tight')

    plt.close(fig)



def plot_price_duration(n, fn):

    fig, ax = plt.subplots()

    fig.set_size_inches((10,4))

    to_plot = n.buses_t.marginal_price["DE-electricity"].copy()

    s = to_plot.sort_values(ascending=False)

    s.index = 100*np.arange(len(s.index))/len(s.index)

    s.plot(ax=ax)

    ax.set_ylabel("electricity price [€/MWh]")
    ax.set_xlabel("fraction of time [%]")
    ax.set_ylim([-0.5,1.05*to_plot.max()])
    ax.set_xlim([0,100])
    ax.set_title("electricity price duration curve")

    graphic_fn = f"{results_dir}/{fn[:-3]}-price_duration"

    s.to_csv(f"{graphic_fn}.csv")
    fig.savefig(f"{graphic_fn}.pdf",
                transparent=True,
                bbox_inches='tight')
    fig.savefig(f"{graphic_fn}.png",
                dpi=200,
                transparent=True,
                bbox_inches='tight')

    plt.close(fig)


def generate_statistics(n, fn, config):

    nyears = n.snapshot_weightings["generators"].sum()/8766

    ct = config["countries"][0]

    s = pd.Series()

    s["electricity mean price [€/MWh]"] = n.buses_t.marginal_price[f"{ct}-electricity"].mean()

    costs = pd.read_csv("costs.csv",
                        index_col=0)

    caps = pd.Series(config["future_capacities"][ct])

    component_costs = (caps*costs["fixed [€/MW/a]"]/1e3).rename(lambda n: n + " yearly fixed costs [M€/a]")

    caps.index = [i + " capacity [GWh]" if "energy" in i else i + " capacity [GW]" for i in caps.index]

    s = pd.concat([s,caps,component_costs])

    s["total yearly fixed costs [M€/a]"] = component_costs.sum()


    supply = get_supply(n,[f"{ct}-electricity"])

    s = pd.concat([s,supply.sum().abs().rename(lambda n: n + " yearly dispatch [TWh/a]")/nyears/1e6])

    vre_techs = config["vre_techs"]

    available = n.generators_t.p_max_pu.multiply(n.snapshot_weightings["generators"],axis=0).multiply(n.generators.p_nom_opt,axis=1)
    available = available.groupby(n.generators.carrier,axis=1).sum()[vre_techs]

    s = pd.concat([s,available.sum().rename(lambda n: n + " yearly available [TWh/a]")/nyears/1e6])

    cf_available = available.mean()/n.generators.p_nom_opt.groupby(n.generators.carrier).sum()[vre_techs]
    s = pd.concat([s,cf_available.rename(lambda n: n + " capacity factor available [%]")*100])

    used = n.generators_t.p.groupby(n.generators.carrier,axis=1).sum()[vre_techs]
    s = pd.concat([s,used.sum().rename(lambda n: n + " yearly used [TWh/a]")/nyears/1e6])


    curtailed = available-used
    s = pd.concat([s,curtailed.sum().rename(lambda n: n + " yearly curtailed [TWh/a]")/nyears/1e6])

    curtailment = curtailed.sum()/available.sum()
    s = pd.concat([s,curtailment.rename(lambda n: n + " average curtailment [%]")*100])

    cf = (n.generators_t.p.mean()/n.generators.p_nom_opt).groupby(n.generators.carrier).mean()
    s = pd.concat([s,cf.rename(lambda n: n + " capacity factor [%]")*100])

    cf = (n.links_t.p0.mean()/n.links.p_nom_opt).groupby(n.links.carrier).mean()
    s = pd.concat([s,cf.rename(lambda n: n + " capacity factor [%]")*100])

    p = n.generators_t.p.multiply(n.snapshot_weightings["generators"],axis=0).groupby(n.generators.carrier,axis=1).sum()
    revenue = p.multiply(n.buses_t.marginal_price[f"{ct}-electricity"],axis=0)
    mv = revenue.sum()/p.sum()

    s = pd.concat([s,revenue.sum().rename(lambda n: n + " yearly revenue [M€/a]")/nyears/1e6])
    s = pd.concat([s,mv.rename(lambda n: n + " average market value [€/MWh]")])


    p0 = n.links_t.p0.multiply(n.snapshot_weightings["generators"],axis=0)
    prices0 = n.buses_t.marginal_price[n.links.bus0]
    prices0.columns = n.links.index
    p1 = n.links_t.p1.multiply(n.snapshot_weightings["generators"],axis=0)
    prices1 = n.buses_t.marginal_price[n.links.bus1]
    prices1.columns = n.links.index
    revenue = (-p1*prices1 -p0*prices0).sum().groupby(n.links.index).sum()
    #mv = revenue.sum()/p.sum()
    s = pd.concat([s,revenue.rename(lambda n: n + " yearly revenue minus variable costs [M€/a]")/nyears/1e6])

    for port in ["0","1"]:
        links = n.links.index[n.links[f"bus{port}"] == f"{ct}-electricity"]
        p = n.links_t[f"p{port}"].multiply(n.snapshot_weightings["generators"],axis=0).groupby(n.links.carrier[links],axis=1).sum()
        revenue = p.multiply(n.buses_t.marginal_price[f"{ct}-electricity"],axis=0)
        mv = revenue.sum()/p.sum()
        s = pd.concat([s,mv.rename(lambda n: n + " average market value [€/MWh]")])


    s["total yearly revenue [M€/a]"] = s[s.index.str.contains(" yearly revenue")].sum()

    s["System levelised cost [€/MWh]"] = s["total yearly fixed costs [M€/a]"]/s["load yearly dispatch [TWh/a]"]

    print("replacing following nans with zero")

    print(s[s.isna()])

    s[s.isna()] = 0.

    print(s)

    s.to_csv(f"{results_dir}/{fn[:-3]}-statistics.csv")

def plot_network(n, fn):

    plot_supplydemand(n, fn)
    plot_supply(n, fn)
    plot_state_of_charge(n, fn)
    plot_price(n, fn)

    if "-full.nc" in fn:
        plot_price_duration(n, fn)
        generate_statistics(n, fn, config)

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
