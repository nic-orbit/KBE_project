from parapy.gui import display

from cubesat_configurator.mission import Mission
from pprint import pprint


def paseos_test():
    my_mission = Mission(mission_lifetime=24, # months
                            orbit_type="SSO", # SSO, Polar, Equatorial, custom
                            custom_inclination=30, # deg
                            number_of_images_per_day=10, # number
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
