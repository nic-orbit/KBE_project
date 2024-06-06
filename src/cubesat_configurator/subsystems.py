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
    instrument_height = Input() # mm
    instrument_width = Input() # mm
    instrument_length = Input() # mm
    instrument_cost = Input() # USD
    instrument_images_per_day=Input() #number
    instrument_pixel_resolution=Input() #range to be defined or we split this into w and h
    instrument_bit_depth=Input() #range to be defined

    @Attribute
    def pixel_count(self):
        pass

    @Attribute
    def instrument_data_rate(self):
        return (self.pixel_count*self.instrument_bit_depth*self.instrument_images_per_day)/8000

class OBC(ac.Subsystem):
    pass


class EPS(ac.Subsystem):
    pass


class ADCS(ac.Subsystem):
    pass


class COMM(ac.Subsystem):
    pass




