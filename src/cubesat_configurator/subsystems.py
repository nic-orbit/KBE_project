from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo, IsInstance, Between
import subsystem as ac
    

class Payload(ac.Subsystem):
    #instrument requirements
    instrument_min_operating_temp = Input() # deg C
    instrument_max_operating_temp = Input() # deg C
    #instrument characteristics
    instrument_focal_length = Input() # mm
    instrument_pixel_size = Input() # µm
    instrument_power_consumption = Input() # W
    instrument_mass = Input() # kg
    instrument_height = Input() # mm
    instrument_width = Input() # mm
    instrument_length = Input() # mm
    instrument_cost = Input() # USD
    instrument_images_per_day=Input() #number
    instrument_image_width=Input() #pixels
    instrument_image_height=Input() #pixels #range to be defined or we split this into w and h, consider list
    instrument_bit_depth=Input(validator=Between(min=1, max=24)) #range to be defined (1-24) Check gs for inputvalidator

    @Attribute
    def pixel_count(self):
        return(self.instrument_image_height*self.instrument_image_width)

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




