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

from jinja2 import Template, Environment, FileSystemLoader

import yaml, datetime, pandas as pd, sys, os

from collections import OrderedDict

from helpers import get_date_index, get_last_days

# load templates folder to environment (security measure)
env = Environment(loader=FileSystemLoader('./'))



def generate_html(config):

    date_index = get_date_index(config)

    isocalendar = date_index.isocalendar()

    isocalendar["week_string"] = isocalendar.year.astype(str) + "-" + isocalendar.week.astype(str)
    weeks = isocalendar["week_string"].unique()[:-config["weeks_to_plot"]-1:-1]

    print(weeks)

    ct = config["countries"][0]

    current_capacities = pd.DataFrame(config["historical_capacities"][ct]).T
    current_capacities = current_capacities.iloc[-1].to_dict()
    current_capacities.update({"pumped_hydro" : 9.6,
                               "pumped_hydro_energy" : 50,
                               "battery" : "<1",
                               "battery_energy" : "<10",
                               "hydrogen_electrolyser" : "<1",
                               "hydrogen_turbine" : 0,
                               "hydrogen_energy" : "<1"})

    results_dir = f"{config['results_dir']}/{config['scenario']}"

    statistics = pd.read_csv(os.path.join(results_dir,f"{ct}-full-statistics.csv"),
                             index_col=0).squeeze()
    statistics.index = statistics.index.str.replace("€","&euro;")
    statistics = statistics.to_dict(into=OrderedDict)


    dates = get_last_days(config).astype(str)
    days_fn = f"{ct}-days-{dates[0]}-{dates[-1]}"

    # load the `index.jinja` template
    index_template = env.get_template('template.html')
    output_from_parsed_template = index_template.render(config=config,
                                                        current_capacities=current_capacities,
                                                        results_dir=results_dir,
                                                        weeks=weeks,
                                                        n_weeks=len(weeks),
                                                        ct=ct,
                                                        days_fn=days_fn,
                                                        statistics=statistics)

    # write the parsed template
    with open(f"{config['html_dir']}/{config['scenario']}.html", "w") as chap_page:
        chap_page.write(output_from_parsed_template)


if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    scenario_fn = sys.argv[1]

    with open(scenario_fn, 'r') as file:
        config.update(yaml.safe_load(file))

    config["scenario"] = scenario_fn[scenario_fn.find("-")+1:-5]

    generate_html(config)
