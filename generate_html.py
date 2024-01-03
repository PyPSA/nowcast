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

import yaml, datetime, pandas as pd

# load templates folder to environment (security measure)
env = Environment(loader=FileSystemLoader('./'))



def generate_html(config):

    end_date = config["end_date"]

    if end_date == "today":
        end_date = datetime.date.today()
    elif end_date == "yesterday":
        end_date = datetime.date.today() - datetime.timedelta(days=1)

    date_index = pd.date_range(start=config["start_date"],
                               end=end_date)

    isocalendar = date_index.isocalendar()

    isocalendar["week_string"] = isocalendar.year.astype(str) + "-" + isocalendar.week.astype(str)
    weeks = isocalendar["week_string"].unique()[:-config["weeks_to_plot"]-1:-1]

    print(weeks)

    ct = config["countries"][0]

    # load the `index.jinja` template
    index_template = env.get_template('template.html')
    output_from_parsed_template = index_template.render(name=config["scenario"],
                                                        future_capacities=config["future_capacities"][ct],
                                                        results_dir=f"{config['results_dir']}/{config['scenario']}",
                                                        weeks=weeks,
                                                        n_weeks=len(weeks),
                                                        ct=ct)

    # write the parsed template
    with open(f"{config['html_dir']}/{config['scenario']}.html", "w") as chap_page:
        chap_page.write(output_from_parsed_template)


if __name__ == "__main__":

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    print(config)

    generate_html(config)
