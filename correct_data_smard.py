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


import pandas as pd, yaml, os, datetime

from urllib.request import urlretrieve

from helpers import get_date_index, get_existing_dates


def get_ageb_data(config, date_index):

    ct = config["countries"][0]

    years = date_index.year.unique()

    fn = "STRERZ_Abgabe-12-2023.xlsx"

    if not os.path.isfile(fn):
        urlretrieve(f"https://ag-energiebilanzen.de/wp-content/uploads/2023/10/{fn}",fn)

    ageb = pd.read_excel(fn,
                         sheet_name="STRERZ (netto)",
                         header=2,
                         index_col=1).iloc[:-6,1:]

    ageb_brutto = pd.read_excel(fn,
                                sheet_name="STRERZ (brutto)",
                                header=2,
                                index_col=1).iloc[:-8,1:-3]

    ageb.columns = ageb.columns.astype(int)
    ageb_brutto.columns = ageb_brutto.columns.astype(int)

    rename = {" - Wind onshore" : "onshore",
              " - Wind offshore" : "offshore",
              " - Photovoltaik" : "pv",
              " - Wasserkraft2)" : "hydro"}

    ind = f"{ct}-" + pd.Index(config["vre_techs"])

    ageb_sel = ageb.rename({ key : f"{ct}-{value}" for key,value in rename.items()},axis=0).loc[ind,years[:-2]].astype(float)

    ageb_sel.loc[f"{ct}-load"] = (ageb.loc["Nettostromerzeugung exkl. PSE"] + ageb_brutto.loc["Stromimportsaldo"]).loc[years[:-2]].astype(float)

    return ageb_sel



def get_smard_yearly_data(config, date_index):

    ct = config["countries"][0]

    full = pd.DataFrame(dtype=float)

    for date in date_index:

        date_string = str(date.date())

        weather_fn = f"{config['weather_dir']}/{ct}-day-{date_string}.csv"

        if not os.path.isfile(weather_fn):
            print(f"{weather_fn} is missing, skipping {date_string}")
            continue

        df = pd.read_csv(weather_fn,
                         parse_dates=True,
                         index_col=0)
        full = pd.concat((full,df))

    years = date_index.year.unique()[:-2]

    year_df = pd.DataFrame(index=years,columns=full.columns,
                           dtype=float)

    for year in years:
        year_df.loc[year] = full.loc[full.index.year == year].sum()

    return year_df.T/1e6


def get_correction_factor(config, date_index):

    ct = config["countries"][0]

    correction_fn = "correction_factors.csv"

    if not os.path.isfile(correction_fn):

        # net generation in TWh/a
        ageb_data = get_ageb_data(config, date_index)

        smard_yearly = get_smard_yearly_data(config, date_index)
        print(ageb_data)
        print(smard_yearly)

        correction_factor = ageb_data/smard_yearly.loc[ageb_data.index]

        years = date_index.year.unique()

        correction_factor = correction_factor.reindex(years,
                                                      axis=1,
                                                      method='ffill')

        correction_factor.to_csv(correction_fn)

    correction_factor = pd.read_csv(correction_fn,
                                    index_col=0)

    correction_factor.columns = correction_factor.columns.astype(int)

    return correction_factor


def correct_data(config, correction_factor, date_index):

    ct = config["countries"][0]

    dir_name = config["weather_dir"]

    if not os.path.isdir(dir_name):
        os.mkdir(dir_name)

    already = get_existing_dates(dir_name,
                                 r"DE-day-(\d{4}-\d{2}-\d{2})-corrected.csv")

    dates_to_process = date_index.difference(already)

    print(f"dates_to_process: {dates_to_process}")

    for date in dates_to_process:
        date_string = str(date.date())

        correction_factors = correction_factor[date.year]

        weather_fn = f"{config['weather_dir']}/{ct}-day-{date_string}.csv"

        df = pd.read_csv(weather_fn,
                         parse_dates=True,
                         index_col=0)

        corrected = df.multiply(correction_factors)

        corrected_fn = f"{config['weather_dir']}/{ct}-day-{date_string}-corrected.csv"

        corrected.to_csv(corrected_fn)

if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    date_index = get_date_index(config)

    correction_factor = get_correction_factor(config, date_index)

    print("Applying correction factors:")

    print(correction_factor)

    correct_data(config, correction_factor, date_index)
