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


import pandas as pd, pytz, yaml, os, datetime, requests

from helpers import get_date_index

def get_open_meteo(locations, start_date, end_date, historic=False):

    latitude = locations["latitude"].astype(str).str.cat(sep=",")
    longitude = locations["longitude"].astype(str).str.cat(sep=",")

    if historic:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={latitude}&longitude={longitude}&start_date={start_date}&end_date={end_date}&hourly=temperature_2m"
    else:
        past_days = (datetime.date.today() - start_date).days
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=temperature_2m&past_days={past_days}"

    print(url)

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
    else:
        print("Failed to retrieve data")

    index = pd.to_datetime(data[0]['hourly']['time'])

    temperature = pd.DataFrame(index=index,
                               dtype=float)

    for i,ind in enumerate(data):
        temperature[locations.index[i]] = ind["hourly"]["temperature_2m"]

    return temperature.loc[str(start_date):str(end_date)]


def get_all_data(config):

    ct = config["countries"][0]

    locations = pd.read_csv("DE-bundesländer.csv",
                            header=None,
                            index_col=0)
    locations.columns = ["population","latitude","longitude"]
    locations["population"] = locations["population"].astype(int)

    dir_name = config["weather_dir"]

    if not os.path.isdir(dir_name):
        os.mkdir(dir_name)

    fn = os.path.join(dir_name,
                      f"{ct}-temperature.csv")

    date_index = get_date_index(config)

    if not os.path.isfile(fn):
        dates_to_process = date_index
        temperature = pd.DataFrame(dtype=float)
    else:
        temperature = pd.read_csv(fn,
                                  index_col=0,
                                  parse_dates=True)
        already = pd.Index(temperature.index.date).unique()
        dates_to_process = date_index.difference(already)

    print(f"dates_to_process: {dates_to_process}")

    days_ago = pd.Series((pd.DatetimeIndex([datetime.date.today()]*len(dates_to_process))-dates_to_process).days,
                         dates_to_process)

    if (days_ago > 1).any():
        historic_days = days_ago[days_ago > 1].index
        historic = get_open_meteo(locations,
                                  historic_days[0].date(),
                                  historic_days[-1].date(),
                                  historic=True)
        temperature = pd.concat([temperature,historic])
        already = pd.Index(temperature.index.date).unique()
        dates_to_process = date_index.difference(already)

    print(f"dates_to_process: {dates_to_process}")

    if not dates_to_process.empty:
        recent = get_open_meteo(locations,
                                dates_to_process[0].date(),
                                dates_to_process[-1].date(),
                                historic=False)
        temperature = pd.concat([temperature,recent])

    temperature.to_csv(fn)

if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    get_all_data(config)
