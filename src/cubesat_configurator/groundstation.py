from parapy.core import *
from parapy.geom import *


class GroundStation(Base):
    latitude = Input()
    longitude = Input()
    elevation = Input()
    company = Input()
    location = Input()
    number=Input()
    name = Input()
