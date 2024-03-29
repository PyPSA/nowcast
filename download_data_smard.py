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

from helpers import get_date_index, get_existing_dates

# DE-load seems to be actual load rather than forecast
data_to_retrieve = {"DE-load" : 410,
                    "DE-pv" : 125,
                    "DE-onshore" : 123,
                    "DE-offshore" : 3791,
                    "DE-hydro" : 1226}




def get_smard_series(filter, uts, region="DE", resolution="quarterhour"):

    url = f"https://www.smard.de/app/chart_data/{filter}/{region}/{filter}_{region}_{resolution}_{uts*1000}.json"

    print(url)

    # Sending a GET request to the URL
    response = requests.get(url)

    # Checking if the request was successful
    if response.status_code == 200:
        # Converting the JSON response to a Python dictionary
        data = response.json()
    else:
        print("Failed to retrieve data")
        return None

    idx, values = zip(*data["series"])

    s = pd.Series(values, idx)

    s.index = pd.to_datetime(s.index/1e3,unit='s').tz_localize('UTC')#.tz_convert('Europe/Berlin')

    return s



def get_previous_monday(date_string):
    """date_string is e.g. '2023-01-25'"""
    dt = datetime.datetime.strptime(date_string, '%Y-%m-%d').astimezone(pytz.timezone("Europe/Berlin"))
    return dt - datetime.timedelta(dt.weekday())


def get_week_data(data_to_retrieve, date_string, ct):
    """date_string is e.g. '2023-01-25'"""
    print(f"you passed the date {date_string}")
    monday = get_previous_monday(date_string)
    print(f"the previous monday was {monday}")
    uts = int(monday.timestamp())
    print(f"unix timestamp was {uts}")
    #print(uts*1e3 in all_uts)

    df = pd.DataFrame()
    for key, value in data_to_retrieve.items():
        df[key] = get_smard_series(value, uts, region=ct, resolution="hour")

    return df



def get_all_data(config):

    ct = config["countries"][0]

    dir_name = config["weather_dir"]

    if not os.path.isdir(dir_name):
        os.mkdir(dir_name)

    already = get_existing_dates(dir_name,
                                 r"DE-day-(\d{4}-\d{2}-\d{2}).csv")

    date_index = get_date_index(config)

    dates_to_process = date_index.difference(already)

    print(f"dates_to_process: {dates_to_process}")

    for date in dates_to_process:
        date_string = str(date.date())
        print(f"Getting data for {date_string}")

        monday = get_previous_monday(date_string)

        day_fn = f"{dir_name}/DE-day-{date_string}.csv"
        week_fn = f"{dir_name}/DE-week-{monday.date()}.csv"

        download = False

        if os.path.isfile(week_fn):
            print(f"week file {week_fn} already exists")
            df = pd.read_csv(week_fn,index_col=0,parse_dates=True)
            if df.loc[date_string].isna().any().any():
                print(f"...but data is missing for {date_string}, so re-downloading data")
                download = True
        else:
            print(f"week file {week_fn} doesn't exist, downloading data")
            download = True

        if download:
            df = get_week_data(data_to_retrieve, date_string, ct)
            df.to_csv(week_fn)

        if df.loc[date_string].isna().any().any():
            print(f"warning, data is missing for {date_string}:")
            print(df.loc[date_string])

        df.index = df.index.tz_convert('Europe/Berlin')
        df_day = df.loc[date_string]
        df_day.index = df_day.index.tz_convert('UTC')
        df_day.to_csv(day_fn)

if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    get_all_data(config)
