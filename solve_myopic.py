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


import pypsa, yaml, pandas as pd, os, datetime, sys

from shutil import copy

from download_data_smard import get_existing_dates

def extend_df(df,hours):
    """extend an hourly df by hours, filling forward"""
    extended_index = df.index.union(pd.date_range(start=df.index[-1] + pd.Timedelta(hours=1), periods=hours, freq='H'))
    extended_df = df.reindex(extended_index, method='ffill')
    return extended_df

def interpolate_historical_capacities(config, ct, date_index):

    df = pd.DataFrame(config["historical_capacities"][ct]).T
    df.index = pd.to_datetime(df.index)

    big_date_index = pd.date_range(start=min(df.index[0], date_index[0]),
                                   end=max(df.index[-1], date_index[-1]))

    interpolation = df.reindex(big_date_index).interpolate(limit_direction="both")

    return interpolation.loc[date_index]

def derive_pu_availability(current_series, current_capacities):

    pu = pd.DataFrame()
    for item in current_capacities:
        print(f"calculating per unit for {item}")
        pu[item] = current_series[item]/current_capacities[item]/1e3
    return pu


def prepare_network(per_unit, future_capacities, load, soc, config):
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
                    marginal_cost=config["hydrogen_value"],
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

def solve_network(n, config, solver_name):
    n.optimize.create_model()

    status, termination_condition = n.optimize.solve_model(solver_name=solver_name,
                                                           solver_options=config["solver_options"][solver_name],
                                                           log_fn=config["solver_logfile"])

def solve_all(config):

    solver_name = determine_solver_name(config)
    print(f"using solver {solver_name}")

    results_dir = f"{config['results_dir']}/{config['scenario']}"

    ct = config["countries"][0]

    extended_hours = config["extended_hours"]

    already = get_existing_dates(results_dir,
                                 ct + r"-day-(\d{4}-\d{2}-\d{2}).nc")

    end_date = config["end_date"]

    if end_date == "today":
        end_date = datetime.date.today()
    elif end_date == "yesterday":
        end_date = datetime.date.today() - datetime.timedelta(days=1)

    date_index = pd.date_range(start=config["start_date"],
                               end=end_date)

    dates_to_process = date_index.difference(already)

    print(f"dates_to_process: {dates_to_process}")

    historical_capacities = interpolate_historical_capacities(config, ct, date_index)

    for date in dates_to_process:

        date_string = str(date.date())

        print(f"Solving date {date_string}")

        fn = f"{results_dir}/DE-day-{date_string}.nc"

        day_before = date - datetime.timedelta(days=1)
        day_before_fn = f"{results_dir}/DE-day-{str(day_before.date())}.nc"

        if "n" in locals() and day_before.tz_localize("UTC") in n.snapshots:
            print(f"using network in scope for {day_before.date()} SOC")
        elif os.path.isfile(day_before_fn):
            print(f"reading in SOC from {day_before_fn}")
            n = pypsa.Network(day_before_fn)
        else:
            print(f"no previously-calculated SOC, using soc_start")
            soc = { f"{ct}-{key}" : value for key,value in config["soc_start"][ct].items() }

        if "n" in locals():
            soc = n.stores_t.e[-extended_hours-1:-extended_hours].squeeze().to_dict()

        print("using previous soc:")
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

        current_capacities = {f"{ct}-{key}" : value for key, value in historical_capacities.loc[date].items()}
        print("current capacities:")
        print(current_capacities)

        per_unit = derive_pu_availability(extended_df,
                                          current_capacities)

        future_capacities = { f"{ct}-{key}" : value for key,value in config["future_capacities"][ct].items() }

        n = prepare_network(per_unit,
                            future_capacities,
                            extended_df[[f"{ct}-load"]],
                            soc,
                            config)


        solve_network(n,
                      config,
                      solver_name)

        n.export_to_netcdf(fn,
                           float32=True, compression={'zlib': True, "complevel":9, "least_significant_digit":5})


def gurobi_present():

    try:
        import gurobipy
        gurobipy.Model()
    except:
        return False
    else:
        return True


def determine_solver_name(config):
    for solver_name in config["solver_names"]:
        if solver_name == "gurobi":
            if gurobi_present():
                return solver_name
        else:
            return solver_name


def copy_config(config,scenario_fn):

    results_dir = f"{config['results_dir']}/{config['scenario']}"

    if not os.path.isdir(results_dir):
        os.mkdir(results_dir)

    files = [
        "config.yaml",
        scenario_fn,
        "solve_myopic.py",
    ]

    for f in files:
        copy(f, results_dir)

if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    scenario_fn = sys.argv[1]

    with open(scenario_fn, 'r') as file:
        config.update(yaml.safe_load(file))

    config["scenario"] = scenario_fn[scenario_fn.find("-")+1:-5]

    copy_config(config,scenario_fn)

    solve_all(config)
