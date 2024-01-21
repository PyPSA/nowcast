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

from jinja2 import Template, Environment, FileSystemLoader

import yaml, os, pandas as pd, datetime

from helpers import get_last_days

# load templates folder to environment (security measure)
env = Environment(loader=FileSystemLoader('./'))



def generate_index():

    scenarios = {}

    for fn in os.listdir("./"):
        if fn[:9] == "scenario-" and fn[-5:] == ".yaml":
            scenario = fn[9:-5]
            with open(fn, 'r') as file:
                config = yaml.safe_load(file)
            scenarios[scenario] = {key: config[key] for key in ["name","description"]}

    print(scenarios)

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    preferred_order = pd.Index(config["preferred_scenario_order"])

    scenario_order = pd.Index(list(scenarios.keys()))

    new_scenario_order = preferred_order.intersection(scenario_order).append(scenario_order.difference(preferred_order))

    print(new_scenario_order)


    date_strings = get_last_days(config).astype(str)

    ct = config["countries"][0]

    days_fn = f"{ct}-days-{date_strings[0]}-{date_strings[-1]}-supply.png"

    # load the `index.jinja` template
    index_template = env.get_template('index-template.html')
    output_from_parsed_template = index_template.render(scenarios=scenarios,
                                                        scenario_order=list(new_scenario_order),
                                                        results_dir=config['results_dir'],
                                                        days_fn=days_fn)


    # write the parsed template
    with open(f"index.html", "w") as chap_page:
        chap_page.write(output_from_parsed_template)


if __name__ == "__main__":

    generate_index()
