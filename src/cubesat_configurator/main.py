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

def test():
    t0 = constants.PaseosConfig.start_epoch
    sat_actor = ActorBuilder.get_actor_scaffold(name="myCubeSat",
                                        actor_type=SpacecraftActor,
                                        epoch=t0)
    ActorBuilder.set_orbit(actor=sat_actor,
                            position=[500000, 0, 0],
                            velocity=[0, 7660, 0],
                            epoch=t0, 
                            central_body=constants.PaseosConfig.earth)
    
    ActorBuilder.add_comm_device(actor=sat_actor,
                                 device_name="myCommDevice",
                                bandwidth_in_kbps=100)
    
    gs_actor = ActorBuilder.get_actor_scaffold(name="myGroundStation",
                                        actor_type=GroundstationActor,
                                        epoch=t0)
    
    ActorBuilder.set_ground_station_location(gs_actor,
                                            latitude=50,
                                            longitude=4,
                                            elevation=0,
                                            minimum_altitude_angle=5)
    
    info = paseos.get_communication_window(sat_actor, "myCommDevice", gs_actor)
    print(info)
                                

def paseos_test():
    my_mission = Mission(mission_lifetime=24, # months
                            orbit_type="SSO", # SSO, Polar, Equatorial, custom
                            custom_inclination=30, # deg
                            reqiured_GSD=50, # m
                            ground_station_selection=[58], # Delft, Havaii, Kourou
                            req_pointing_accuracy=0.5, # deg
                            instrument_min_operating_temp=-10, # deg C
                            instrument_max_operating_temp=40, # deg C
                            instrument_data_rate=100, # kbps
                            instrument_focal_length=15, # mm
                            instrument_pixel_size=2,  # µm
                            instrument_height=50, # mm
                            instrument_width=100, # mm
                            instrument_length=100, # mm
                            instrument_power_consumption=10, # W
                            instrument_mass=1, # kg
                            )
    print(my_mission.cubesat.orbit.period)
    pprint(my_mission.cubesat.simulate_first_orbit)
    pprint(my_mission.cubesat.min_downlink_data_rate)
    print(my_mission.cubesat.system_data_rate)


def test2():
    my_mission = Mission()
    display(my_mission)

if __name__ == '__main__':
    paseos_test()
    # test2()