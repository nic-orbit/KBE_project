from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo
from cubesat_configurator import subsystem as ac
import pandas as pd
import os


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
    # instrument_image_width=Input()
    # instrument_image_length=Input()
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

class ADCS(ac.Subsystem):
    required_pointing_accuracy = ac.Input()  # deg
    def read_comm_from_csv(self):
        """Read communication subsystem data from CSV."""
        script_dir = os.path.dirname(__file__)
        relative_path = os.path.join('data', 'ADCS.csv')
        cs_info_path = os.path.join(script_dir, relative_path)
        return pd.read_csv(cs_info_path)
    
    @Attribute
    def adcs_selection(self):
        """Select communication subsystem based on payload requirements."""
        adcs = self.read_comm_from_csv()
        adcs_list = []

        for index, row in adcs.iterrows():
            # Compare the data rate value from the CSV with the user-provided data rate
            if row['Pointing_Accuracy'] > self.required_pointing_accuracy:
                # Score calculation
                score = (
                    row['Mass'] * self.parent.mass_factor*0.001 +
                    row['Cost'] * self.parent.cost_factor +
                    row['Power'] * self.parent.power_factor
                )
                # Add the row to the list of selected options as a dictionary
                adcs_list.append({
                    'index': index,
                    'Company': row['Company'],
                    'Data_Rate': row['Data_Rate'],
                    'Power': row['Power'],
                    'Mass': row['Mass'],
                    'Height': row['Height'],
                    'Cost': row['Cost'],
                    'Score': score
                })

        if len(adcs_list) == 0:
            # Check if any of the components match the requirement and display error 
            raise ValueError("No suitable component found for ADCS")

        # Choose the component with the smallest score
        adcs_selection = min(adcs_list, key=lambda x: x['Score'])

        return adcs_selection
    


class COMM(ac.Subsystem):
    def read_comm_from_csv(self):
        """Read communication subsystem data from CSV."""
        script_dir = os.path.dirname(__file__)
        relative_path = os.path.join('data', 'Communication_subsystem.csv')
        cs_info_path = os.path.join(script_dir, relative_path)
        return pd.read_csv(cs_info_path)
    
    @Attribute
    def comm_selection(self):
        """Select communication subsystem based on payload requirements."""
        comm = self.read_comm_from_csv()
        comm_list = []

        for index, row in comm.iterrows():
            # Compare the data rate value from the CSV with the user-provided data rate
            if row['Data_Rate'] > self.payload.instrument_data_rate:
                # Score calculation
                score = (
                    row['Mass'] * self.parent.mass_factor *0.001+
                    row['Cost'] * self.parent.cost_factor +
                    row['Power'] * self.parent.power_factor
                )
                # Add the row to the list of selected options as a dictionary
                comm_list.append({
                    'index': index,
                    'Company': row['Company'],
                    'Data_Rate': row['Data_Rate'],
                    'Power': row['Power'],
                    'Mass': row['Mass'],
                    'Height': row['Height'],
                    'Cost': row['Cost'],
                    'Score': score
                })

        if len(comm_list) == 0:
            # Check if any of the components match the requirement and display error 
            raise ValueError("No suitable component found for Communication Subsystem")

        # Choose the component with the smallest score
        comm_selection = min(comm_list, key=lambda x: x['Score'])

        return comm_selection

class OBC(ac.Subsystem):
    required_onboard_data_storage = ac.Input()  # Value needs to come from PASEOS simulation (GB)

def read_obc_from_csv(self):
        """Read communication subsystem data from CSV."""
        script_dir = os.path.dirname(__file__)
        relative_path = os.path.join('data', 'OBC.csv')
        cs_info_path = os.path.join(script_dir, relative_path)
        return pd.read_csv(cs_info_path)
    
@Attribute
def obc_selection(self):
    """Select communication subsystem based on payload requirements."""
    obc = self.read_OBC_from_csv()
    obc_list = []

    for index, row in obc.iterrows():
            # Compare the data rate value from the CSV with the user-provided data rate
            if row['Storage'] > self.required_onboard_data_storage:
                # Score calculation
                score = (
                    row['Mass'] * self.parent.mass_factor* 0.001 +
                    row['Cost'] * self.parent.cost_factor +
                    row['Power'] * self.parent.power_factor * 0.001
                )
                # Add the row to the list of selected options as a dictionary
                obc_list.append({
                    'index': index,
                    'Company': row['Company'],
                    'Data_Rate': row['Data_Rate'],
                    'Power': row['Power'],
                    'Mass': row['Mass'],
                    'Height': row['Height'],
                    'Cost': row['Cost'],
                    'Score': score
                })

    if len(obc_list) == 0:
            # Check if any of the components match the requirement and display error 
            raise ValueError("No suitable component found for OBC Subsystem")

    # Choose the component with the smallest score
    obc_selection = min(obc_list, key=lambda x: x['Score'])

    return obc_selection

class EPS(ac.Subsystem):
    pass

class Structure(ac.Subsystem):
    pass


class Thermal(ac.Subsystem):
    pass












