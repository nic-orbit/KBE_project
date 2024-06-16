from parapy.core import *
from parapy.geom import *
from parapy.core.validate import GreaterThan, IsInstance
from parapy.core.widgets import Dropdown, CheckBox
from parapy.exchange.step import STEPWriter

import pandas as pd

from cubesat_configurator import paseos_parser as pp
from cubesat_configurator import constants
from cubesat_configurator.cubesat import CubeSat
from cubesat_configurator.groundstation import GroundStation
from cubesat_configurator.report_generator import fill_report_template
from datetime import date


class Mission(GeomBase): 
    """
    This class represents a mission for a CubeSat. It includes mission requirements such as lifetime, required Ground Sample Distance (GSD), orbit type, and custom inclination. It also includes system requirements such as pointing accuracy. 

    The class also includes a method to read ground station data from a CSV file and select specific ground stations based on the indices provided in 'ground_station_selection'.

    Inputs:
        mission_lifetime (int): The mission lifetime in months.
        reqiured_GSD (float): The required Ground Sample Distance in meters.
        orbit_type (str): The type of orbit (SSO, Polar, Equatorial, custom).
        custom_inclination (float): The custom inclination in degrees.
        ground_station_selection (list): The indices of the selected ground stations.
        req_pointing_accuracy (float): The required pointing accuracy in degrees.

    Attributes:
        max_orbit_altitude (float): The maximum allowed orbit altitude in km based on the required GSD and the instrument characteristics.
        ground_station_info(list): Reads ground station data from a CSV file, selects specific ground stations, and returns these stations as a list.
        number_of_ground_stations (int): The number of selected ground stations.
    Parts:
        cubesat (CubeSat): The CubeSat.
        groundstation (GroundStation): The GroundStation(s).
    """
    #mission requirements
    mission_lifetime = Input(doc="Mission Lifetime in months") # months
    reqiured_GSD = Input() # m
    number_of_images_per_day = Input() # number
    orbit_type = Input('SSO', widget=Dropdown(["SSO", "Polar", "Equatorial", "custom"])) # SSO, Polar, Equatorial, custom) # SSO, Polar, Equatorial, custom
    custom_inclination = Input(0) # deg 
    # Ground Stations selection
    ground_station_selection = Input(validator=IsInstance(list))
    #system requirements
    req_pointing_accuracy = Input(validator=GreaterThan(0)) # deg
    username = Input('USERNAME', doc="Username for the report")

    @action(label="Generate STEP",
            button_label="Click to generate STEP file.")
    def generate_step(self):
        print("STEP file will be generated for the current configuration: \n")
        # need to calculate total mass before generating STEP file, otherwise the mass of subsystems will be 0!
        print("Calculating total mass...")
        print(f'total mass: {self.cubesat.total_mass}')
        structure = self.cubesat.structure
        structure.subsystem_data_for_stacking
        structure._display_stacking(structure.optimal_stacking_order, structure.form_factor*100)
        print("Generating STEP file...")
        writer = STEPWriter(trees=[self.cubesat], filename = constants.GenericConfig.step_file_location)
        writer.write()

    @action(label="Generate Report",
            button_label="Click to generate report.")
    def generate_report(self):
        print("Generating report...")
        comm_df = pd.DataFrame([self.cubesat.communication.comm_selection])
        comm_df = comm_df.drop(columns=["index", "Pointing_Accuracy", "Storage", "Form_factor",  "Type", "Power", "Capacity" ])
        obc_df = pd.DataFrame([self.cubesat.obc.obc_selection])
        obc_df = obc_df.drop(columns=["index", "Pointing_Accuracy", "Data_Rate", "Form_factor",  "Type", "Power_DL", "Power_Nom", "Capacity" ])
        adcs_df = pd.DataFrame([self.cubesat.adcs.adcs_selection])
        adcs_df = adcs_df.drop(columns=["index", "Data_Rate", "Storage", "Form_factor",  "Type", "Power_DL", "Power_Nom", "Capacity" ])
        bat_df = pd.DataFrame([self.cubesat.power.battery_selection])
        bat_df = bat_df.drop(columns=["index", "Data_Rate", "Pointing_Accuracy", "Storage", "Form_factor",  "Type", "Power", "Power_DL", "Power_Nom" ])
        th_coating_df = pd.DataFrame([self.cubesat.thermal.selected_coating])

        print(comm_df)
        custom_tables = {
            "Ground Station Selection": pd.DataFrame(self.ground_station_info).round({'Lat': 4, 'Lon': 4}),
            "Communication Selection": comm_df.round(2),
            "Onboard Computer Selection": obc_df.round(2),
            "ADCS Selection": adcs_df.round(2),
            "Battery Selection": bat_df.round(2),
            "Thermal Coating Selection": th_coating_df.round(2)
        }

        fill_report_template(constants.GenericConfig.report_template_path, constants.GenericConfig.report_output_path, self.report_data, custom_tables)

    @Attribute
    def report_data(self):
        """
        Returns a dictionary with the data needed to fill the report template.
        """
        self.cubesat.total_mass
        self.cubesat.total_power_consumption
        self.cubesat.total_cost
        return {
            # Introduction
            '<date_generated>': date.today().strftime("%d/%m/%Y"),
            '<author>': self.username,
            # Mission 
            "<mission_lifetime>": str(self.mission_lifetime),
            "<required_GSD>": str(self.reqiured_GSD),
            "<im_per_day>": self.number_of_images_per_day,
            "<orbit_type>": self.orbit_type,
            "<custom_incl>": self.custom_inclination if self.orbit_type == "custom" else "N/A",
            "<gs_list>": self.ground_station_selection,
            # "<selected_gs>": pd.DataFrame(self.ground_station_info).to_string(index=False, header=True, justify='center', col_space=1),
            "<req_point_acc>": self.req_pointing_accuracy,
            # CubeSat Factors
            '<mass_factor>': self.cubesat.mass_factor,
            '<power_factor>': self.cubesat.power_factor,
            '<cost_factor>': self.cubesat.cost_factor,
            # Instrument Specification
            "<ins_min_temp>": self.cubesat.payload.instrument_min_operating_temp,
            "<ins_max_temp>": self.cubesat.payload.instrument_max_operating_temp,    
            '<focal_length>': self.cubesat.payload.instrument_focal_length,
            '<pixel_size>': self.cubesat.payload.instrument_pixel_size,
            '<ins_power>': self.cubesat.payload.power,
            '<ins_mass>': self.cubesat.payload.mass,
            '<ins_height>': self.cubesat.payload.height,
            '<ins_cost>': self.cubesat.payload.cost,
            '<resolution>': self.cubesat.payload.instrument_pixel_resolution,
            '<bit_depth>': self.cubesat.payload.instrument_bit_depth,
            ### OUTPUTS
            # Orbit Design
            "<orb_alt>": self.cubesat.orbit.altitude,
            "<orb_a>": self.cubesat.orbit.semi_major_axis,
            "<orb_e>": self.cubesat.orbit.eccentricity,
            "<orb_i>": self.cubesat.orbit.inclination,
            "<orb_raan>": self.cubesat.orbit.RAAN,
            "<orb_aop>": self.cubesat.orbit.argument_of_periapsis,
            "<orb_ta>": self.cubesat.orbit.true_anomaly,
            "<orb_period>": self.cubesat.orbit.period,
            "<ecl_time_orb>": self.cubesat.simulate_first_orbit['eclipse_time_per_orbit'],
            "<ecl_time_day>": self.cubesat.simulate_first_orbit['eclipse_time_per_day'],
            "<comm_per_orb>": self.cubesat.simulate_first_orbit['comm_window_per_orbit'],
            "<comm_per_day>": self.cubesat.simulate_first_orbit['comm_window_per_day'],
            "<comm_short>": self.cubesat.simulate_first_orbit['shortest_comm_window'],
            "<comm_long>": self.cubesat.simulate_first_orbit['longest_comm_window'],
            "<c_per_day>": self.cubesat.simulate_first_orbit['number_of_contacts_per_day'],
            # Mass Budget
            "<pl_mass>": self.cubesat.payload.mass,
            "<adcs_mass>": self.cubesat.adcs.mass,
            "<obc_mass>": self.cubesat.obc.mass,
            "<str_mass>": self.cubesat.structure.mass,
            "<thm_mass>": self.cubesat.thermal.mass,
            "<comm_mass>": self.cubesat.communication.mass,
            "<power_mass>": self.cubesat.power.mass,
            "<margin_mass>": self.cubesat.total_mass*constants.SystemConfig.system_margin / (1+constants.SystemConfig.system_margin),
            "<total_mass>": self.cubesat.total_mass,
            # Power Budget
            "<pl_power>": self.cubesat.payload.power,
            "<adcs_power>": self.cubesat.adcs.power*constants.Power.duty_cycle,
            "<obc_power>": self.cubesat.obc.power,
            "<str_power>": "N/A",
            "<thm_power>": self.cubesat.power._thermal_power * (self.cubesat.power.eclipse_time/self.cubesat.power._time_period),
            "<comm_power>": self.cubesat.power.avg_power_communication,
            "<power_power>": "N/A",
            "<margin_power>": self.cubesat.power.average_power_required*constants.SystemConfig.system_margin / (1+constants.SystemConfig.system_margin),
            "<total_power>": self.cubesat.power.average_power_required,
            "<peak_power>": self.cubesat.total_power_consumption,
            # Cost Budget
            "<pl_cost>": self.cubesat.payload.cost,
            "<adcs_cost>": self.cubesat.adcs.cost,
            "<obc_cost>": self.cubesat.obc.cost,
            "<str_cost>": self.cubesat.structure.cost,
            "<thm_cost>": self.cubesat.thermal.cost,
            "<comm_cost>": self.cubesat.communication.cost,
            "<power_cost>": self.cubesat.power.cost,
            "<margin_cost>": self.cubesat.total_cost*constants.SystemConfig.system_margin / (1+constants.SystemConfig.system_margin),
            "<total_cost>": self.cubesat.total_cost,
            # Communication 
            "<req_dl>" : self.cubesat.min_downlink_data_rate,
            # OBC
            "<req_store>": self.cubesat.obc.required_onboard_data_storage*1000,
            # ADCS
            "<req_pa>": self.cubesat.adcs.required_pointing_accuracy,
            # Power
            "<req_bc>": self.cubesat.power.req_battery_capacity,
            "<req_spp>": self.cubesat.power.req_solar_panel_power,
            "<sp_area>": self.cubesat.power.solar_panel_area,
            "<sp_mass>": self.cubesat.power.solar_panel_mass,
            "<sp_cost>": self.cubesat.power.solar_panel_cost,
            # Thermal
            "<ttmax>": self.cubesat.thermal.T_max_in_C,
            "<ttmin>": self.cubesat.thermal.T_min_in_C,
            "<ttmargin>": self.cubesat.thermal.T_margin,
            "<th_power>": self.cubesat.thermal.final_heater_values["Heater Power"],
            "<th_cc>": self.cubesat.thermal.final_heater_values["Cold Case with Heater"],
            "<th_cm>": self.cubesat.thermal.final_heater_values["Cold Margin with Heater"],
            # Structure
            "<str_ff>": self.cubesat.structure.form_factor,
            "<str_m>": self.cubesat.structure.mass,
            "<str_c>": self.cubesat.structure.cost,
            "<str_d>": self.cubesat.structure.distance_CoM_to_geometric_center,
        }


    # Not moved to Orbit class becasuse we want to instanciate the Orbit class with altitude as an input
    # # This allows the user to input the altitude directly in the app. 
    @Attribute
    def max_orbit_altitude(self):
        """
        Calculate the maximum allowed orbit altitude (in km) based on the required ground sample distance (GSD) and the instrument
        characteristics.
        """
        h = (self.reqiured_GSD / (self.cubesat.payload.instrument_pixel_size * 10**-6) ) * self.cubesat.payload.instrument_focal_length * 10**-6  # km
        return h
    
    # helper
    @Attribute
    def ground_station_info(self):
        """
        This function reads ground station data from a CSV file, selects specific ground stations based on the indices provided in 'self.ground_station_selection', and returns these selected stations as a list. 

        For each index in 'self.ground_station_selection', the function checks if the index is within the valid range of the stations DataFrame. If it is, the function retrieves the latitude, longitude, company, location, and name of the ground station at that index, appends the station to the 'stations_list', and prints a message indicating the addition of the ground station. If the index is not valid, the function prints a message indicating the absence of a ground station at that index.

        Returns:
            stations_list (list): A list of selected ground stations from the CSV file.
        """
        stations = pp.read_ground_stations_from_csv()
        stations_list = []

        for i in self.ground_station_selection:
        # check that index is within the list
            if 0 <= i <= stations.last_valid_index():
                station_dict = {
                    "Name": f"GS_{stations.loc[i, 'Number']} ({stations.loc[i, 'Location']})",
                    "Lat": stations.loc[i, "Lat"],
                    "Lon": stations.loc[i, "Lon"],
                    "Company": stations.loc[i, "Company"],
                    "Location": stations.loc[i, "Location"],
                    "Elevation": stations.loc[i, "Elevation"],
                    "Number": f"{stations.loc[i, 'Number']}"                    
                }
                stations_list.append(station_dict)
                print(f"Added '{station_dict['Company']}' groundstation {i} located at {station_dict['Location']}")
            else:
                print(f"No ground station with index {i} in data.")
        
        return stations_list

    # helper
    @Attribute
    def number_of_ground_stations(self):
        """
        Returns the number of selected ground stations.
        More specifically, the function returns the length of the 'ground_station_selection' list.
        """
        return len(self.ground_station_selection)

    @Part
    def cubesat(self):
        """
        Returns one CubeSat instance.
        """
        return CubeSat()
    
    @Part
    def groundstation(self):
        """
        Returns a Sequence of GroundStation instances based on the selected ground stations.
        """
        return GroundStation(quantify=self.number_of_ground_stations,
                             latitude=self.ground_station_info[child.index]['Lat'],
                             longitude=self.ground_station_info[child.index]['Lon'],
                             elevation=self.ground_station_info[child.index]['Elevation'],
                             company=self.ground_station_info[child.index]['Company'],
                             location=self.ground_station_info[child.index]['Location'],
                             name=self.ground_station_info[child.index]['Name'],
                             number=self.ground_station_info[child.index]['Number']
                             )