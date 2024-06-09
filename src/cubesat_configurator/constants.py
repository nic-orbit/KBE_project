import pykep as pk


class PaseosConfig:
    simulation_timestep = 60  # seconds
    start_epoch = pk.epoch_from_string("2024-august-01 08:00:00")
    earth = pk.planet.jpl_lp("earth")


class SystemConfig:
    system_margin = 0.2