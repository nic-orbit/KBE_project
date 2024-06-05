from parapy.core import *
from parapy.geom import *
import numpy as np
import pykep as pk


class Orbit(Base):
    altitude = Input() # km
    inclination = Input() # deg
    eccentricity = Input(0) # dimensionless
    RAAN = Input(0) # deg
    argument_of_periapsis = Input(0) # deg
    true_anomaly = Input(0) # deg

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