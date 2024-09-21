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


import pypsa, yaml, pandas as pd, os, datetime, sys, numpy as np

from shutil import copy

from helpers import get_date_index

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


def prepare_base_network(config):

    n = pypsa.Network()

    for ct in config["countries"]:

        future_capacities = { f"{ct}-{key}" : value for key,value in config["future_capacities"][ct].items()}

        n.add("Bus",
              f"{ct}-electricity",
              carrier="electricity")

        n.add("Load",
              f"{ct}-load",
              bus=f"{ct}-electricity",
              carrier="load")

        bevs = future_capacities[f"{ct}-battery_electric_vehicles"]
        if bevs > 0:
            n.add("Bus",
                  f"{ct}-bev",
                  carrier="bev")

            n.add("Load",
                  f"{ct}-bev_demand",
                  bus=f"{ct}-bev",
                  carrier="bev_demand")

            n.add("Link",
                  f"{ct}-bev_charger",
                  bus0=f"{ct}-electricity",
                  bus1=f"{ct}-bev",
                  p_nom=config['bev_charger_power']*bevs*1e3,
                  ramp_limit_up=config['bev_demand_yearly']/8760/config['bev_charger_power']*1e3*config['bev_ramping'],
                  ramp_limit_down=config['bev_demand_yearly']/8760/config['bev_charger_power']*1e3*config['bev_ramping'],
                  carrier="bev_charger")

            n.add("Store",
                  f"{ct}-bev",
                  bus=f"{ct}-bev",
                  e_nom_cyclic=True,
                  e_nom=config['bev_battery_size']*bevs*1e3,
                  carrier="bev")

        heat_pumps = future_capacities[f"{ct}-heat_pumps"]
        if heat_pumps > 0:
            n.add("Bus",
                  f"{ct}-heat",
                  carrier="heat")

            n.add("Load",
                  f"{ct}-heat_demand",
                  bus=f"{ct}-heat",
                  carrier="heat_demand")

            n.add("Link",
                  f"{ct}-heat_pumps",
                  bus0=f"{ct}-electricity",
                  bus1=f"{ct}-heat",
                  carrier="heat_pumps",
                  ramp_limit_up=config['heat_pump_ramping'],
                  ramp_limit_down=config['heat_pump_ramping'],
                  p_nom=config['heat_pump_power']*heat_pumps*1e3)

            n.add("Store",
                  f"{ct}-heat_storage",
                  bus=f"{ct}-heat",
                  e_nom_cyclic=True,
                  e_nom=config['heat_storage_per_heat_pump']*heat_pumps*1e3,
                  standing_loss=config['heat_storage_standing_loss'],
                  carrier="heat_storage")


        n.add("Generator",
              f"{ct}-load_shedding",
              bus=f"{ct}-electricity",
              p_nom=1e6,
              marginal_cost=config["voll"],
              carrier="load_shedding")

        for key in future_capacities:
            if key[:19] == f"{ct}-elastic_decrease":
                price = float(key[20:])
                decrease = future_capacities[key]*1e3
                print(f"decrease: {decrease} for price {price}")
                n.add("Generator",
                      f"{ct}-load_decrease-{int(price)}",
                      bus=f"{ct}-electricity",
                      p_nom=decrease,
                      marginal_cost=price,
                      carrier="load_decrease")
            elif key[:19] == f"{ct}-elastic_increase":
                price = float(key[20:])
                increase = future_capacities[key]*1e3
                print(f"increase: {increase} for price {price}")
                n.add("Generator",
                      f"{ct}-load_increase-{int(price)}",
                      bus=f"{ct}-electricity",
                      p_nom=-increase,
                      p_max_pu=0.,
                      p_min_pu=1.,
                      marginal_cost=price,
                      carrier="load_increase")

        for vre_tech in config["vre_techs"]:
            name = f"{ct}-{vre_tech}"
            n.add("Generator",
                  name,
                  bus=f"{ct}-electricity",
                  p_nom=future_capacities[name]*1e3,
                  marginal_cost=config[f"mc-{vre_tech}"],
                  carrier=vre_tech)


        n.add("Bus",
              f"{ct}-pumped_hydro",
              carrier="pumped_hydro")

        name = f"{ct}-pumped_hydro_energy"
        n.add("Store",
              name,
              bus = f"{ct}-pumped_hydro",
              carrier="pumped_hydro_energy",
              e_nom=future_capacities[name]*1e3)

        n.add("Link",
              f"{ct}-pumped_hydro_charger",
              bus0 = f"{ct}-electricity",
              bus1 = f"{ct}-pumped_hydro",
              carrier="pumped_hydro_charger",
              efficiency = config["pumped_hydro_efficiency_charging"],
              p_nom=future_capacities[f"{ct}-pumped_hydro"]*1e3)

        n.add("Link",
              f"{ct}-pumped_hydro_discharger",
              bus0 = f"{ct}-pumped_hydro",
              bus1 = f"{ct}-electricity",
              carrier="pumped_hydro_discharger",
              efficiency = config["pumped_hydro_efficiency_discharging"],
              p_nom=future_capacities[f"{ct}-pumped_hydro"]*1e3)


        n.add("Bus",
                    f"{ct}-battery",
                    carrier="battery")

        name = f"{ct}-battery_energy"
        n.add("Store",
                    name,
                    bus = f"{ct}-battery",
                    carrier="battery_energy",
                    e_nom=future_capacities[name]*1e3)

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

        name = f"{ct}-hydrogen_demand"
        n.add("Load",
              name,
              bus=f"{ct}-hydrogen",
              carrier="hydrogen_demand",
              p_set=future_capacities[name]*1e3)

        name = f"{ct}-hydrogen_energy"
        n.add("Store",
                    name,
                    bus=f"{ct}-hydrogen",
                    carrier="hydrogen_energy",
                    e_nom=future_capacities[name]*1e3,
                    marginal_cost=config["hydrogen_value"])


        #add noise on efficiency to lift dispatch degeneracy
        #this helps stabilise results
        deviation = config['hydrogen_converter_efficiency_noise']
        intervals = config['hydrogen_converter_degeneracy']
        adjustments = np.arange(-deviation,deviation + 1e-5,deviation*2/(intervals-1))

        for i,adjustment in enumerate(adjustments):
            n.add("Link",
                  f"{ct}-hydrogen_turbine-{i}",
                  bus0=f"{ct}-hydrogen",
                  bus1=f"{ct}-electricity",
                  carrier="hydrogen_turbine",
                  p_nom=future_capacities[f"{ct}-hydrogen_turbine"]*1e3/config["hydrogen_turbine_efficiency"]/intervals,
                  efficiency=config["hydrogen_turbine_efficiency"] + adjustment)
            n.add("Link",
                  f"{ct}-hydrogen_electrolyser-{i}",
                  bus0=f"{ct}-electricity",
                  bus1=f"{ct}-hydrogen",
                  carrier="hydrogen_electrolyser",
                  p_nom=future_capacities[f"{ct}-hydrogen_electrolyser"]*1e3/intervals,
                  efficiency=config["hydrogen_electrolyser_efficiency"] + adjustment)


    n.consistency_check()
    return n



def attach_time_series(n, config, per_unit, load, heat_profile, cop, bev_profile):

    ct = config["countries"][0]

    heat_pumps = config["future_capacities"][ct]["heat_pumps"]

    bevs = config["future_capacities"][ct]["battery_electric_vehicles"]

    if heat_pumps > 0:
        load = pd.concat((load, pd.DataFrame({f"{ct}-heat_demand" : pd.Series(config['heat_pump_demand_yearly']*heat_profile*heat_pumps*1e6, load.index)})),
                         axis=1)

    if bevs > 0:
        load = pd.concat((load, bev_profile[["bev_demand"]].rename(lambda n: f"{ct}-{n}",axis=1)*bevs*1e6*config['bev_demand_yearly']),
                         axis=1)

    efficiency = pd.DataFrame({f"{ct}-heat_pumps" : cop})

    links_p_max_pu = bev_profile[["bev_availability"]].rename({"bev_availability" : f"{ct}-bev_charger"}, axis=1)

    if n.snapshots[0] == "now":
        n.generators_t.p_max_pu = per_unit
        n.loads_t.p_set = load
        n.links_t.efficiency = efficiency
        n.links_t.p_max_pu = links_p_max_pu
        n.set_snapshots(per_unit.index)
    else:
        #first clip any excess
        snapshots = pd.date_range(n.snapshots[0],
                             per_unit.index[0] - datetime.timedelta(hours=1),
                             freq="h")
        n.set_snapshots(snapshots)
        n.generators_t.p_max_pu = pd.concat((n.generators_t.p_max_pu,
                                             per_unit))
        n.loads_t.p_set = pd.concat((n.loads_t.p_set,
                                     load))
        n.links_t.efficiency = pd.concat((n.links_t.efficiency,
                                          efficiency))
        n.links_t.p_max_pu = pd.concat((n.links_t.p_max_pu,
                                        links_p_max_pu))
        snapshots = pd.date_range(n.snapshots[0],
                             per_unit.index[-1],
                             freq="h")
        n.set_snapshots(snapshots)


def apply_soc(n, soc):
    for store,value in soc.items():
        n.stores.at[store,"e_initial"] = value


def solve_network(n, snapshots, config, solver_name):

    ct = config["countries"][0]

    n.optimize.create_model(snapshots)

    n.model.objective += -(config["dayahead_discount_factor"]*
                           config["hydrogen_value"]/
                           config["hydrogen_turbine_efficiency"]*
                           (n.model["Store-e"].loc[n.snapshots[-1],f"{ct}-battery_energy"]
                            + n.model["Store-e"].loc[n.snapshots[-1],f"{ct}-pumped_hydro_energy"]))

    status, termination_condition = n.optimize.solve_model(solver_name=solver_name,
                                                           solver_options=config["solver_options"][solver_name],
                                                           log_fn=config["solver_logfile"])

    if status == "warning" or "infeasible" in termination_condition:
        print(f"optimisation error, exiting, status: {status}, condition: {termination_condition}")
        sys.exit()

def solve_all(config):

    solver_name = determine_solver_name(config)
    print(f"using solver {solver_name}")

    ct = config["countries"][0]

    fn = f"{config['results_dir']}/{config['scenario']}/{ct}.nc"

    if not os.path.isfile(fn):
        print(f"{fn} doesn't exist yet, building from scratch")
        n = prepare_base_network(config)
    else:
        n = pypsa.Network(fn)

    extended_hours = config["extended_hours"]

    date_index = get_date_index(config)

    historical_capacities = interpolate_historical_capacities(config, ct, date_index)

    if config["force_restart_date"] != "none":
        dates_to_process = pd.date_range(start=config["force_restart_date"],
                                         end=date_index[-1])
    elif n.snapshots[0] == "now":
        dates_to_process = date_index
    else:
        tz = config["time_zone"][ct]
        dates_already = pd.Index(n.snapshots.tz_localize("UTC").tz_convert(tz).date).unique()
        dates_to_process = pd.date_range(start=dates_already[-1] + datetime.timedelta(days=1),
                                         end=date_index[-1])

    print(f"dates to process: {dates_to_process}")
    if dates_to_process.empty:
        return

    for date in dates_to_process:

        date_string = str(date.date())

        print(f"Solving date {date_string}")

        weather_fn = f"{config['weather_dir']}/{ct}-day-{date_string}-corrected.csv"
        if not os.path.isfile(weather_fn):
            print(f"{weather_fn} is missing, skipping {date_string}")
            continue

        df = pd.read_csv(weather_fn,
                         parse_dates=True,
                         index_col=0).tz_convert(tz=None)

        extended_df = extend_df(df,
                                extended_hours)

        current_capacities = {f"{ct}-{key}" : value for key, value in historical_capacities.loc[date].items()}
        print("current capacities:")
        print(current_capacities)

        per_unit = derive_pu_availability(extended_df,
                                          current_capacities)

        heat_profile = pd.read_csv(os.path.join(config['weather_dir'],
                                                f'{ct}-heat_profile.csv'),
                                   parse_dates=True,
                                   index_col=0).squeeze().reindex(per_unit.index, method="bfill")

        bev_profile = pd.read_csv(os.path.join(config['weather_dir'],
                                                f'{ct}-bev_profile.csv'),
                                  parse_dates=True,
                                  index_col=0).reindex(per_unit.index, method="bfill")

        cop = pd.read_csv(os.path.join(config['weather_dir'],
                                       f'{ct}-heat_pump_cop.csv'),
                          parse_dates=True,
                          index_col=0).squeeze().reindex(per_unit.index, method="bfill")

        attach_time_series(n,
                           config,
                           per_unit,
                           extended_df[[f"{ct}-load"]],
                           heat_profile,
                           cop,
                           bev_profile)

        if date == date_index[0]:
            soc = { f"{ct}-{key}" : float(value) for key,value in config["soc_start"][ct].items() }
        else:
            previous_hour = per_unit.index[0] - datetime.timedelta(hours=1)
            soc = n.stores_t.e.loc[previous_hour].to_dict()

        print("using previous soc:")
        print(soc)

        apply_soc(n,soc)

        solve_network(n,
                      per_unit.index,
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

    results_dir = f"{config['results_dir']}"

    if not os.path.isdir(results_dir):
        os.mkdir(results_dir)

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
