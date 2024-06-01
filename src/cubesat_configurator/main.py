from parapy.geom import Box
from parapy.gui import display

import pykep as pk
import paseos
from paseos import ActorBuilder, SpacecraftActor, GroundstationActor
import numpy as np

import concrete_classes.high_level as hl
import abstract_classes as ac


def testing():
    my_mission = hl.Mission(mission_lifetime=24, # months
                            orbit_type="SSO", # SSO, Polar, Equatorial, custom
                            custom_inclination=30, # deg
                            reqiured_GSD=50, # m
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
    
    print(f"{my_mission.cubesat.orbit.altitude} km")
    print(f"{my_mission.cubesat.orbit.inclination} deg")
    

    display(my_mission)

def paseos_test():
    my_mission = hl.Mission(mission_lifetime=24, # months
                            orbit_type="SSO", # SSO, Polar, Equatorial, custom
                            custom_inclination=30, # deg
                            reqiured_GSD=50, # m
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
    #INPUTS
    t0 = pk.epoch(0)
    pl_bandwidth = 100 # kbps
    bus_bandwidth = 10 # kbps
    starting_battery_capacity = 10 # Wh
    maximum_battery_capacity = 10 # Wh
    incoming_power = 4 # W
    solar_panel_efficiency = 0.25
    # derived 
    downlink_bw = pl_bandwidth + bus_bandwidth # kbps
    battery_charging_rate = incoming_power*solar_panel_efficiency # W

    print("Orbit: ")
    print(f'position vector: {my_mission.cubesat.orbit.position_vector}')
    print(f'velocity vector: {my_mission.cubesat.orbit.velocity_vector}')
    print("\nGroundstation: ")
    print(f"{my_mission.groundstation.latitude} deg")
    print(f"{my_mission.groundstation.longitude} deg")
    print(f"{my_mission.groundstation.elevation} m")
    print(f"epoch = {t0}")

    sat_actor = ActorBuilder.get_actor_scaffold(name="myCubeSat",
                                       actor_type=SpacecraftActor,
                                       epoch=t0)

    # Define the central body as Earth by using pykep APIs.
    earth = pk.planet.jpl_lp("earth")

    # Let's set the orbit of sat_actor.
    ActorBuilder.set_orbit(actor=sat_actor,
                        position=my_mission.cubesat.orbit.position_vector,
                        velocity=my_mission.cubesat.orbit.velocity_vector,
                        epoch=t0, 
                        central_body=earth
                        )
    # comm device
    ActorBuilder.add_comm_device(sat_actor, "link1", downlink_bw)

    # power
    ActorBuilder.set_power_devices(
        sat_actor, starting_battery_capacity, maximum_battery_capacity, battery_charging_rate
    )
    stored_power = []
    
    # Initialize PASEOS simulation
    sim = paseos.init_sim(sat_actor)
        
    #Create GroundstationActor
    ground_station = GroundstationActor(name="myGroundStation", epoch=t0)

    #Set the ground station at lat lon 79.002723 / 14.642972
    # and its elevation 0m
    ActorBuilder.set_ground_station_location(ground_station,
                                            latitude=79.002723,
                                            longitude=14.642972,
                                            elevation=0)
    # Add a communication device to the ground station
    ActorBuilder.add_comm_device(ground_station, "link1", 1)

    # Adding grndStation to PASEOS.
    sim.add_known_actor(ground_station)


if __name__ == '__main__':
    # testing()
    paseos_test()


