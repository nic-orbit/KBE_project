from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo
import abstract_classes as ac
import numpy as np


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
    
    @Part
    def payload(self):
        return Payload(width=self.parent.instrument_width,
                       height=self.parent.instrument_height,
                       length=self.parent.instrument_length,
                       mass=self.parent.instrument_mass,
                       power=self.parent.instrument_power_consumption
                       )
    
    @Part
    def communication(self):
        return Communication()
    
    @Part
    def power(self):
        return EPS()


class OBC(ac.Subsystem):
    pass


class ADCS(ac.Subsystem):
    pass


class EPS(ac.Subsystem):
    pass

class Communication(ac.Subsystem):
    pass
    

class Payload(ac.Subsystem):
    pass

    # @Part
    # def shape(self):
    #     if self.shape == "box":
    #         return Box(length=self.length, width=self.width, height=self.height)
    #     elif self.shape == "cylinder":
    #         return Cylinder(radius=self.diameter/2, height=self.height)
    #     elif self.shape == "sphere":
    #         return Sphere(radius=self.diameter/2)
    #     elif self.shape == "cone":
    #         return Cone(radius=self.diameter/2, height=self.height)
    #     else:
    #         raise ValueError(f"Invalid or no shape specified for {self.name}")


class Orbit(Base):
    altitude = Input() # km
    inclination = Input() # deg
    eccentricity = Input(0) # dimensionless
    RAAN = Input(0) # deg
    argument_of_periapsis = Input(0) # deg
    true_anomaly = Input(0) # deg

    @Attribute
    def apoapsis(self):
        return self.altitude*(1+self.eccentricity)

    @Attribute
    def periapsis(self):
        return self.altitude*(1-self.eccentricity)
    
    @Attribute
    def semi_major_axis(self):
        return 0.5*(self.apoapsis+self.periapsis)
    

class GroundStation(GeomBase):
    latitiude = Input(0)
    longitude = Input(0)

