from parapy.gui import display

from cubesat_configurator.mission import Mission
from pprint import pprint


def run():
    my_mission = Mission(mission_lifetime=24, # months
                        reqiured_GSD=50, # m
                        number_of_images_per_day=5, # number
                        orbit_type="SSO", # SSO, Polar, Equatorial, custom
                        custom_inclination=52, # deg
                        ground_station_selection=[58, 53], # 58=Delft, 53=Havaii, 49=Kourou
                        req_pointing_accuracy=1, # deg
                        )
    
    display(my_mission)

    print("Thank you for using the CubeSat Configurator! :) ")

if __name__ == '__main__':
    run()
