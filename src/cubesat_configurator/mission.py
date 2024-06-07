from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo, IsInstance
import paseos_parser as pp
from cubesat import CubeSat
from groundstation import GroundStation


class Mission(GeomBase): 
    """
    This class represents a mission for a CubeSat. It includes mission requirements such as lifetime, required Ground Sample Distance (GSD), orbit type, and custom inclination. It also includes system requirements such as pointing accuracy. 

    The class also includes a method to read ground station data from a CSV file and select specific ground stations based on the indices provided in 'ground_station_selection'.

    Inputs:
        mission_lifetime (int): The mission lifetime in months.
        reqiured_GSD (float): The required Ground Sample Distance in meters.
        orbit_type (str): The type of orbit (SSO, Polar, Equatorial, custom).
        custom_inclination (float): The custom inclination in degrees.
        ground_station_selection (list): The indices of the selected ground stations.
        req_pointing_accuracy (float): The required pointing accuracy in degrees.

    Attributes:
        max_orbit_altitude (float): The maximum allowed orbit altitude in km based on the required GSD and the instrument characteristics.
        ground_station_info(list): Reads ground station data from a CSV file, selects specific ground stations, and returns these stations as a list.
        number_of_ground_stations (int): The number of selected ground stations.
    Parts:
        cubesat (CubeSat): The CubeSat.
        groundstation (GroundStation): The GroundStation(s).
    """
    #mission requirements
    mission_lifetime = Input(doc="Mission Lifetime in months") # months
    reqiured_GSD = Input() # m
    orbit_type = Input() # SSO, Polar, Equatorial, custom
    custom_inclination = Input(0) # deg 
    # Ground Stations selection
    ground_station_selection = Input(validator=IsInstance(list))
    #system requirements
    req_pointing_accuracy = Input(validator=GreaterThan(0)) # deg


    # Not moved to Orbit class becasuse we want to instanciate the Orbit class with altitude as an input
    # # This allows the user to input the altitude directly in the app. 
    @Attribute
    def max_orbit_altitude(self):
        """
        Calculate the maximum allowed orbit altitude (in km) based on the required ground sample distance (GSD) and the instrument
        characteristics.
        """
        h = (self.reqiured_GSD / (self.cubesat.payload.instrument_pixel_size * 10**-6) ) * self.cubesat.payload.instrument_focal_length * 10**-6  # km
        return h
    
    # helper
    @Attribute
    def ground_station_info(self):
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
        """
        Returns the number of selected ground stations.
        More specifically, the function returns the length of the 'ground_station_selection' list.
        """
        return len(self.ground_station_selection)

    @Part
    def cubesat(self):
        """
        Returns one CubeSat instance.
        """
        return CubeSat()
    
    @Part
    def groundstation(self):
        """
        Returns a Sequence of GroundStation instances based on the selected ground stations.
        """
        return GroundStation(quantify=self.number_of_ground_stations,
                             latitude=self.ground_station_info[child.index]['Lat'],
                             longitude=self.ground_station_info[child.index]['Lon'],
                             elevation=self.ground_station_info[child.index]['Elevation'],
                             location=self.ground_station_info[child.index]['Location'],
                             number=self.ground_station_info[child.index]['Number']
                             )