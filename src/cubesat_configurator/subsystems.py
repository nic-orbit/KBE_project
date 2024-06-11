from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo, IsInstance
from parapy.core.widgets import (
    Button, CheckBox, ColorPicker, Dropdown, FilePicker, MultiCheckBox,
    ObjectPicker, SingleSelection, TextField)
from cubesat_configurator import subsystem as ac
import pandas as pd
import numpy as np
import os
import pykep as pk
from cubesat_configurator import constants
from cubesat_configurator import thermal_helpers as th


class Payload(ac.Subsystem):
    
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
    # instrument_image_width=Input()
    # instrument_image_length=Input()
    instrument_pixel_resolution=Input() # range to be defined or we split this into w and h, consider list
    instrument_bit_depth=Input() #range to be defined (1-24) Check gs for inputvalidator
    
    height = Input(instrument_height)
    cost=Input(instrument_cost) 
    # Thought it would be nice to check if the sensor fits within the limits of the satellite
    # I saw in extreme cases (15 µm & 4k resolution) it can be almost 60 mm long on the long side. 

    @Attribute
    def instrument_images_per_day(self):
        return self.parent.parent.number_of_images_per_day

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
        return self.instrument_pixel_resolution[0]*self.instrument_pixel_resolution[1] # pixels
        # if we use separate values for width and height:
        # return self.instrument_resolution_width*self.instrument_resolution_height

    @Attribute
    def image_size(self):
        """
        Calculates the size of the image based on the instrument pixel resolution and pixel size.
        """
        return self.pixel_count*self.instrument_bit_depth*10**-3 # kbits

    @Attribute
    def instrument_data_rate(self):
        """
        Payload data rate calculation based on the instrument characteristics.
        PLDR = (Number_of_pixels * Bit_depth [bits] * Number_of_images_per_day) / seconds per day * 1E-3 [kbps]
        """
        instrument_data_per_day = self.image_size*self.instrument_images_per_day # kbits
        return ( instrument_data_per_day ) / ( pk.DAY2SEC ) # kbps
#Done for now
class ADCS(ac.Subsystem):
    required_pointing_accuracy = Input()  # deg

    @required_pointing_accuracy.validator
    def required_pointing_accuracy_validator(self, value):
        if value < 0:
            msg =  self.requirement_key + " cannot be negative"
            return False, msg
        
        adcs_df = self.read_adcs_from_csv
        # find minimum Pointing Accuracy value from the CSV
        min_pa = adcs_df[self.requirement_key].min()
        if value < min_pa:
            msg = "Required " + self.requirement_key + f" cannot be lower than {min_pa} deg, because it is the minimum value in the database."
            return False, msg
        return True
    
    requirement_key = 'Pointing_Accuracy'
    
    @Attribute
    def read_adcs_from_csv(self):
        return self.read_subsystems_from_csv('ADCS.csv')

    @Attribute
    def adcs_selection(self):
        """Select ADCS subsystem based on payload requirements."""
        adcs = self.read_adcs_from_csv
        selected = self.component_selection(adcs, self.requirement_key,  self.required_pointing_accuracy, 'less')

        return selected
    
class COMM(ac.Subsystem):
    # required_downlink_data_rate = Input()  # kbps
    def read_comm_from_csv(self):
        return self.read_subsystems_from_csv('Communication_subsystem.csv')
    
    @Attribute
    def comm_selection(self):
        """Select communication subsystem based on payload requirements."""
        comm = self.read_comm_from_csv()
        comm_list = []

        for index, row in comm.iterrows():
            # Compare the data rate value from the CSV with the user-provided data rate
            if row['Data_Rate'] > self.parent.required_downlink_data_rate: 
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
    

#Done for now
class OBC(ac.Subsystem):
    required_onboard_data_storage = Input()  # Value needs to come from PASEOS simulation (GB)

    @required_onboard_data_storage.validator
    def required_onboard_data_storage_validator(self, value):
        if value < 0:
            msg = "Onboard data storage cannot be negative"
            return False, msg
        
        comms_df = self.read_obc_from_csv()
        # find maximum data storage value from the CSV
        max_storage = comms_df['Storage'].max()
        if value > max_storage:
            msg = f"Required onboard data storage cannot exceed {max_storage} GB, because it is the maximum value in the database."
            return False, msg
        return True
    
    def read_obc_from_csv(self):
        return self.read_subsystems_from_csv('OBC.csv')

    @Attribute
    def obc_selection(self):
        """Select OBC subsystem based on payload requirements."""
        obc = self.read_obc_from_csv()
        return self.component_selection(self,obc, 'Storage', self.required_onboard_data_storage)
    

class EPS(ac.Subsystem):
    # Solar_panel_type = Input(validator=IsInstance(['Body-mounted', 'Deployable']), default='Body-mounted')
    Solar_panel_type = Input(default='Body-mounted', widget=Dropdown(['Body-mounted', 'Deployable']))
        

    def read_SolarPanel_from_csv(self):
        return self.read_subsystems_from_csv('Solar_Panel.csv')
    
    def read_bat_from_csv(self):
        return self.read_subsystems_from_csv('Battery.csv')
    
    @Attribute
    def avg_power_comm(self):
        comm_selection_list=self.comm_selection
        tgs=self.parent.simulate_first_orbit["comm_window_per_day"] #input from Paseos
        avg_power_comm=0
        for row in comm_selection_list:
            power_comm=row['Power_DL']*(tgs/24)+row['Power_Nom']*(1-(tgs/24)) # tgs = communication time per day 
            avg_power_comm+=power_comm
        return(avg_power_comm)
    
    @Attribute
    def total_power_required(self):
        obc_selection_list=self.obc_selection
        adcs_selection_list=self.adcs_selection
        total_power=(self.avg_power_comm + obc_selection_list['Power'] + adcs_selection_list['Power'] + self.parent.payload.instrument_power_consumption)*(1+constants.SystemConfig.system_margin)
        return (total_power)

    
    @Attribute
    def solar_panel_selection(self):
        """Select Solar Panels based on payload requirements."""
        sp = self.read_sp_from_csv()
        time_period=ac.Input()
        eclipse_time=ac.Input()
        solar_panel_power_req=self.total_power_required*(time_period)/(1-eclipse_time)
        sp_list = []
        for index, row in sp.iterrows():
            # Compare the data rate value from the CSV with the user-provided data rate
            if row['Power'] > solar_panel_power_req and row['Type'] == self.Solar_panel_type:
                # Score calculation
                score = (
                    int(row['Mass']) * self.parent.mass_factor* 0.001 +
                    int(row['Cost']) * self.parent.cost_factor +
                    int(row['Power']) * self.parent.power_factor
                )
                # Add the row to the list of selected options
                sp_list.append({
                    'index': index,
                    'Form_factor': row['Form_factor'],
                    'Type': row['Type'],
                    'Power': row['Power'],
                    'Mass': row['Mass'],
                    'Cost': row['Cost'],
                    'Score': score
                })

        if len(sp_list) == 0:
            # Check if any of the components match the requirement and display error 
            raise ValueError("No suitable component found for Solar Panels")

        # Choose the component with the smallest score
        sp_selection = min(sp_list, key=lambda x: x['Score'])

        return sp_selection

    @Attribute
    def battery_selection(self):
        """Select Solar Panels based on payload requirements."""
        bat = self.read_bat_from_csv()
        time_period=ac.Input()
        eclipse_time=ac.Input()
        battery_power_req=self.total_power_required*(time_period)/(eclipse_time)
        bat_list = []
        for index, row in bat.iterrows():
            # Compare the data rate value from the CSV with the user-provided data rate
            if row['Power'] > battery_power_req:
                # Score calculation
                score = (
                    int(row['Mass']) * self.parent.mass_factor* 0.001 +
                    int(row['Cost']) * self.parent.cost_factor +
                    int(row['Power']) * self.parent.power_factor
                )
                # Add the row to the list of selected options
                bat_list.append({
                    'index': index,
                    'Company': row['Company'],
                    'Power': row['Power'],
                    'Mass': row['Mass'],
                    'Cost': row['Cost'],
                    'Height':row['Height'],
                    'Score': score
                })

        if len(bat_list) == 0:
            # Check if any of the components match the requirement and display error 
            raise ValueError("No suitable component found for Batteries")

        # Choose the component with the smallest score
        bat_selection = min(bat_list, key=lambda x: x['Score'])

        return bat_selection


class Structure(ac.Subsystem):

    def read_struct_from_csv(self):
        return self.read_subsystems_from_csv('Structure.csv')

    @Attribute
    def form_factor(self):
        "Calculate form factor for cubesat"
        obc_selection_list=self.obc_selection
        adcs_selection_list=self.adcs_selection
        bat_selection_list=self.bat_selection
        comm_selection_list=self.comm_selection
        total_height=obc_selection_list['Height'] + adcs_selection_list['Height'] + self.instrument_height + bat_selection_list['Height'] + comm_selection_list['Height']
        height_factor = total_height / 100
        
        if height_factor < 1:
            form_factor = 1
        elif height_factor < 1.5:
            form_factor = 1.5
        elif height_factor < 2:
            form_factor = 2
        elif height_factor < 3:
            form_factor = 3
        else:
            form_factor = "No available Cubesat sizes found"
        return form_factor

    @Attribute
    def structure(self):
        form_factor_req = self.form_factor

        struct = self.read_struct_from_csv()
        struct_selection = []

        for index, row in struct.iterrows():
            # Compare the data rate value from the CSV with the user-provided data rate
            if row['Form_Factor'] == form_factor_req:
                
                # Add the row to the list of selected options as a dictionary
                struct_selection.append({
                    'index': index,
                    'Form_Factor': row['Form_Factor'],
                    'Mass': row['Mass'],
                    'Cost': row['Cost']
                })

        if len(struct_selection) == 0:
            # Check if any of the components match the requirement and display error 
            raise ValueError("No suitable component found for OBC Subsystem")

        return struct_selection     

class Thermal(ac.Subsystem):
    T_max_in_C = Input()  # deg C
    T_min_in_C = Input()  # deg C
    T_margin = Input()  # deg C (or K)
    satellite_cp = Input(900)  # J/kgK specific heat capacity of aluminum
    
    @T_max_in_C.validator
    def T_max_in_C_validator(self, value):
        if value - self.T_margin < self.T_min_in_C + self.T_margin:
            msg = "Maximum temperature cannot be smaller than minimum temperature, including the margin."
            return False, msg
        return True
    
    @T_min_in_C.validator
    def T_min_in_C_validator(self, value):
        if value + self.T_margin > self.T_max_in_C - self.T_margin:
            msg = "Minimum temperature cannot be larger than maximum temperature, including the margin."
            return False, msg
        return True
    
    @T_margin.validator
    def T_margin_validator(self, value):
        if value < 0:
            msg = "Margin cannot be negative"
            return False, msg
        return True
    
    @Attribute
    def T_max_with_margin_in_K(self):
        return self.T_max_in_C + 273.15 - self.T_margin # K
    
    @Attribute
    def T_min_with_margin_in_K(self):
        return self.T_min_in_C + 273.15 + self.T_margin # K

    @Attribute
    def sa_type(self):
        return self.parent.eps.Solar_panel_type
    
    @Attribute
    def form_factor(self):
        return self.parent.structure.form_factor
    
    @Attribute
    def apoapsis(self):
        return self.parent.orbit.apoapsis
    
    @Attribute
    def periapsis(self):
        return self.parent.orbit.periapsis
    
    @Attribute
    def satellite_mass(self):
        return self.parent.mass
    
    @Attribute
    def eclipse_time(self):
        return self.parent.simulate_first_orbit["eclipse_time_per_orbit"]
    
    @Attribute
    def coatings_df(self):
        if self.sa_type == 'Body-mounted':
            return pd.read_csv(os.path.join(os.path.dirname(__file__), 'data/thermal_coatings/coatings_NASA_solarcells.csv'))
        elif self.sa_type == 'Deployable':
            return pd.read_csv(os.path.join(os.path.dirname(__file__), 'data/thermal_coatings/coatings_SMAD_no_dupl.csv'))
        else:
            raise ValueError('Invalid solar array type. Choose "Body-mounted" or "Deployable".')
        
    @Attribute
    def Q_internal(self):
        # TODO: Get correct heat dissipation values from the components
        ADCS_dissipation = self.parent.adcs.adcs_selection['Power']
        COMM_dissipation = self.parent.communication.comm_selection['Power']
        OBC_dissipation = self.parent.obc.obc_selection['Power']
        Payload_dissipation = self.parent.payload.instrument_power_consumption

        return ADCS_dissipation + COMM_dissipation + OBC_dissipation + Payload_dissipation
    
    @Attribute
    def selected_coating(self):

        U = np.array([1, 2, 3], dtype=float)  # form factors

        # max cross sectional area for all u in U
        A_C_max = np.sqrt(2) * U * 0.01 # m^2

        # min cross sectional area for all u in U, same for all form factors
        A_C_min = 0.01 # m^2

        # surface area for all u in U
        A_S = (2+4*U) * 0.01 # m^2

        local_coatings_df = self.coatings_df.copy()

        ####### loop coatings
        for i in range(0, len(local_coatings_df)):
            ####### loop form factors
            for u in range(0, len(U)):
                T_hot_eq = th.calculate_equilibrium_hot_temp(0, 
                                                            self.Q_internal,
                                                            local_coatings_df.loc[i, 'Absorptivity'], 
                                                            local_coatings_df.loc[i, 'Emissivity'], 
                                                            self.periapsis, 
                                                            self.apoapsis, 
                                                            A_C_max[u], 
                                                            A_C_min, 
                                                            A_S[u])  # K
                T_cold_eq = th.calculate_equilibrium_cold_temp(0, 
                                                            self.Q_internal,
                                                            local_coatings_df.loc[i, 'Absorptivity'], 
                                                            local_coatings_df.loc[i, 'Emissivity'], 
                                                            self.periapsis, 
                                                            self.apoapsis, 
                                                            A_C_max[u], 
                                                            A_C_min, 
                                                            A_S[u])  # K

                # final temperatures for design
                T_hot = T_hot_eq
                
                T_cold = th.exact_transient_solution_cooling(T_cold_eq, 
                                                             T_hot, 
                                                             self.satellite_mass, 
                                                             self.satellite_cp, 
                                                             local_coatings_df.loc[i, 'Emissivity'], 
                                                             A_S[u], 
                                                             self.eclipse_time)  # K

                local_coatings_df.loc[i, f'Hot Case {u+1}U'] = T_hot  # K
                local_coatings_df.loc[i, f'Cold Case {u+1}U'] = T_cold  # K
                local_coatings_df.loc[i, f'Hot Margin {u+1}U'] = self.T_max_with_margin_in_K - T_hot  # K
                local_coatings_df.loc[i, f'Cold Margin {u+1}U'] = T_cold - self.T_min_with_margin_in_K  # K

        # print coatings_df only the margins
        print(local_coatings_df[['Coating' , 'Hot Margin 1U', 'Cold Margin 1U','Hot Margin 2U', 'Cold Margin 2U', 'Hot Margin 3U',  'Cold Margin 3U']])
        
        selected_coating = th.select_coating(self.form_factor, local_coatings_df)
        return selected_coating

    @Attribute
    def T_hot_case(self):
        return self.selected_coating['Hot Case']
    
    @Attribute
    def T_cold_case(self):
        if self.selected_coating[f'Cold Margin {self.form_factor}U'] >= 0:
            return self.selected_coating['Cold Case']
        else:
            self.final_heater_values['Cold Case with Heater']

    @Attribute
    def final_heater_values(self):
        # maximum cross sectional area for given form factor
        A_C_max = np.sqrt(2) * self.form_factor * 0.01 # m^2
        # minimum cross sectional area for all form factors
        A_C_min = 0.01 # m^2
        # cubesat surface area for given form factor
        A_S = (2+4*self.form_factor) * 0.01 # m^2

        T = self.selected_coating['Cold Case']
        P = 0
        while T < self.T_min_with_margin_in_K:
            T_hot_eq = th.calculate_equilibrium_hot_temp(P, 
                                                        self.Q_internal,
                                                        self.selected_coating['Absorptivity'], 
                                                        self.selected_coating['Emissivity'], 
                                                        self.periapsis, 
                                                        self.apoapsis, 
                                                        A_C_max, 
                                                        A_C_min, 
                                                        A_S)  # K
            T_cold_eq = th.calculate_equilibrium_cold_temp(P, 
                                                        self.Q_internal,
                                                        self.selected_coating['Absorptivity'], 
                                                        self.selected_coating['Emissivity'], 
                                                        self.periapsis, 
                                                        self.apoapsis, 
                                                        A_C_max, 
                                                        A_C_min, 
                                                        A_S)  # K
            T_hot = T_hot_eq
            # print(f"for test {T_cold_eq} < {T_hot}")
            T = th.exact_transient_solution_cooling(T_cold_eq, 
                                                    T_hot, 
                                                    self.satellite_mass, 
                                                    self.satellite_cp, 
                                                    self.selected_coating.loc['Emissivity'], 
                                                    A_S, 
                                                    self.eclipse_time)  # K
            
            P += 0.001  # increase heater power by 1mW

        final_heater_values = {
            'Heater Power': round(P,3),
            'Cold Case with Heater': T,
            'Cold Margin with Heater': T - self.T_min_with_margin_in_K}
        
        return final_heater_values














