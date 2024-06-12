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
    
#All good 
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
        self.height = selected['Height']
        return selected

#All good    
class COMM(ac.Subsystem):
    requirement_key = 'Data_Rate'
    required_downlink_data_rate = Input()  # Value needs to come from PASEOS simulation (GB)

    @required_downlink_data_rate.validator
    def required_downlink_data_rate_validator(self, value):
        if value < 0:
            msg = "Onboard data rate cannot be negative"
            return False, msg
        
        comms_df = self.read_comm_from_csv
        # find maximum data rate value from the CSV
        max_data_rate = comms_df['Data_Rate'].max()
        if value > max_data_rate:
            msg = f"Required onboard data storage cannot exceed {max_data_rate} kbps, because it is the maximum value in the database."
            return False, msg
        return True
    
    @Attribute
    def read_comm_from_csv(self):
        return self.read_subsystems_from_csv('Communication_subsystem.csv')
    
    @Attribute
    def comm_selection(self):
        """Select Communication subsystem based on downlink data rate requirements."""
        comm = self.read_comm_from_csv
        tgs = self.parent.simulate_first_orbit["comm_window_per_day"]
        selected = self.component_selection(comm, self.requirement_key,  self.required_downlink_data_rate, 'greater', is_comm=True, tgs=tgs)
        self.height=selected['Height']
        return selected
    

#All good 
class OBC(ac.Subsystem):
    required_onboard_data_storage = Input()  # Value needs to come from PASEOS simulation (GB)
    requirement_key='Storage'

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
        obc_selection = self.component_selection(obc, self.requirement_key,  self.required_onboard_data_storage, 'greater')
        self.height = obc_selection['Height']
        return obc_selection
    

class EPS(ac.Subsystem):
    
    Solar_cell_type = Input(default='Triple Junction GaAs rigid', widget=Dropdown(['Si rigid panel', 'HES Flexible array','Triple Junction GaAs rigid', 'Triple Junction GaAs ultraflex']))
    
    eclipse_time = Input()

    def read_SolarPanel_from_csv(self):
        sp=self.read_subsystems_from_csv('Solar_Panel.csv')
        selected_panel = sp[sp['Type'] == self.Solar_cell_type]
        return (selected_panel.iloc[0])
    
    def read_bat_from_csv(self):
        return self.read_subsystems_from_csv('Battery.csv')
    
    @Attribute
    def _time_period(self):
        return self.parent.orbit.period
    
    @Attribute
    def _mission_lifetime_yrs(self):
        return (self.parent.parent.mission_lifetime/12)
    
    @Attribute
    def _communication_power(self):
        return self.parent.communication.comm_selection
    
    @Attribute
    def _obc_power(self):
        return self.parent.obc.obc_selection['Power']
    
    @Attribute
    def _adcs_power(self):
        return self.parent.adcs.adcs_selection['Power']
    
    @Attribute
    def _thermal_power(self):
        return self.parent.thermal.power
    
    @Attribute
    def _payload_power(self):
        return self.parent.payload.instrument_power_consumption
    
    @Attribute
    def avg_power_communication(self):
        tgs = self.parent.simulate_first_orbit["comm_window_per_day"]  # input from Paseos
        power_communication = self._communication_power['Power_DL'] * (tgs / (24*3600)) + self._communication_power['Power_Nom'] * (1 - (tgs / (24*3600)))  # tgs = communication time per day       
        return power_communication

    @Attribute
    def eclipse_power(self):
        return(self._adcs_power * constants.Power.duty_cycle + self._communication_power['Power_Nom'] + self._obc_power + self._payload_power + self._thermal_power)

    @Attribute
    def eclipse_power_without_COM(self):
        return(self._adcs_power * constants.Power.duty_cycle + self._obc_power + self._payload_power + self._thermal_power)

    @Attribute
    def average_power_required(self):
        total_power = (self._adcs_power * constants.Power.duty_cycle + self.avg_power_communication + self._obc_power + self._payload_power + self._thermal_power * (self.eclipse_time/self._time_period))
        return total_power

    @Attribute
    def battery_selection(self):
        """Select Batteries based on power requirements."""
        requirement_key = 'Capacity'
        bat = self.read_bat_from_csv()
        number_of_cycles = self._mission_lifetime_yrs*365.25*(24*3600/self._time_period)
        print(number_of_cycles)
        state_of_charge_min =  (-162.1584 + 26.7349 * np.log(number_of_cycles))*0.01 
        print(state_of_charge_min)
        req_battery_capacity = state_of_charge_min * self.eclipse_time * self.eclipse_power/3600
        print(req_battery_capacity)

        if req_battery_capacity > bat['Capacity'].max():
            req_battery_capacity = state_of_charge_min * self.eclipse_time * self.eclipse_power_without_COM
            print(req_battery_capacity)
        selected = self.component_selection(bat, requirement_key, req_battery_capacity, 'greater', subsystem_name='eps')
        self.height = selected['Height']
        return selected
    
    @Attribute
    def req_solar_panel_power(self):
        required_power = (self.average_power_required*(1-(self.eclipse_time/self._time_period))) + (self.eclipse_power * (self.eclipse_time/self._time_period))
        return (required_power)
    
    @Attribute
    def _solar_panel_fluxEOL(self):
        """Select Solar Panels based on power requirements."""
        selected_solar_panel=self.read_SolarPanel_from_csv()
        Flux_solar = selected_solar_panel['Efficiency'] * constants.Thermal.S
        Flux_BOL = Flux_solar * constants.Power.I_d
        L_D = (1-constants.Power.F_d)**(self._mission_lifetime_yrs)
        Flux_EOL = Flux_BOL * L_D 
        return Flux_EOL
    
    @Attribute
    def solar_panel_area(self):
        area = self.req_solar_panel_power/self._solar_panel_fluxEOL
        return area
    
    @Attribute
    def solar_panel_mass(self):
        selected_solar_panel = self.read_SolarPanel_from_csv()
        return (self.req_solar_panel_power/selected_solar_panel['Specific_power'] * 1000)
    
    @Attribute
    def solar_panel_cost(self):
        selected_solar_panel = self.read_SolarPanel_from_csv()
        return (self.req_solar_panel_power/selected_solar_panel['Cost'])
        

class Structure(ac.Subsystem):

    def read_struct_from_csv(self):
        return self.read_subsystems_from_csv('Structure.csv')

    @Attribute
    def form_factor(self):
        "Calculate form factor for cubesat"
        obc_selection_list=self.parent.obc.obc_selection
        adcs_selection_list=self.parent.adcs.adcs_selection
        bat_selection_list=self.parent.power.battery_selection
        comm_selection_list=self.parent.communication.comm_selection
        total_height = obc_selection_list['Height'] + adcs_selection_list['Height'] + self.parent.payload.instrument_height + bat_selection_list['Height'] + comm_selection_list['Height']
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
        self.height = form_factor*100
        return form_factor

    @Attribute
    def structure(self):
        form_factor_req = self.form_factor
        struct = self.read_struct_from_csv()
        struct_selection = []

        for index, row in struct.iterrows():
            # Compare the required Form Factor value with the requirements from the CSV 
            if row['Form_Factor'] == form_factor_req:
                struct_selection.append({
                    'index': index,
                    'Form_Factor': row['Form_Factor'],
                    'Mass': row['Mass'],
                    'Cost': row['Cost']
                })
        if len(struct_selection) == 0:
            raise ValueError("No suitable component found based on the criteria.") 
        
        selected_structure = struct_selection[0]
        self.mass = selected_structure['Mass']
        self.cost = selected_structure['Cost']
        
        return selected_structure     

class Thermal(ac.Subsystem):
    T_max_in_C = Input()  # deg C
    T_min_in_C = Input()  # deg C
    T_margin = Input(5)  # deg C (or K)
    satellite_cp = Input(900)  # J/kgK specific heat capacity of aluminum
    
    # @T_max_in_C.validator
    # def T_max_in_C_validator(self, value):
    #     if value - self.T_margin < self.T_min_in_C + self.T_margin:
    #         msg = "Maximum temperature cannot be smaller than minimum temperature, including the margin."
    #         return False, msg
    #     return True
    
    # @T_min_in_C.validator
    # def T_min_in_C_validator(self, value):
    #     if value + self.T_margin > self.T_max_in_C - self.T_margin:
    #         msg = "Minimum temperature cannot be larger than maximum temperature, including the margin."
    #         return False, msg
    #     return True
    
    # @T_margin.validator
    # def T_margin_validator(self, value):
    #     if value < 0:
    #         msg = "Margin cannot be negative"
    #         return False, msg
    #     return True
    
    @Attribute
    def T_max_with_margin_in_K(self):
        return self.T_max_in_C + 273.15 - self.T_margin # K
    
    @Attribute
    def T_min_with_margin_in_K(self):
        return self.T_min_in_C + 273.15 + self.T_margin # K
    
    @Attribute
    def form_factor(self):
        # return self.parent.structure.form_factor
        return 2 
    
    @Attribute
    def apoapsis(self):
        return self.parent.orbit.apoapsis
    
    @Attribute
    def periapsis(self):
        return self.parent.orbit.periapsis
    
    @Attribute
    def satellite_mass(self):
        # return self.parent.mass
        return 2  # kg mass of satellite
    
    @Attribute
    def eclipse_time(self):
        return self.parent.simulate_first_orbit["eclipse_time_per_orbit"]
    
    @Attribute
    def coatings_df(self):
            return pd.read_csv(os.path.join(os.path.dirname(__file__), 'data/thermal_coatings/coatings_SMAD_no_dupl.csv'))
        
    @Attribute
    def Q_internal(self):
        # TODO: Get correct heat dissipation values from the components
        ADCS_dissipation = self.parent.adcs.adcs_selection['Power']
        COMM_dissipation = self.parent.communication.comm_selection['Power_Nom']
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
        if self.selected_coating[f'Cold Margin'] >= 0:
            self.power = 0
            return self.selected_coating['Cold Case']
        else:
            self.power = self.final_heater_values['Heater Power']
            return self.final_heater_values['Cold Case with Heater']

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
                                                    self.selected_coating['Emissivity'], 
                                                    A_S, 
                                                    self.eclipse_time)  # K
            
            P += 0.001  # increase heater power by 1mW

        final_heater_values = {
            'Heater Power': round(P,3),
            'Cold Case with Heater': T,
            'Cold Margin with Heater': T - self.T_min_with_margin_in_K}
        
        return final_heater_values














