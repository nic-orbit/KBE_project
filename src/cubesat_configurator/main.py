from parapy.geom import Box
from parapy.gui import display

import pykep as pk
import paseos
from paseos import ActorBuilder, SpacecraftActor, GroundstationActor
import numpy as np

import concrete_classes.high_level as hl
import abstract_classes as ac
import paseos_parser as pp

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
                            orbit_type="Polar", # SSO, Polar, Equatorial, custom
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
    t0 = pk.epoch_from_string("2024-june-01 08:00:00")
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
    #print orbital period
    print(f"orbital period: {my_mission.cubesat.orbit.period} s")
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
    gs_1 = GroundstationActor(name="Delft", epoch=t0)
    gs_2 = GroundstationActor(name="Korou", epoch=t0)

    #Set the ground station at lat lon 52.0116 / 4.3571 ( Delft, Netherlands)
    # and its elevation 0m
    ActorBuilder.set_ground_station_location(gs_1,
                                            latitude=52.0116,
                                            longitude=4.3571,
                                            elevation=0, 
                                            minimum_altitude_angle=5
                                            )
    ActorBuilder.set_ground_station_location(gs_2,
                                            latitude=5.171,
                                            longitude=-52.690,
                                            elevation=0, 
                                            minimum_altitude_angle=5
                                            )
    
    # Add a communication device to the ground station
    # ActorBuilder.add_comm_device(ground_station_actor, "link1", 1)

    # Adding grndStation to PASEOS.
    sim.add_known_actor(gs_1)
    sim.add_known_actor(gs_2)

    # List of ground stations
    list_of_gs = [gs_1, gs_2]


    data = 0
    data_through_time = []
    eclipse_time = 0
    
    gs_info_delft = pp.GroundContactInfo()
    gs_info_korou = pp.GroundContactInfo()

    total_comm_window = 0
    T = my_mission.cubesat.orbit.period
    # simulation timestep
    dt = 10 # s
    # number of orbits to simulate = 1 day / orbital period = Number of orbits in a day
    orbits_to_simulate = np.ceil(24 * 60 * 60 / T)
    comm_power_consumption = 6 # W

    runs = round(T / dt * orbits_to_simulate)
    print(f"runs: {runs}")
    n_increments = 100
    incr = np.round(runs / n_increments, 0)
    print(f"incr: {incr}")

    
    # print simulation parameters
    print(
        "-----------------------------------------------------\n"
        f" starting simulation for {orbits_to_simulate} orbits with {runs} runs  \n"
        "-----------------------------------------------------"
    )
    verbose = False

    for i in range(runs):
        
        # print progress
        if i % incr == 0 and verbose:
            print(f"progress: {np.round(i / runs * 100, 2)}%")
            print(f"eclipse time: {eclipse_time} s")
            print(f"total comm window: {total_comm_window} s")
            show = True
        else:
            show = False
        eclipse_flag = sat_actor.is_in_eclipse()
        if eclipse_flag:
            eclipse_time += dt
            if show:
                print("in eclipse")

        delft_contact = gs_info_delft.has_link_to_ground_station(sat_actor, gs_1)
        korou_contact = gs_info_korou.has_link_to_ground_station(sat_actor, gs_2)
        if delft_contact or korou_contact:
            total_comm_window += dt
            if show:
                print("in contact with Ground Station")

        # advance the time
        sim.advance_time(dt, 0.00001)

    total_comm_window = gs_info_delft.total_contact_time() + gs_info_korou.total_contact_time()
    comm_windows = gs_info_delft.comm_window_list + gs_info_korou.comm_window_list

    # print end time of simulation
    print(
        "-----------------------------------------------------\n"
        f"simulation ended at: {sat_actor.local_time}")

    print(
        "-----------------------------------------------------\n"
        f" avg comms window per orbit: {round(total_comm_window / orbits_to_simulate, 1)} [s/orbit]  \n"
        "-----------------------------------------------------"
    )
    print(
        f" shortest comms window: {min(comm_windows)} [s]  \n"
        "-----------------------------------------------------"
    )
    print(
        f" average comms window: {round(total_comm_window / len(comm_windows), 1)} [s] \n"
        "-----------------------------------------------------"
    )
    print(
        f" longest comms window: {max(comm_windows)} [s] \n"
        "-----------------------------------------------------"
    )
    # print number of contacts
    print(
        f"---------- number of contacts: {len(comm_windows)} ----------\n"
        "-----------------------------------------------------"
    )


if __name__ == '__main__':
    # testing()
    paseos_test()