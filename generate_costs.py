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


import urllib.request, pandas as pd, os

techdata_fn = "costs_2030.csv"

commit = "bc9ef42bc1d7b0313eb6cf429070d9a863502891"

if not os.path.isfile(techdata_fn):

    print("downloading:")
    url = f'https://raw.githubusercontent.com/PyPSA/technology-data/{commit}/outputs/{techdata_fn}'
    print(url)
    urllib.request.urlretrieve(url,
                               techdata_fn)

def annuity(lifetime,rate):
    if rate == 0.:
        return 1/lifetime
    else:
        return rate/(1. - 1. / (1. + rate)**lifetime)

cost_map = {'onshore': "onwind",
            'pv': "solar-utility",
            'offshore': "offwind",
            'battery': "battery inverter",
            'battery_energy': "battery storage",
            'hydrogen_electrolyser': "electrolysis",
            'hydrogen_turbine': "CCGT",
            'hydrogen_ocgt': "OCGT",
            'hydrogen_energy': 'hydrogen storage underground',
            'hydro': 'ror',
            'pumped_hydro': 'PHS'}

fn = "costs.csv"

if not os.path.isfile(fn):

    costs = pd.read_csv(techdata_fn,
                        index_col=[0,1])

    df = costs.loc[cost_map.values()].value.unstack().rename({ value: key for key,value in cost_map.items()})


    df = df[["FOM","investment","lifetime"]].fillna(0.)


    df.rename({"FOM": "FOM [%inv/a]",
               "investment" : "investment [€/kW(h)]",
               "lifetime" :"lifetime [a]"},
              axis=1,
              inplace=True)

    #use corrected cavern costs
    df.at["hydrogen_energy","investment [€/kW(h)]"] *= 0.1

    # adjust for inflation
    df["investment [€/kW(h)]"] *= 1.02**(2020-2015)
    df["discount rate [pu]"] = 0.07
    df["fixed [€/MW/a]"] = [1000*(annuity(v["lifetime [a]"],v["discount rate [pu]"])+v["FOM [%inv/a]"]/100.)*v["investment [€/kW(h)]"] for i,v in df.iterrows()]
    #df["capacity"] = config["future_capacities"]["DE"]


    df.to_csv(fn)
