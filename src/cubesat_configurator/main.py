from parapy.geom import Box
from parapy.gui import display

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


if __name__ == '__main__':
    testing()


