from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo, IsInstance
import numpy as np
import paseos_parser as pp
from cubesat import CubeSat
from groundstation import GroundStation


class Mission(GeomBase): 
    #mission requirements
    mission_lifetime = Input(doc="Mission Lifetime in months") # months
    reqiured_GSD = Input() # m
    orbit_type = Input() # SSO, Polar, Equatorial, custom
    custom_inclination = Input(0) # deg TBD if we use this!
    # Ground Stations selection
    ground_station_selection = Input(validator=IsInstance(list))
    #system requirements
    req_pointing_accuracy = Input(validator= GreaterThan(0)) # deg

    ##### MOVE EVERYTHING TO INSTRUMENT CLASS #####
    #instrument requirements
    instrument_min_operating_temp = Input() # deg C
    instrument_max_operating_temp = Input() # deg C
    #instrument characteristics
    #### data_rate is a Attribute and inputs are image pixel resolution 
    #### and pixel depth and number of images per day
    instrument_data_rate = Input() # kbps
    instrument_focal_length = Input() # mm
    instrument_pixel_size = Input() # µm
    instrument_power_consumption = Input() # W
    instrument_mass = Input() # kg
    instrument_height = Input() # mm
    instrument_width = Input() # mm
    instrument_length = Input() # mm
    instrument_cost = Input() # USD

    @Attribute
    def ground_station_dataframe(self):
        stations = pp.read_ground_stations_from_csv()
        stations_list = []

        for i in self.ground_station_selection:
            # check that index is within the list
            if 0 <= i <= stations.last_valid_index():
                lat = stations.loc[i, "Lat"]
                lon = stations.loc[i, "Lon"]
                company = stations.loc[i, "Company"]
                location = stations.loc[i, "Location"]
                gs_name = f"gs_actor_{i}"
                stations_list.append(stations.loc[i])
                print(f"Added '{company}' groundstation {i} located at {location}")
            else:
                print(f"No ground station with index {i} in data.")
        return stations_list

    @Attribute
    def number_of_ground_stations(self):
        return len(self.ground_station_selection)
    
    # MOVE TO ORBIT CLASS
    @Attribute
    def orbit_inclination(self):
        inc_SSO = np.round(0.0087033*self.max_orbit_altitude+90.2442419, 2) # deg, derived from linear regression of SSO altitudes and inclinations from wikipedia
        return 90 if self.orbit_type == "Polar" else inc_SSO if self.orbit_type == "SSO" else 0 if self.orbit_type == "Equatorial" else self.custom_inclination
    
    # MOVE TO ORBIT CLASS
    @Attribute
    def max_orbit_altitude(self):
        """
        Calculate the maximum orbit altitude based on the required ground sample distance (GSD) and the instrument
        characteristics.
        """
        h = (self.reqiured_GSD / (self.instrument_pixel_size * 10**-6) ) * self.instrument_focal_length * 10**-6  # km
        return h

    @Part
    def cubesat(self):
        return CubeSat(orbit_altitude=self.max_orbit_altitude)
    
    @Part
    def groundstation(self):
        return GroundStation(quantify=self.number_of_ground_stations,
                             latitude=self.ground_station_dataframe[child.index]['Lat'],
                             longitude=self.ground_station_dataframe[child.index]['Lon'],
                             elevation=self.ground_station_dataframe[child.index]['Elevation'],
                             location=self.ground_station_dataframe[child.index]['Location'],
                             number=self.ground_station_dataframe[child.index]['Number']
                             )