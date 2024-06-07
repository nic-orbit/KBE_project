from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo
import subsystem as ac


class Payload(ac.Subsystem):
    ##### MOVE EVERYTHING TO INSTRUMENT CLASS #####
    #instrument requirements
    instrument_min_operating_temp = Input() # deg C
    instrument_max_operating_temp = Input() # deg C
    #instrument characteristics
    #### data_rate is a Attribute and inputs are image pixel resolution 
    #### and pixel depth and number of images per day
    # instrument_data_rate = Input() # kbps
    instrument_focal_length = Input() # mm
    instrument_pixel_size = Input() # µm
    instrument_power_consumption = Input() # W
    instrument_mass = Input() # kg
    instrument_cost = Input() # USD
    ### maybe we can delete these and use just height, width and length?
    instrument_height = Input() # mm
    instrument_width = Input() # mm
    instrument_length = Input() # mm
    ### maybe we can delete these and use just height, width and length?
    # I feel like images per day should be on mission level?
    instrument_images_per_day=Input() # number
    instrument_pixel_resolution=Input() # range to be defined or we split this into w and h, consider list
    instrument_bit_depth=Input() #range to be defined (1-24) Check gs for inputvalidator
    
    height = Input(instrument_height)

    # Thought it would be nice to check if the sensor fits within the limits of the satellite
    # I saw in extreme cases (15 µm & 4k resolution) it can be almost 60 mm long on the long side. 
    @Attribute
    def sensor_length(self):
        """
        Calculates the length of the sensor / processor side based on the resolution and pixel size.
        """
        return max(self.instrument_pixel_resolution)*self.instrument_pixel_size*10**-3 # mm

    @Attribute
    def pixel_count(self):
        """
        Calculates the number of pixels in the image based on the instrument pixel resolution.
        """
        # if we use a list:
        return self.instrument_pixel_resolution[0]*self.instrument_pixel_resolution[1]
        # if we use separate values for width and height:
        # return self.instrument_resolution_width*self.instrument_resolution_height

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




