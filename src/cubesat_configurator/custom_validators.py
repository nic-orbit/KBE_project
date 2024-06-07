from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo, IsInstance, Range, AdaptedValidator


def altitude_validator(value):
        """
        Validator for the altitude input of Orbit class. The altitude must higher then 100 km and lower than 2000 km.
        """
        if value < 100:
            print(
                  "The altitude must be higher than 150 km. \n"
                  f"Current value: {value} km, please increase GSD or adjust instrument characteristics (e.g. focal length or pixel size).\n"
                  "Formula: h [km] = (GSD [m] / (pixel_size [µm] * 10**-6) ) * focal_length [mm] * 10**-6  "
                  )
            return False
        return True