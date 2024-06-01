from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo
import abstract_classes as ac
from concrete_classes import subsystems as subsys
import numpy as np
import pykep as pk
import yaml
import os
from pprint import pprint
import paseos_parser as pp


class Mission(GeomBase): 
    #mission requirements
    mission_lifetime = Input(doc="Mission Lifetime in months") # months
    reqiured_GSD = Input() # m
    orbit_type = Input() # SSO, Polar, Equatorial, custom
    custom_inclination = Input(0) # deg TBD if we use this!
    #system requirements
    req_pointing_accuracy = Input(validator= GreaterThan(0)) # deg
    #instrument requirements
    instrument_min_operating_temp = Input() # deg C
    instrument_max_operating_temp = Input() # deg C
    #instrument characteristics
    instrument_data_rate = Input() # kbps
    instrument_focal_length = Input() # mm
    instrument_pixel_size = Input() # µm
    instrument_power_consumption = Input() # W
    instrument_mass = Input() # kg
    instrument_height = Input() # mm
    instrument_width = Input() # mm
    instrument_length = Input() # mm

    @Attribute
    def orbit_inclination(self):
        inc_SSO = np.round(0.0087033*self.max_orbit_altitude+90.2442419, 2) # deg, derived from linear regression of SSO altitudes and inclinations from wikipedia
        return 90 if self.orbit_type == "Polar" else inc_SSO if self.orbit_type == "SSO" else 0 if self.orbit_type == "Equatorial" else self.custom_inclination
    
    
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
        return GroundStation()


class CubeSat(GeomBase):
    orbit_altitude = Input() # km

    @Attribute
    def orbit(self):
        return Orbit(altitude=self.orbit_altitude,
                inclination=self.parent.orbit_inclination)
    
    @Attribute
    def mass(self):
        mass = 0
        for child in self.children:
            if isinstance(child, ac.Subsystem):
                mass += child.mass
        return mass

    @Attribute
    def power_consumption(self):
        power = 0
        for child in self.children:
            if isinstance(child, ac.Subsystem):
                power += child.power
        return power
    
    @Attribute
    def subsystem_dict(self):
        # Get the current directory of the script
        script_dir = os.path.dirname(__file__)
        relative_path = os.path.join('..', 'Subsystem_Library')

        # Construct the full relative file path
        file_path_trunk = os.path.join(script_dir, relative_path)

        subsystems = {"OBC": "OBC.yaml", "EPS": "EPS.yaml", "COMM": "COMM.yaml"}

        for key, value in subsystems.items():
            file_path = os.path.join(file_path_trunk, value)

            # Check if the file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"The file '{file_path}' does not exist.")

            with open(file_path) as f:
                try:
                    subsystems[key] = yaml.safe_load(f)
                except yaml.YAMLError as exc:
                    print(exc)

        pprint(subsystems)
        return subsystems


    @Part
    def payload(self):
        return subsys.Payload(width=self.parent.instrument_width,
                       height=self.parent.instrument_height,
                       length=self.parent.instrument_length,
                       mass=self.parent.instrument_mass,
                       power=self.parent.instrument_power_consumption
                       )
    
    @Part
    def communication(self):
        return subsys.COMM()
    
    @Part
    def power(self):
        return subsys.EPS()
    
    @Part
    def obc(self):
        return subsys.OBC()
    

class GroundStation(GeomBase):
    latitude = Input(52.0116)
    longitude = Input(4.3571)
    elevation = Input(0)


class Orbit(Base):
    altitude = Input() # km
    inclination = Input() # deg
    eccentricity = Input(0) # dimensionless
    RAAN = Input(0) # deg
    argument_of_periapsis = Input(0) # deg
    true_anomaly = Input(0) # deg

    @Attribute
    def apoapsis(self):
        return (self.altitude + pk.EARTH_RADIUS)*(1+self.eccentricity) # Earth radius = 6378 km

    @Attribute
    def periapsis(self):
        return (self.altitude + pk.EARTH_RADIUS)*(1-self.eccentricity)
    
    @Attribute
    def semi_major_axis(self):
        return 0.5*(self.apoapsis+self.periapsis)
    
    @Attribute
    def position_vector(self):
        """
        Convert the Keplerian elements to a position vector in the ECI frame for this orbit in meters.
        Returns:    
            r_eci: np.array
                Position vector in the ECI frame
        """
        r_eci, v_eci = pp.keplerian_to_eci(self.semi_major_axis, self.eccentricity, self.inclination, self.RAAN, self.argument_of_periapsis, self.true_anomaly)
        return r_eci*1000
    
    @Attribute
    def velocity_vector(self):
        """
        Convert the Keplerian elements to a velocity vector in the ECI frame for this orbit in meters per second.
        Returns:    
            v_eci: np.array
                Velocity vector in the ECI frame
        """
        r_eci, v_eci = pp.keplerian_to_eci(self.semi_major_axis, self.eccentricity, self.inclination, self.RAAN, self.argument_of_periapsis, self.true_anomaly)
        return v_eci*1000