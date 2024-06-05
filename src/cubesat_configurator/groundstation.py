from parapy.core import *
from parapy.geom import *


class GroundStation(Base):
    latitude = Input()
    longitude = Input()
    elevation = Input()
    company = Input()
    location = Input()
    number=Input()

    @Attribute
    def name(self):
        # name is a combination of index and location
        return f"GS_{self.number} ({self.location})"
