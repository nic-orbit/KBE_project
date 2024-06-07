from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo, Range
from cubesat_configurator import subsystem as ac


class Payload(ac.Subsystem):
    #instrument requirements
    instrument_min_operating_temp = Input() # deg C
    instrument_max_operating_temp = Input() # deg C
    #instrument characteristics
    instrument_focal_length = Input() # mm
    instrument_pixel_size = Input() # µm
    instrument_power_consumption = Input() # W
    instrument_mass = Input() # kg
    instrument_cost = Input() # USD
    ### maybe we can delete these and use just height, width and length?
    instrument_height = Input() # mm
    instrument_width = Input() # mm
    instrument_length = Input() # mm
    # I feel like images per day should be on mission level?
    instrument_images_per_day=Input() #number
    instrument_image_width=Input() #pixels
    instrument_image_height=Input() #pixels #range to be defined or we split this into w and h, consider list
    instrument_bit_depth=Input(validator=Range(limit1=1, limit2=24)) #range to be defined (1-24) Check gs for inputvalidator

    height = Input(instrument_height)
    mass = Input(instrument_mass)
    cost = Input(instrument_cost)

    @Attribute
    def pixel_count(self):
        """
        Calculates the number of pixels in the image based on the instrument pixel resolution.
        """
        return(self.instrument_image_height*self.instrument_image_width)

    # Thought it would be nice to check if the sensor fits within the limits of the satellite
    # I saw in extreme cases (15 µm & 4k resolution) it can be almost 60 mm long on the long side. 
    @Attribute
    def sensor_length(self):
        """
        Calculates the length of the sensor / processor side based on the resolution and pixel size.
        """
        return max([self.instrument_image_width, self.instrument_image_height])*self.instrument_pixel_size*10**-3 # mm

    @Attribute
    def instrument_data_rate(self):
        """
        Payload data rate calculation based on the instrument characteristics.
        PLDR = (Number_of_pixels * Bit_depth * Number_of_images_per_day) / orbital_period   [kbps]
        """
        return ( self.pixel_count*self.instrument_bit_depth*self.instrument_images_per_day ) / ( self.parent.orbit.period * 1000 ) # kbps

class OBC(ac.Subsystem):
    required_onboard_data_storage = Input() # this value needs to come from paseos simulation
    pass


class EPS(ac.Subsystem):
    pass


class ADCS(ac.Subsystem):
    required_pointing_accuracy = Input() # deg
    pass


class COMM(ac.Subsystem):
    pass


class Structure(ac.Subsystem):
    pass


class Thermal(ac.Subsystem):
    pass

