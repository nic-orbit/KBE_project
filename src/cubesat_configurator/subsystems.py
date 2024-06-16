from parapy.core import *
from parapy.geom import *
from parapy.exchange.step import STEPReader
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
import itertools
from cubesat_configurator import thermal_helpers as th


class Payload(ac.Subsystem):
    color = Input('yellow', widget=ColorPicker)
    #instrument requirements
    instrument_min_operating_temp = Input() # deg C
    instrument_max_operating_temp = Input() # deg C
    #instrument characteristics
    #### data_rate is a Attribute and inputs are image pixel resolution 
    #### and pixel depth and number of images per day
    # instrument_data_rate = Input() # kbps
    instrument_focal_length = Input() # mm
    instrument_pixel_size = Input() # µm
    # instrument_power_consumption = Input() # W
    # instrument_mass = Input() # kg
    # instrument_cost = Input() # USD
    # ### maybe we can delete these and use just height, width and length?
    # instrument_height = Input() # mm
    # instrument_width = Input() # mm
    # instrument_length = Input() # mm
    ### maybe we can delete these and use just height, width and length?
    # I feel like images per day should be on mission level?
    # instrument_image_width=Input()
    # instrument_image_length=Input()
    instrument_pixel_resolution=Input() # range to be defined or we split this into w and h, consider list
    instrument_bit_depth=Input() #range to be defined (1-24) Check gs for inputvalidator
    
    # mass = Input()
    # height = Input()
    # cost=Input()
    subsystem_type = 'Payload' 
    # Thought it would be nice to check if the sensor fits within the limits of the satellite
    # I saw in extreme cases (15 µm & 4k resolution) it can be almost 60 mm long on the long side. 

    @Attribute
    def _instrument_images_per_day(self):
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
        instrument_data_per_day = self.image_size*self._instrument_images_per_day # kbits
        return ( instrument_data_per_day ) / ( pk.DAY2SEC ) # kbps
    
#All good 
class ADCS(ac.Subsystem):
    required_pointing_accuracy = Input()  # deg
    color = Input('green', widget=ColorPicker)
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
        self.subsystem_type = 'ADCS'
        adcs = self.read_adcs_from_csv
        selected = self.component_selection(adcs, self.requirement_key,  self.required_pointing_accuracy, 'less')
        self.height = selected['Height']
        return selected

#All good    
class COMM(ac.Subsystem):
    requirement_key = 'Data_Rate'
    required_downlink_data_rate = Input()  # Value needs to come from PASEOS simulation (GB)
    color = Input('red', widget=ColorPicker)
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
        self.subsystem_type = 'Communication'
        comm = self.read_comm_from_csv
        tgs = self.parent.simulate_first_orbit["comm_window_per_day"]
        selected = self.component_selection(comm, self.requirement_key,  self.required_downlink_data_rate, 'greater', is_comm=True, tgs=tgs)
        self.height=selected['Height']
        return selected
    
    @Attribute
    def comm_select_df(self):
        df = pd.DataFrame(self.comm_selection)
        print(df)
        return df
    

#All good 
class OBC(ac.Subsystem):
    required_onboard_data_storage = Input()  # Value needs to come from PASEOS simulation (GB)
    requirement_key='Storage'
    color = Input('blue', widget=ColorPicker)
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
        self.subsystem_type = 'Onboard Computer'
        obc = self.read_obc_from_csv()
        obc_selection = self.component_selection(obc, self.requirement_key,  self.required_onboard_data_storage, 'greater')
        self.height = obc_selection['Height']
        return obc_selection
    

class EPS(ac.Subsystem):
    color = Input('Aqua', widget=ColorPicker)    
    
    Solar_cell_type = Input(default='Triple Junction GaAs rigid', widget=Dropdown(['Si rigid panel', 'HES Flexible array','Triple Junction GaAs rigid', 'Triple Junction GaAs ultraflex']))
    
    eclipse_time = Input()

    def read_SolarPanel_from_csv(self):
        sp=self.read_subsystems_from_csv('Solar_Panel.csv')
        selected_panel = sp[sp['Type'] == self.Solar_cell_type]
        return (selected_panel.iloc[0])
    
    def read_bat_from_csv(self):
        return self.read_subsystems_from_csv('Battery.csv')
    
    @Attribute
    def eps_mass(self):
        # mass = battery + solar panel mass
        self.mass = self.battery_selection['Mass'] + self.solar_panel_mass
        return self.battery_selection['Mass'] + self.solar_panel_mass
    
    @Attribute
    def eps_cost(self):
        # cost = battery + solar panel cost
        self.cost = self.battery_selection['Cost'] + self.solar_panel_cost
        return self.battery_selection['Cost'] + self.solar_panel_cost
    
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
        return self.parent.payload.power
    
    @Attribute
    def avg_power_communication(self):
        tgs = self.parent.simulate_first_orbit["comm_window_per_day"]  # input from Paseos
        power_communication = self._communication_power['Power_DL'] * (tgs / (24*3600)) + self._communication_power['Power_Nom'] * (1 - (tgs / (24*3600)))  # tgs = communication time per day       
        return power_communication

    @Attribute
    def eclipse_power(self):
        return(self._adcs_power * constants.Power.duty_cycle + self.avg_power_communication + self._obc_power + self._payload_power + self._thermal_power)

    @Attribute
    def eclipse_power_without_COM(self):
        return(self._adcs_power * constants.Power.duty_cycle + self._obc_power + self._payload_power + self._thermal_power + self._communication_power['Power_Nom'])

    @Attribute
    def average_power_required(self):
        total_power = (self._adcs_power * constants.Power.duty_cycle + self.avg_power_communication + self._obc_power + self._payload_power + self._thermal_power * (self.eclipse_time/self._time_period))
        return total_power*(1+constants.SystemConfig.system_margin)
    
    @Attribute
    def number_of_charging_cycles(self):
        return self._mission_lifetime_yrs*365.25*(24*3600/self._time_period)  
    
    @Attribute
    def min_state_of_charge(self):
        return (-162.1584 + 26.7349 * np.log(self.number_of_charging_cycles))*0.01 # logarithmic approximation of the minimum state of charge based on the number of charging cycles
    
    @Attribute
    def req_battery_capacity(self):
        bat = self.read_bat_from_csv()
        req_battery_capacity = self.min_state_of_charge * self.eclipse_time * self.eclipse_power/3600
        if req_battery_capacity > bat['Capacity'].max():
            req_battery_capacity = self.min_state_of_charge * self.eclipse_time * self.eclipse_power_without_COM
        return req_battery_capacity


    @Attribute
    def battery_selection(self):
        """Select Batteries based on power requirements."""
        self.subsystem_type = 'EPS'
        requirement_key = 'Capacity'
        bat = self.read_bat_from_csv()
        selected = self.component_selection(bat, requirement_key, self.req_battery_capacity, 'greater', subsystem_name='eps')
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
        return (selected_solar_panel['Specific_cost']*self.req_solar_panel_power*1000)
        

     

class Thermal(ac.Subsystem):
    T_max_in_C = Input()  # deg C
    T_min_in_C = Input()  # deg C
    T_margin = Input(5)  # deg C (or K)
    satellite_cp = Input(900)  # J/kgK specific heat capacity of aluminum
    
    @Attribute
    def T_max_with_margin_in_K(self):
        return self.T_max_in_C + 273.15 - self.T_margin # K
    
    @Attribute
    def T_min_with_margin_in_K(self):
        return self.T_min_in_C + 273.15 + self.T_margin # K
    
    @Attribute
    def form_factor(self):
        # return self.parent.structure.form_factor
        return self.parent.structure.form_factor 
    
    @Attribute
    def _apoapsis(self):
        return self.parent.orbit.apoapsis
    
    @Attribute
    def _periapsis(self):
        return self.parent.orbit.periapsis
    
    @Attribute
    def satellite_mass(self):
        
        pl_mass = self.parent.payload.mass
        adcs_mass = self.parent.adcs.mass
        comm_mass = self.parent.communication.mass
        obc_mass = self.parent.obc.mass
        eps_mass = self.parent.power.eps_mass
        structure_mass = self.parent.structure.mass
        total_mass = pl_mass + adcs_mass + comm_mass + obc_mass + eps_mass + structure_mass  # grams
        return total_mass /1000 # kg mass of satellite 
    
    @Attribute
    def eclipse_time(self):
        return self.parent.simulate_first_orbit["eclipse_time_per_orbit"]
    
    @Attribute
    def coatings_df(self):
            return pd.read_csv(os.path.join(os.path.dirname(__file__), 'data/thermal_coatings/coatings_SMAD_no_dupl.csv'))
        
    @Attribute
    def Q_internal(self):
        
        ADCS_dissipation = self.parent.adcs.adcs_selection['Power']
        COMM_dissipation = self.parent.communication.comm_selection['Power_Nom']
        OBC_dissipation = self.parent.obc.obc_selection['Power']
        Payload_dissipation = self.parent.payload.power

        return ADCS_dissipation + COMM_dissipation + OBC_dissipation + Payload_dissipation
    
    @Attribute
    def selected_coating(self):

        U = np.array([1, 1.5, 2, 3], dtype=float)  # form factors

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
            for index, u in enumerate(U):
                T_hot_eq = th.calculate_equilibrium_hot_temp(0, 
                                                            self.Q_internal,
                                                            local_coatings_df.loc[i, 'Absorptivity'], 
                                                            local_coatings_df.loc[i, 'Emissivity'], 
                                                            self._periapsis, 
                                                            self._apoapsis, 
                                                            A_C_max[index], 
                                                            A_C_min, 
                                                            A_S[index])  # K
                T_cold_eq = th.calculate_equilibrium_cold_temp(0, 
                                                            self.Q_internal,
                                                            local_coatings_df.loc[i, 'Absorptivity'], 
                                                            local_coatings_df.loc[i, 'Emissivity'], 
                                                            self._periapsis, 
                                                            self._apoapsis, 
                                                            A_C_max[index], 
                                                            A_C_min, 
                                                            A_S[index])  # K

                # final temperatures for design
                T_hot = T_hot_eq
                
                T_cold = th.exact_transient_solution_cooling(T_cold_eq, 
                                                             T_hot, 
                                                             self.satellite_mass, 
                                                             self.satellite_cp, 
                                                             local_coatings_df.loc[i, 'Emissivity'], 
                                                             A_S[index], 
                                                             self.eclipse_time)  # K

                local_coatings_df.loc[i, f'Hot Case {u}U'] = T_hot  # K
                local_coatings_df.loc[i, f'Cold Case {u}U'] = T_cold  # K
                local_coatings_df.loc[i, f'Hot Margin {u}U'] = self.T_max_with_margin_in_K - T_hot  # K
                local_coatings_df.loc[i, f'Cold Margin {u}U'] = T_cold - self.T_min_with_margin_in_K  # K

        # print coatings_df only the margins
        print(local_coatings_df[['Coating' , 'Hot Margin 1.0U', 'Cold Margin 1.0U', 'Hot Margin 1.5U', 'Cold Margin 1.5U', 'Hot Margin 2.0U', 'Cold Margin 2.0U', 'Hot Margin 3.0U',  'Cold Margin 3.0U']])
        print(float(self.form_factor))
        selected_coating = th.select_coating(float(self.form_factor), local_coatings_df)
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
                                                        self._periapsis, 
                                                        self._apoapsis, 
                                                        A_C_max, 
                                                        A_C_min, 
                                                        A_S)  # K
            T_cold_eq = th.calculate_equilibrium_cold_temp(P, 
                                                        self.Q_internal,
                                                        self.selected_coating['Absorptivity'], 
                                                        self.selected_coating['Emissivity'], 
                                                        self._periapsis, 
                                                        self._apoapsis, 
                                                        A_C_max, 
                                                        A_C_min, 
                                                        A_S)  # K
            T_hot = T_hot_eq
            print(f"for test {T_cold_eq} < {T_hot}")
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














