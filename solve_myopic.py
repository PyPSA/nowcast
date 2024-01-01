## Copyright 2023 Tom Brown

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

from shutil import copy


def extend_df(df,hours):
    """extend an hourly df by hours, filling forward"""
    extended_index = df.index.union(pd.date_range(start=df.index[-1] + pd.Timedelta(hours=1), periods=hours, freq='H'))
    extended_df = df.reindex(extended_index, method='ffill')
    return extended_df


def derive_pu_availability(current_series, current_capacities):

    pu = pd.DataFrame()
    for item in current_capacities:
        print(f"calculating per unit for {item}")
        pu[item] = current_series[item]/current_capacities[item]/1e3
    return pu


def prepare_network(per_unit, future_capacities, load, soc, hydrogen_value):
    n = pypsa.Network()
    n.set_snapshots(per_unit.index)

    for ct in config["countries"]:
        n.add("Bus",
              f"{ct}-electricity",
              carrier="electricity")

        n.add("Load",
              f"{ct}-load",
              bus=f"{ct}-electricity",
              p_set=load[f"{ct}-load"],
              carrier="load")

        n.add("Generator",
              f"{ct}-load_shedding",
              bus=f"{ct}-electricity",
              p_nom=1e6,
              marginal_cost=config["voll"],
              carrier="load_shedding")

        for vre_tech in config["vre_techs"]:
            name = f"{ct}-{vre_tech}"
            n.add("Generator",
                  name,
                  bus=f"{ct}-electricity",
                  p_max_pu=per_unit[name],
                  p_nom=future_capacities[name]*1e3,
                  marginal_cost=config[f"mc-{vre_tech}"],
                  carrier=vre_tech)


        n.add("Bus",
                    f"{ct}-battery",
                    carrier="battery")

        name = f"{ct}-battery_energy"
        n.add("Store",
                    name,
                    bus = f"{ct}-battery",
                    carrier="battery_energy",
                    e_nom=future_capacities[name]*1e3,
                    e_initial=soc[name])

        n.add("Link",
                    f"{ct}-battery_charger",
                    bus0 = f"{ct}-electricity",
                    bus1 = f"{ct}-battery",
                    carrier="battery_charger",
                    efficiency = config["battery_power_efficiency_charging"],
                    p_nom=future_capacities[f"{ct}-battery"]*1e3)

        n.add("Link",
                    f"{ct}-battery_discharger",
                    bus0 = f"{ct}-battery",
                    bus1 = f"{ct}-electricity",
                    carrier="battery_discharger",
                    efficiency = config["battery_power_efficiency_discharging"],
                    p_nom=future_capacities[f"{ct}-battery"]*1e3)

        n.add("Bus",
              f"{ct}-hydrogen",
              carrier="hydrogen")

        name = f"{ct}-hydrogen_energy"
        n.add("Store",
                    name,
                    bus=f"{ct}-hydrogen",
                    carrier="hydrogen_energy",
                    e_nom=future_capacities[name]*1e3,
                    marginal_cost=hydrogen_value,
                    e_initial=soc[name])

        name=f"{ct}-hydrogen_turbine"
        n.add("Link",
              name,
              bus0=f"{ct}-hydrogen",
              bus1=f"{ct}-electricity",
              carrier="hydrogen_turbine",
              p_nom=future_capacities[name]*1e3/config["hydrogen_turbine_efficiency"],
              efficiency=config["hydrogen_turbine_efficiency"])

        name=f"{ct}-hydrogen_electrolyser"
        n.add("Link",
              name,
              bus0=f"{ct}-electricity",
              bus1=f"{ct}-hydrogen",
              carrier="hydrogen_electrolyser",
              p_nom=future_capacities[name]*1e3,
              efficiency=config["hydrogen_electrolyser_efficiency"])




    n.consistency_check()
    return n

def solve_network(n):
    n.optimize.create_model()

    status, termination_condition = n.optimize.solve_model(solver_name=config["solver_name"],
                                                           solver_options=config["solver_options"],
                                                           log_fn=config["solver_logfile"])

def solve_all(config):

    ct = "DE"

    extended_hours = config["extended_hours"]

    end_date = config["end_date"]

    if end_date == "today":
        end_date = datetime.date.today()
    elif end_date == "yesterday":
        end_date = datetime.date.today() - datetime.timedelta(days=1)

    date_index = pd.date_range(start=config["start_date"],
                               end=end_date,
                               tz=pytz.timezone(config["time_zone"][ct]))

    print(date_index)

    for i,date in enumerate(date_index):

        print(i)

        date_string = str(date.date())
        print(date_string)

        fn = f"{results_dir}/DE-day-{date_string}.nc"
        if os.path.isfile(fn):
            print(f"{fn} already exists, skipping")
            continue

        if i == 0:
            soc = { f"{ct}-{key}" : value for key,value in config["soc_start"][ct].items() }
        else:
            day_before = date - datetime.timedelta(days=1)
            if "n" in locals() and day_before in n.snapshots:
                print(f"using network in scope for {day_before.date()} SOC")
            else:
                day_before_fn = f"{results_dir}/DE-day-{str(day_before.date())}.nc"
                print(f"reading in SOC from {day_before_fn}")
                n = pypsa.Network(day_before_fn)

            soc = n.stores_t.e[-extended_hours-1:-extended_hours].squeeze().to_dict()

        print("soc:")
        print(soc)

        weather_fn = f"{config['weather_dir']}/{ct}-day-{date_string}.csv"
        if not os.path.isfile(weather_fn):
            print(f"{weather_fn} is missing, skipping {date_string}")
            continue

        df = pd.read_csv(weather_fn,
                         parse_dates=True,
                         index_col=0)

        extended_df = extend_df(df,
                                extended_hours)

        current_capacities = { f"{ct}-{key}" : value for key,value in config["historical_capacities"][ct][datetime.datetime.strptime("2023-12-30", '%Y-%m-%d').date()].items() }

        print("current capacities:")
        print(current_capacities)

        per_unit = derive_pu_availability(extended_df,
                                          current_capacities)

        future_capacities = { f"{ct}-{key}" : value for key,value in config["future_capacities"][ct].items() }

        n = prepare_network(per_unit,
                            future_capacities,
                            extended_df[[f"{ct}-load"]],
                            soc,
                            config["hydrogen_value"])


        solve_network(n)

        n.export_to_netcdf(fn,
                           float32=True, compression={'zlib': True, "complevel":9, "least_significant_digit":5})


def copy_config(results_dir):

    files = [
        "config.yaml",
        "solve_myopic.py",
    ]
    for f in files:
        copy(f, results_dir)

if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    print(config)

    results_dir = f"{config['results_dir']}/{config['scenario']}"
    if not os.path.isdir(results_dir):
        os.mkdir(results_dir)

    copy_config(results_dir)

    solve_all(config)
