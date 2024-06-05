from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo

class Subsystem(GeomBase):
    height = Input(1)
    width = Input(1)
    length = Input(1)
    diameter = Input(1)
    mass = Input(0)
    power = Input(0)
    cost = Input(0)

    @Attribute
    def score_calculation():
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