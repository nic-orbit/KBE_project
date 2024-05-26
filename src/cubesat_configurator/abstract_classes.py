from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo

class SpaceComponent(GeomBase):
    mass = Input(0)
    power = Input(0)

# class CoM(Base):
#     x = Input(0)
#     y = Input(0)
#     z = Input(0)

class Subsystem(SpaceComponent):
    height = Input(1)
    width = Input(1)
    length = Input(1)
    diameter = Input(1)

    # @Attribute
    # def type_dict(self):
    #     """
    #     dictionary of different geometry primitives from which a user can choose
    #     :return: dict
    #     """
    #     return {"cylinder": Cylinder,
    #             "box": Box,
    #             "cone": Cone,
    #             "sphere": Sphere}
    
    @Attribute
    def CoM(self):
        if self.shape == "box":
            return Point(x=0.5*self.width, y=0.5*self.length, z=0.5*self.height)
        elif self.shape == "cylinder":
            return Point(x=0, y=0, z=0.5*self.height)
        elif self.shape == "sphere":
            return Point(x=0, y=0, z=0)
        elif self.shape == "cone":
            return Point(x=0, y=0, z=0.25*self.height)
        else:
            raise ValueError(f"Invalid or no shape specified for {self.name}")
    
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
        # return DynamicType(type=self.type_dict[self.shape],
        #                    length=self.length,
        #                    width=self.width,
        #                    height=self.height,
        #                    radius=self.diameter/2,
        #                    radius1=self.diameter/2, # base of cone
        #                     radius2=0 # top of cone
        #                    )

