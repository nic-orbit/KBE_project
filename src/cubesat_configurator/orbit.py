from parapy.core import *
from parapy.geom import *
import numpy as np
import pykep as pk
from typing import cast
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo, IsInstance, Range, AdaptedValidator
from cubesat_configurator.custom_validators import altitude_validator


class Orbit(Base):
    altitude = Input() # km
    eccentricity = Input(0) # dimensionless
    RAAN = Input(0) # deg
    argument_of_periapsis = Input(0) # deg
    true_anomaly = Input(0) # deg

    @altitude.validator
    def altitude(self, value):
        """
        Validator for the altitude input of Orbit class. The altitude must higher then 100 km and lower than 2000 km.
        """
        if value < 100:
            print(
                  "The altitude must be higher than 100 km. \n"
                  f"Current value: {value} km, please increase GSD or adjust instrument characteristics (e.g. focal length or pixel size).\n"
                  "Formula: h [km] = (GSD [m] / (pixel_size [µm] * 10**-6) ) * focal_length [mm] * 10**-6  "
                  )
            return False
        if value > 2000:
            print(
                  "The altitude must be lower than 2000 km. \n"
                  f"Current value: {value} km, please decrease GSD or adjust instrument characteristics (e.g. focal length or pixel size).\n"
                  "Formula: h [km] = (GSD [m] / (pixel_size [µm] * 10**-6) ) * focal_length [mm] * 10**-6  "
                  )
            return False
        return True

    
    @Attribute
    def inclination(self):
        inc_SSO = np.round(0.0087033*self.altitude+90.2442419, 2) # deg, derived from linear regression of SSO altitudes and inclinations from wikipedia
        return 90 if self.parent.parent.orbit_type == "Polar" else inc_SSO if self.parent.parent.orbit_type == "SSO" else 0 if self.parent.parent.orbit_type == "Equatorial" else self.parent.parent.custom_inclination

    @Attribute
    def apoapsis(self):
        return (self.altitude*1000 + pk.EARTH_RADIUS)*(1+self.eccentricity) # in m

    @Attribute
    def periapsis(self):
        return (self.altitude*1000 + pk.EARTH_RADIUS)*(1-self.eccentricity) # in m
    
    @Attribute
    def period(self):
        return 2 * np.pi * np.sqrt(self.semi_major_axis**3 / pk.MU_EARTH) # in s
    
    @Attribute
    def semi_major_axis(self):
        return 0.5*(self.apoapsis+self.periapsis) # in m
    
    @Attribute
    def position_vector(self):
        """
        Convert the Keplerian elements to a position vector in the ECI frame for this orbit in meters.
        Returns:    
            r_eci: np.array
                Position vector in the ECI frame
        """        
        # convert km in m
        r_eci, v_eci = pk.par2ic([self.semi_major_axis, self.eccentricity, self.inclination, self.RAAN, self.argument_of_periapsis, self.true_anomaly], pk.MU_EARTH)
        return r_eci
    
    @Attribute
    def velocity_vector(self):
        """
        Convert the Keplerian elements to a velocity vector in the ECI frame for this orbit in meters per second.
        Returns:    
            v_eci: np.array
                Velocity vector in the ECI frame
        """     
        # convert km in m
        r_eci, v_eci = pk.par2ic([self.semi_major_axis, self.eccentricity, self.inclination, self.RAAN, self.argument_of_periapsis, self.true_anomaly], pk.MU_EARTH)
        return v_eci
    
    def __str__(self):
        return ("------ Orbit ------  \n"
                f"altitude: {self.altitude} km\n"
                # print keplerian elements
                f"semi-major axis: {self.semi_major_axis} m\n"
                f"inclination: {self.inclination} deg\n"
                f"eccentricity: {self.eccentricity}\n"
                f"RAAN: {self.RAAN} deg\n"
                f"argument of periapsis: {self.argument_of_periapsis} deg\n"
                f"true anomaly: {self.true_anomaly} deg\n"
                #print orbital period
                f"orbital period: {self.period} s \n"
                f"position vector: {self.position_vector} \n"
                f"velocity vector: {self.velocity_vector} \n"
                "-------------------\n"
        )