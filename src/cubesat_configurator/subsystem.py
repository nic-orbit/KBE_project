from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo
import os
import pandas as pd

class Subsystem(GeomBase):
    height = Input(10)
    mass = Input(0.01)
    power = Input(0.01)
    cost = Input(0.01) #implement specific range for mass, power, cost (rating on 3?)

    # we force width and length to be always equal to 100 mm to adhere to CubeSat form factor!
    width = 100
    length = 100

    def read_subsystems_from_csv(self, subsystem_file_name):
        """Read subsystem data from CSV."""
        script_dir = os.path.dirname(__file__)
        relative_path = os.path.join('data', subsystem_file_name)
        obc_info_path = os.path.join(script_dir, relative_path)
        return pd.read_csv(obc_info_path)

    @Attribute
    def score_calculation(self):
        pass
    
    @Attribute
    def CoM(self):
        return Point(x=0.5*self.width, y=0.5*self.length, z=0.5*self.height)
    
    @Part
    def bounding_box(self):
        """
        Example of dynamic type chosen from type_dict, based on user input dyn_input_key
        :return: DynamicType
        input must be provided for all classes. DynamicType will automatically select those
        necessary to the selected class
        """
        return Box(length=self.length, 
                   width=self.width, 
                   height=self.height)
    

if __name__ == "__main__":
    from parapy.gui import display
    obj = Subsystem(height=1, width=1, length=1, diameter=1, shape="box")
    display(obj)