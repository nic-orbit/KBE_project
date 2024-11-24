from parapy.core import Base, Input, Part
from parapy.geom import Cube


class MyModel(Base):
    dimensions = Input(2)

    @Part
    def cube(self):
        return Cube(self.dimensions)
