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

import pytz, datetime, pandas as pd, yaml, os

def generate_periodic_profiles(dt_index, nodes, weekly_profile, localize=None):
    """
    Give a 24*7 long list of weekly hourly profiles, generate this for each
    country for the period dt_index, taking account of time zones and summer
    time.
    """
    weekly_profile = pd.Series(weekly_profile, range(24 * 7))

    week_df = pd.DataFrame(index=dt_index, columns=nodes)

    for node in nodes:
        timezone = pytz.timezone(pytz.country_timezones[node[:2]][0])
        tz_dt_index = dt_index.tz_convert(timezone)
        week_df[node] = [24 * dt.weekday() + dt.hour for dt in tz_dt_index]
        week_df[node] = week_df[node].map(weekly_profile)

    week_df = week_df.tz_localize(localize)

    return week_df

def build_heat_demand(config):

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

    daily_t = mean_t.resample("D").mean()

    heat_demand_profile = (config["heating_temperature_threshold"] - daily_t).clip(lower=0.)

    hourly_heat_demand_profile = heat_demand_profile.reindex(mean_t.index, method="ffill")

    heat_profile = pd.read_csv("heat_load_profile_BDEW.csv",
                               index_col=0)

    weekday = list(heat_profile[f"residential space weekday"])
    weekend = list(heat_profile[f"residential space weekend"])
    weekly_profile = weekday * 5 + weekend * 2
    intraday_year_profile = generate_periodic_profiles(
        mean_t.index.tz_localize("UTC"),
        nodes=["DE"],
        weekly_profile=weekly_profile,
    )
    hourly_heat_demand = hourly_heat_demand_profile*intraday_year_profile.squeeze()

    hourly_heat_demand_with_water = hourly_heat_demand + config['hot_water_fraction']/(1 - config['hot_water_fraction'])*hourly_heat_demand.mean()

    # with 1 unit/a demand
    final_profile = len(hourly_heat_demand_with_water)/8766/hourly_heat_demand_with_water.sum()*hourly_heat_demand_with_water

    final_profile.to_csv(os.path.join(dir_name,
                                      f"{ct}-heat_profile.csv"))

if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    build_heat_demand(config)
