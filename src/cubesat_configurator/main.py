from parapy.geom import Box
from parapy.gui import display
import pandas as pd
import os

import pykep as pk
import paseos
from paseos import ActorBuilder, SpacecraftActor, GroundstationActor
import numpy as np

from mission import Mission
from pprint import pprint

import constants


def paseos_test():
    my_mission = Mission(mission_lifetime=24, # months
                            orbit_type="Polar", # SSO, Polar, Equatorial, custom
                            custom_inclination=30, # deg
                            reqiured_GSD=100, # m
                            ground_station_selection=[58, 53, 49], # 58=Delft, 53=Havaii, 49=Kourou
                            req_pointing_accuracy=0.5, # deg
                            )
    print(my_mission.cubesat.orbit)

    pprint(my_mission.cubesat.simulate_first_orbit)

    print(my_mission.cubesat.min_downlink_data_rate)

    print(my_mission.cubesat.payload.sensor_length)

    display(my_mission)


def test():
    my_mission = Mission(mission_lifetime=24, # months
                            orbit_type="SSO", # SSO, Polar, Equatorial, custom
                            custom_inclination=30, # deg
                            reqiured_GSD=50, # m
                            ground_station_selection=[58], # Delft, Havaii, Kourou
                            req_pointing_accuracy=0.5, # deg
                            )
    display(my_mission)

if __name__ == '__main__':
    paseos_test()
    # test()
