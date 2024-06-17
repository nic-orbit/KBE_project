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
    relative_animation_output_path = os.path.join('animations', 'orbit_animation')
    animation_output_path = os.path.join(script_dir, relative_animation_output_path)
    

class Thermal:
    boltzmann_constant = 5.67e-8  # W/m^2K^4
    earth_avg_temp = 288  # K
    earth_radius = 6371e3  # m
    earth_albedo = 0.3
    e_Earth = 0.9
    S = 1361  # W/m^2
    
    sa_coatings_relative_path = os.path.join('data', 'thermal_coatings', 'coatings_NASA_solarcells.csv')
    sa_coatings_path = os.path.join(script_dir, sa_coatings_relative_path)
    body_coatings_relative_path = os.path.join('data', 'thermal_coatings', 'coatings_SMAD_no_dupl.csv')
    body_coatings_path = os.path.join(script_dir, body_coatings_relative_path)


class SystemConfig:
    system_margin = 0.2


class GenericConfig:
    relative_step_file_path = os.path.join(script_dir, 'step_files', 'cubesat_configuration.step')
    step_file_location = os.path.join(script_dir, relative_step_file_path)

    relative_report_template_path = os.path.join('report', 'Report_Template.docx')
    report_template_path = os.path.join(script_dir, relative_report_template_path)

    relative_report_output_path = os.path.join('report', 'CubeSat_Configurator_Report.docx')
    report_output_path = os.path.join(script_dir, relative_report_output_path)

class Power:
    duty_cycle = 0.1
    F_d=0.0092
    I_d=0.955