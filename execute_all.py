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



import os, sys

scripts = [
    "download_data_smard.py",
    "solve_myopic.py",
    "concatenate_networks.py",
    "plot_networks.py",
    "generate_html.py",
    ]

for script in scripts:
    command = f"{sys.executable} {script}"
    print(f"executing {command}")
    os.system(command)
