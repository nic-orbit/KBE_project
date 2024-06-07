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
    req_pointing_accuracy = Input(validator=GreaterThan(0)) # deg

    
    # helper
    @Attribute
    def ground_station_dataframe(self):
        """
        This function reads ground station data from a CSV file, selects specific ground stations based on the indices provided in 'self.ground_station_selection', and returns these selected stations as a list. 

        For each index in 'self.ground_station_selection', the function checks if the index is within the valid range of the stations DataFrame. If it is, the function retrieves the latitude, longitude, company, location, and name of the ground station at that index, appends the station to the 'stations_list', and prints a message indicating the addition of the ground station. If the index is not valid, the function prints a message indicating the absence of a ground station at that index.

        Returns:
            stations_list (list): A list of selected ground stations from the CSV file.
        """
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

    # helper
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