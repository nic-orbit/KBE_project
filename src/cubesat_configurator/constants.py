import pykep as pk
import os

script_dir = os.path.dirname(__file__)


class PaseosConfig:
    simulation_timestep = 60  # seconds
    start_epoch = pk.epoch_from_string("2024-august-01 08:00:00")
    earth = pk.planet.jpl_lp("earth")
    days_to_simulate = 2  # days
    relative_plots_path = os.path.join(script_dir, 'plots', 'simulation_plots.png')
    simulation_plots_location = os.path.join(script_dir, relative_plots_path)



class SystemConfig:
    system_margin = 0.2