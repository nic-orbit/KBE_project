from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo, IsInstance, Range
from cubesat_configurator import subsystems as subsys
from cubesat_configurator import subsystem as ac
import numpy as np
import pykep as pk
import yaml
import os
from pprint import pprint
from cubesat_configurator import paseos_parser as pp
import paseos
from paseos import ActorBuilder, SpacecraftActor, GroundstationActor, PowerDeviceType
from cubesat_configurator import constants
from cubesat_configurator.orbit import Orbit
import matplotlib.pyplot as plt
from cubesat_configurator.structure import Structure
import matplotlib.pyplot as plt




class CubeSat(GeomBase):
    cost_factor = Input(0.3, validator=Range(0, 1))
    mass_factor = Input(0.4, validator=Range(0, 1))
    power_factor = Input(0.3, validator=Range(0, 1))

    

    @Attribute
    def total_mass(self): # Do we need overall mass and power using a margin first?
        """
        Calculate the total mass of the CubeSat based on the mass of the subsystems (bottom-up approach) for final reporting. 
        """
        mass = 0
        for child in self.children:
            if child.__class__.__name__ == "EPS":
                mass += child.eps_mass
            elif isinstance(child, (ac.Subsystem, Structure)) and hasattr(child, "mass"):
                mass += child.mass
        return mass*(1 + constants.SystemConfig.system_margin) # kg

    @Attribute
    def total_power_consumption(self):
        """
        Calculate the total power consumption of the CubeSat based on the average power consumption of the subsystems (bottom-up approach) for final reporting. 
        """
        power = 0
        for child in self.children:
            if isinstance(child, (ac.Subsystem)) and hasattr(child, "power") and child.power is not None: # no need to include Structure in power calculation
                power += child.power
        return power*(1 + constants.SystemConfig.system_margin) # W
    
    @Attribute
    def total_cost(self):
        """
        Calculate the total cost of the CubeSat based on the cost of the subsystems (bottom-up approach) for final reporting. 
        """
        cost = 0
        for child in self.children:
            if child.__class__.__name__ == "EPS":
                cost += child.eps_cost
            elif isinstance(child, (ac.Subsystem, Structure)) and hasattr(child, "cost") and child.cost is not None:
                cost += child.cost
        return cost*(1 + constants.SystemConfig.system_margin) # USD

    @Attribute
    def system_data_rate(self):
        """
        Calculate the system data rate based on the payload data rate and the margin.
        Assumes that the payload data rate is significantly the highest data rate in the system, which is to be expected for Earth Observation applications.
        Also assumes that the system margin covers the satellite bus data rate. 
        """
        return self.payload.instrument_data_rate*(1 + constants.SystemConfig.system_margin) # kbps
    
    @Attribute
    def min_downlink_data_rate(self):
        """
        Calculate the minimum required downlink data rate based on the system data rate and the communication window fraction.
        DLDR = System Data Rate / Communication Window Fraction of the orbit
        """
        return self.system_data_rate/(self.simulate_first_orbit["comm_window_fraction"]) * (1+constants.SystemConfig.system_margin) # kbps

    @Part 
    def orbit(self):
        """
        Returns an instance of the Orbit class with the maximum allowed orbital altitude from the mission as input.
        """
        return Orbit(altitude=self.parent.max_orbit_altitude)
    
    
    @Attribute
    def simulate_first_orbit(self):
        """
        Simulates the first run of paseos for a day to get communication windows and eclipse times. 
        """
        verbose = False
        plotting = False
        # Things that will be calculated
        eclipse_time = 0

        # Set the start epoch of the simulation
        t0 = constants.PaseosConfig.start_epoch
        # Create a spacecraft actor
        sat_actor = ActorBuilder.get_actor_scaffold(name="myCubeSat",
                                        actor_type=SpacecraftActor,
                                        epoch=t0)

        # Set the orbit of sat_actor.
        ActorBuilder.set_orbit(actor=sat_actor,
                            position=self.orbit.position_vector,
                            velocity=self.orbit.velocity_vector,
                            epoch=t0, 
                            central_body=constants.PaseosConfig.earth
                            )
        
        # Initialize PASEOS simulation
        sim = paseos.init_sim(sat_actor)

        used_gs_list = pp.set_ground_station(t0, sim, self.parent.groundstation)

        used_gs_info_list = []

        # set ground station contact info instances
        for gs in used_gs_list:
            gs_info_instance = pp.GroundContactInfo(spacecraft=sat_actor, station=gs)
            used_gs_info_list.append(gs_info_instance)

        T = self.orbit.period
        # simulation timestep
        dt = constants.PaseosConfig.simulation_timestep # s
        # days to simulate
        days_to_simulate = constants.PaseosConfig.days_to_simulate # days
        # number of orbits to simulate = 1 day / orbital period * days to simulate = Number of orbits to simulate
        orbits_to_simulate = np.ceil(pk.DAY2SEC / T) * days_to_simulate  # orbits
        # number of runs = number of seconds in a day / simulation timestep
        runs = int(pk.DAY2SEC / dt) * days_to_simulate
        # print(f"runs: {runs}")

        if plotting:
            plotter = paseos.plot(sim, paseos.PlotType.SpacePlot)

        simulation_inputs = {
            "simulation_start": t0,
            "simulation_duration": pk.DAY2SEC,
            "orbits_to_simulate": orbits_to_simulate,
            "days_to_simulate": days_to_simulate,
            "runs": runs,
            "dt": dt,
            "altitude": self.orbit.altitude,
            "period": T,
            "N_ground_stations": len(used_gs_info_list),
        }
        
        # print simulation parameters
        if verbose:
            print(
                "-----------------------------------------------------\n"
                f" starting simulation for {orbits_to_simulate} orbits with {runs} runs  \n"
                "-----------------------------------------------------"
            )

        for i in range(runs):

            eclipse_flag = sat_actor.is_in_eclipse()
            if eclipse_flag:
                eclipse_time += dt

            for gs_info in used_gs_info_list:
                gs_info.has_link_to_ground_station()

            # advance the time
            sim.advance_time(dt, 0)

            if plotting:
                plotter.update(sim)

        if plotting:
            plotter.animate(sim=sim, dt=dt, steps=runs, save_to_file="animations\mymovie")

        total_comm_window = 0
        comm_windows = []

        for gs_info in used_gs_info_list:
            contact_time = gs_info.total_contact_time()
            total_comm_window += contact_time 
            comm_windows.extend(gs_info.comm_window_list)

        # RESULTS
        simulation_results = {
            "simulation_inputs": simulation_inputs,
            "simulation_start": t0,
            "simulation_end": sat_actor.local_time,
            "simulation_duration": round((sat_actor.local_time.mjd2000 - t0.mjd2000)*pk.DAY2SEC,1),
            "eclipse_time_per_day": eclipse_time / days_to_simulate,
            "eclipse_time_per_orbit": eclipse_time / orbits_to_simulate,
            "comm_window_per_day": total_comm_window / days_to_simulate,
            "comm_window_per_orbit": total_comm_window / orbits_to_simulate,
            "comm_window_fraction": total_comm_window / (orbits_to_simulate * T),
            "shortest_comm_window": min(comm_windows),
            "average_comm_window": total_comm_window / len(comm_windows),
            "longest_comm_window": max(comm_windows),
            "number_of_contacts_per_day": len(comm_windows) / days_to_simulate,
        }

        if verbose:
            # print end time of simulation
            print(
                "-----------------------------------------------------\n"
                f" simulation ended at: {simulation_results['simulation_start']}   \n"
                f" simulation duration: {simulation_results['simulation_duration']} \n"
                "-----------------------------------------------------")
            print(
                f" avg comms window per orbit: {round(simulation_results['comm_window_per_orbit'], 2)} [s/orbit]  \n"
                f" avg comms percentage of orbit: {round( simulation_results['comm_window_fraction'], 4)} %  \n"
                "-----------------------------------------------------"
            )
            print(
                f" total comms window per day: {round(simulation_results['comm_window_per_day'], 1)} [s/day]  \n"
                "-----------------------------------------------------"
            )
            print(
                f" shortest comms window: {simulation_results['shortest_comm_window']} [s]  \n"
                "-----------------------------------------------------"
            )
            print(
                f" average comms window: {round(simulation_results['average_comm_window'], 2)} [s] \n"
                "-----------------------------------------------------"
            )
            print(
                f" longest comms window: {simulation_results['longest_comm_window']} [s] \n"
                "-----------------------------------------------------"
            )
            # print number of contacts
            print(
                f" number of contacts: {simulation_results['number_of_contacts_per_day']} ----------\n"
                "-----------------------------------------------------"
            )
        
        return simulation_results

    
    @Attribute
    def simulate_second_orbit(self):
        """
        Simulates the first run of paseos for a day to get communication windows and eclipse times. 
        """
        verbose = False
        plotting = False
        # Things that will be calculated
        eclipse_time = 0
        onboard_data = 0 # kbits
        pictures_taken = 0
        status_dict = { 
            "time_s": [],
            "time_h": [],
            "eclipse": [],
            "contact": [],
            "power_consumption": [],
            "battery_SoC": [],
            "onboard_data": [],
            "comm_windows": [],
        } # status dict for plotting

        # Getting parameters from other places

        # satellite parameters
        power_comm = 10 # W
        power_idle = 3 # W
        bus_data_rate = self.system_data_rate * constants.SystemConfig.system_margin / (1+constants.SystemConfig.system_margin) # kbits/s

        # Orbit parameters
        T = self.orbit.period # s

        # simulation configuration parameters
        dt = constants.PaseosConfig.simulation_timestep # s
        days_to_simulate = constants.PaseosConfig.days_to_simulate # days

        # Image parameters
        Im_width = self.payload.instrument_pixel_resolution[0]
        Im_height = self.payload.instrument_pixel_resolution[1]
        Im_bit_depth = self.payload.instrument_bit_depth
        images_per_day = self.payload._instrument_images_per_day
        time_btw_pics = pk.DAY2SEC/images_per_day # in seconds

        # Communication parameters
        downlink_data_rate = self.min_downlink_data_rate # kbps

        # EPS parameters
        capacity = 30 * 3600 # Ws
        charging_rate = 5 # W

        picture_size = self.payload.image_size # kbits

        # Set the start epoch of the simulation
        t0 = constants.PaseosConfig.start_epoch
        # Create a spacecraft actor
        sat_actor = ActorBuilder.get_actor_scaffold(name="myCubeSat",
                                        actor_type=SpacecraftActor,
                                        epoch=t0)

        # Set the orbit of sat_actor.
        ActorBuilder.set_orbit(actor=sat_actor,
                            position=self.orbit.position_vector,
                            velocity=self.orbit.velocity_vector,
                            epoch=t0, 
                            central_body=constants.PaseosConfig.earth)
        
        ActorBuilder.add_comm_device(actor=sat_actor,
                             device_name="comm_1",
                             bandwidth_in_kbps=downlink_data_rate)

        ActorBuilder.set_power_devices(actor=sat_actor,
                                    battery_level_in_Ws=capacity, # start with full battery
                                    max_battery_level_in_Ws=capacity,
                                    charging_rate_in_W=charging_rate,
                                    power_device_type=PowerDeviceType.SolarPanel)
        
        # Initialize PASEOS simulation
        sim = paseos.init_sim(sat_actor)

        used_gs_list = pp.set_ground_station(t0, sim, self.parent.groundstation)

        used_gs_info_list = []

        # set ground station contact info instances
        for gs in used_gs_list:
            gs_info_instance = pp.GroundContactInfo(spacecraft=sat_actor, station=gs)
            used_gs_info_list.append(gs_info_instance)

        # number of orbits to simulate = 1 day / orbital period = Number of orbits in a day
        orbits_to_simulate = np.ceil(pk.DAY2SEC / T) * days_to_simulate  # orbits
        # number of runs = number of seconds in a day / simulation timestep
        runs = int(days_to_simulate * pk.DAY2SEC / dt) 
        # print(f"runs: {runs}")

        if plotting:
            plotter = paseos.plot(sim, paseos.PlotType.SpacePlot)

        simulation_inputs = {
            "simulation_start": t0,
            "simulation_duration": pk.DAY2SEC,
            "orbits_to_simulate": orbits_to_simulate,
            "runs": runs,
            "dt": dt,
            "altitude": self.orbit.altitude,
            "period": T,
            "N_ground_stations": len(used_gs_info_list),
        }
        
        # print simulation parameters
        if verbose:
            print(
                "-----------------------------------------------------\n"
                f" starting simulation for {orbits_to_simulate} orbits with {runs} runs  \n"
                "-----------------------------------------------------"
            )
        #######################
        ### SIMULATION LOOP ###
        #######################

        for i in range(runs):

            eclipse_flag = sat_actor.is_in_eclipse()
            if eclipse_flag:
                eclipse_time += dt

            contact_list = []
            for gs_info in used_gs_info_list:
                contact = gs_info.has_link_to_ground_station()
                contact_list.append(contact)

            # if there is a contact with any ground station
            # calculate the power consumption and data rate
            if any(contact_list):
                power_consumption = power_comm  # W
                # reduce the onboard data by the downlink data rate until it reaches 0
                onboard_data -= downlink_data_rate*dt
                if onboard_data < 0:
                    onboard_data = 0
            else:
                power_consumption = power_idle  # W

            # check if it is time to take a picture, this basically divides the orbit in equal time intervals and takes a picture at each interval
            # simulation starts halfway through the first interval, so the first picture is taken at t = t0 + time_btw_pics/2
            local_time_since_start = (sat_actor.local_time.mjd2000 - t0.mjd2000)*pk.DAY2SEC
            PICTURE_OVERDUE = local_time_since_start > time_btw_pics*(0.5+pictures_taken) # 0.5 is a buffer time, to avoid taking picture right at the edges of the time interval
            if PICTURE_OVERDUE:
                onboard_data += picture_size
                pictures_taken += 1
                print(" ------------- PICTURE TAKEN! --------------------\n"
                    f"Picture nr {pictures_taken} taken at: {sat_actor.local_time}\n"
                    "----------------------------------------------------")

            # update the status dict for plotting
            status_dict["time_s"].append(sim.simulation_time - t0.mjd2000*pk.DAY2SEC)
            status_dict["time_h"].append(((sim.simulation_time - t0.mjd2000*pk.DAY2SEC))/3600)
            status_dict["eclipse"].append(eclipse_flag)
            status_dict["contact"].append(contact)
            status_dict["power_consumption"].append(power_consumption)
            status_dict["battery_SoC"].append(sat_actor.state_of_charge)
            status_dict["onboard_data"].append(onboard_data)

            # update onboard data with the bus data rate
            onboard_data += bus_data_rate*dt

            # advance the time
            sim.advance_time(dt, power_consumption)

            if plotting:
                plotter.update(sim)


        if plotting:
            plotter.animate(sim=sim, dt=dt, steps=runs, save_to_file="animations\mymovie")

        #################################
        ######## POST-PROCESSING ########
        #################################

        # find maximum onboard data
        max_onboard_data = max(status_dict["onboard_data"])
        # find the minimum onboard data, after the maximum onboard data has been reached
        min_onboard_data = min(status_dict["onboard_data"][status_dict["onboard_data"].index(max_onboard_data):])


        total_comm_window = 0
        comm_windows = []

        for gs_info in used_gs_info_list:
            contact_time = gs_info.total_contact_time()
            total_comm_window += contact_time 
            comm_windows.extend(gs_info.comm_window_list)

        status_dict["comm_windows"] = comm_windows

        #################################
        ############ RESULTS ############
        #################################

        simulation_results = {
            "simulation_inputs": simulation_inputs,
            "simulation_start": t0,
            "simulation_end": sat_actor.local_time,
            "simulation_duration": round((sat_actor.local_time.mjd2000 - t0.mjd2000)*pk.DAY2SEC,1),
            "eclipse_time_per_day": eclipse_time / days_to_simulate,
            "comm_window_per_day": total_comm_window / days_to_simulate,
            "comm_window_per_orbit": total_comm_window / orbits_to_simulate,
            "comm_window_fraction": total_comm_window / (orbits_to_simulate * T),
            "comm_window_fraction2": total_comm_window / (pk.DAY2SEC * days_to_simulate),
            "shortest_comm_window": min(comm_windows),
            "average_comm_window": total_comm_window / len(comm_windows),
            "longest_comm_window": max(comm_windows),
            "number_of_contacts_per_day": len(comm_windows) / days_to_simulate,
            "maximum_onboard_data": max_onboard_data,
            "minimum_onboard_data": min_onboard_data,
        }

        if verbose:
            # print end time of simulation
            print(
                "-----------------------------------------------------\n"
                f" simulation ended at: {simulation_results['simulation_start']}   \n"
                f" simulation duration: {simulation_results['simulation_duration']} \n"
                "-----------------------------------------------------")
            print(
                f" avg comms window per orbit: {round(simulation_results['comm_window_per_orbit'], 2)} [s/orbit]  \n"
                f" avg comms percentage of orbit: {round( simulation_results['comm_window_fraction'], 4)} %  \n"
                "-----------------------------------------------------"
            )
            print(
                f" total comms window per day: {round(simulation_results['comm_window_per_day'], 1)} [s/day]  \n"
                "-----------------------------------------------------"
            )
            print(
                f" shortest comms window: {simulation_results['shortest_comm_window']} [s]  \n"
                "-----------------------------------------------------"
            )
            print(
                f" average comms window: {round(simulation_results['average_comm_window'], 2)} [s] \n"
                "-----------------------------------------------------"
            )
            print(
                f" longest comms window: {simulation_results['longest_comm_window']} [s] \n"
                "-----------------------------------------------------"
            )
            # print number of contacts
            print(
                f" number of contacts: {len(comm_windows)} ----------\n"
                "-----------------------------------------------------"
            )
        # self.simulation_status = status_dict
        return simulation_results
    
    @Attribute
    def simulate_last_orbit(self):
        """
        Simulates the first run of paseos for a day to get communication windows and eclipse times. 
        """
        verbose = False
        plotting = False
        # Things that will be calculated
        eclipse_time = 0
        onboard_data = 0 # kbits
        pictures_taken = 0
        status_dict = { 
            "time_s": [],
            "time_h": [],
            "eclipse": [],
            "contact": [],
            "power_consumption": [],
            "battery_SoC": [],
            "onboard_data": [],
            "comm_windows": [],
            "temperature": [],
        } # status dict for plotting

        # Getting parameters from other places

        # satellite parameters
        power_comm = self.power._communication_power['Power_DL'] # W
        power_idle = self.power._communication_power['Power_Nom'] # W
        bus_data_rate = self.system_data_rate * constants.SystemConfig.system_margin / (1+constants.SystemConfig.system_margin) # kbits/s
        mass = self.total_mass # kg
        alpha = self.thermal.selected_coating["Absorptivity"]
        epsilon = self.thermal.selected_coating["Emissivity"]
        side_panel = self.structure.form_factor * 0.01  # m^2
        front_panel = 0.01  # m^2
        T0_in_K = (self.thermal.selected_coating["Hot Case"] + self.thermal.selected_coating["Cold Case"])/2  # K

        # Orbit parameters
        T = self.orbit.period # s

        # simulation configuration parameters
        dt = constants.PaseosConfig.simulation_timestep # s
        days_to_simulate = constants.PaseosConfig.days_to_simulate # days

        # Image parameters
        images_per_day = self.payload._instrument_images_per_day
        time_btw_pics = pk.DAY2SEC/images_per_day # in seconds

        # Communication parameters
        downlink_data_rate = self.min_downlink_data_rate # kbps

        # EPS parameters
        capacity = self.power.battery_selection["Capacity"]*3600  # Ws
        charging_rate = self.power.req_solar_panel_power  # W

        picture_size = self.payload.image_size # kbits

        # Set the start epoch of the simulation
        t0 = constants.PaseosConfig.start_epoch
        # Create a spacecraft actor
        sat_actor = ActorBuilder.get_actor_scaffold(name="myCubeSat",
                                        actor_type=SpacecraftActor,
                                        epoch=t0)

        # Set the orbit of sat_actor.
        ActorBuilder.set_orbit(actor=sat_actor,
                            position=self.orbit.position_vector,
                            velocity=self.orbit.velocity_vector,
                            epoch=t0, 
                            central_body=constants.PaseosConfig.earth)
        
        ActorBuilder.set_thermal_model(
            actor=sat_actor,
            actor_mass=mass,
            actor_initial_temperature_in_K=T0_in_K,
            actor_sun_absorptance=alpha,
            actor_infrared_absorptance=epsilon,
            actor_sun_facing_area=side_panel,
            actor_central_body_facing_area=side_panel,
            actor_emissive_area=4 * side_panel + 2 * front_panel,
            actor_thermal_capacity=900,
            power_consumption_to_heat_ratio=1,
    )
        
        ActorBuilder.add_comm_device(actor=sat_actor,
                             device_name="comm_1",
                             bandwidth_in_kbps=downlink_data_rate)

        ActorBuilder.set_power_devices(actor=sat_actor,
                                    battery_level_in_Ws=capacity, # start with full battery
                                    max_battery_level_in_Ws=capacity,
                                    charging_rate_in_W=charging_rate,
                                    power_device_type=PowerDeviceType.SolarPanel)
        
        # Initialize PASEOS simulation
        sim = paseos.init_sim(sat_actor)

        used_gs_list = pp.set_ground_station(t0, sim, self.parent.groundstation)

        used_gs_info_list = []

        # set ground station contact info instances
        for gs in used_gs_list:
            gs_info_instance = pp.GroundContactInfo(spacecraft=sat_actor, station=gs)
            used_gs_info_list.append(gs_info_instance)

        # number of orbits to simulate = 1 day / orbital period = Number of orbits in a day
        orbits_to_simulate = np.ceil(pk.DAY2SEC / T) * days_to_simulate  # orbits
        # number of runs = number of seconds in a day / simulation timestep
        runs = int(days_to_simulate * pk.DAY2SEC / dt) 
        # print(f"runs: {runs}")

        if plotting:
            plotter = paseos.plot(sim, paseos.PlotType.SpacePlot)

        simulation_inputs = {
            "simulation_start": t0,
            "simulation_duration": pk.DAY2SEC,
            "orbits_to_simulate": orbits_to_simulate,
            "runs": runs,
            "dt": dt,
            "altitude": self.orbit.altitude,
            "period": T,
            "N_ground_stations": len(used_gs_info_list),
        }
        
        # print simulation parameters
        if verbose:
            print(
                "-----------------------------------------------------\n"
                f" starting simulation for {orbits_to_simulate} orbits with {runs} runs  \n"
                "-----------------------------------------------------"
            )
        #######################
        ### SIMULATION LOOP ###
        #######################

        for i in range(runs):

            eclipse_flag = sat_actor.is_in_eclipse()
            if eclipse_flag:
                eclipse_time += dt

            contact_list = []
            for gs_info in used_gs_info_list:
                contact = gs_info.has_link_to_ground_station()
                contact_list.append(contact)

            # if there is a contact with any ground station
            # calculate the power consumption and data rate
            if any(contact_list):
                power_consumption = power_comm  # W
                # reduce the onboard data by the downlink data rate until it reaches 0
                onboard_data -= downlink_data_rate*dt
                if onboard_data < 0:
                    onboard_data = 0
            else:
                power_consumption = power_idle  # W

            # check if it is time to take a picture, this basically divides the orbit in equal time intervals and takes a picture at each interval
            # simulation starts halfway through the first interval, so the first picture is taken at t = t0 + time_btw_pics/2
            local_time_since_start = (sat_actor.local_time.mjd2000 - t0.mjd2000)*pk.DAY2SEC
            PICTURE_OVERDUE = local_time_since_start > time_btw_pics*(0.5+pictures_taken) # 0.5 is a buffer time, to avoid taking picture right at the edges of the time interval
            if PICTURE_OVERDUE:
                onboard_data += picture_size
                pictures_taken += 1
                print(" ------------- PICTURE TAKEN! --------------------\n"
                    f"Picture nr {pictures_taken} taken at: {sat_actor.local_time}\n"
                    "----------------------------------------------------")
                
            temperature = sat_actor.temperature_in_C

            # update the status dict for plotting
            status_dict["time_s"].append(sim.simulation_time - t0.mjd2000*pk.DAY2SEC)
            status_dict["time_h"].append(((sim.simulation_time - t0.mjd2000*pk.DAY2SEC))/3600)
            status_dict["eclipse"].append(eclipse_flag)
            status_dict["contact"].append(contact)
            status_dict["power_consumption"].append(power_consumption)
            status_dict["battery_SoC"].append(sat_actor.state_of_charge)
            status_dict["onboard_data"].append(onboard_data)
            status_dict["temperature"].append(temperature)

            # update onboard data with the bus data rate
            onboard_data += bus_data_rate*dt

            if dt*power_consumption > capacity*status_dict["battery_SoC"][-1]:
                power_consumption = 0

            # advance the time
            sim.advance_time(dt, power_consumption)

            if plotting:
                plotter.update(sim)


        if plotting:
            plotter.animate(sim=sim, dt=dt, steps=runs, save_to_file=constants.PaseosConfig.animation_output_path)

        #################################
        ######## POST-PROCESSING ########
        #################################

        # find maximum onboard data
        max_onboard_data = max(status_dict["onboard_data"])
        # find the minimum onboard data, after the maximum onboard data has been reached
        min_onboard_data = min(status_dict["onboard_data"][status_dict["onboard_data"].index(max_onboard_data):])


        total_comm_window = 0
        comm_windows = []

        for gs_info in used_gs_info_list:
            contact_time = gs_info.total_contact_time()
            total_comm_window += contact_time 
            comm_windows.extend(gs_info.comm_window_list)

        status_dict["comm_windows"] = comm_windows

        #################################
        ############ RESULTS ############
        #################################

        simulation_results = {
            "simulation_inputs": simulation_inputs,
            "simulation_start": t0,
            "simulation_end": sat_actor.local_time,
            "simulation_duration": round((sat_actor.local_time.mjd2000 - t0.mjd2000)*pk.DAY2SEC,1),
            "eclipse_time_per_day": eclipse_time / days_to_simulate,
            "comm_window_per_day": total_comm_window / days_to_simulate,
            "comm_window_per_orbit": total_comm_window / orbits_to_simulate,
            "comm_window_fraction": total_comm_window / (orbits_to_simulate * T),
            "comm_window_fraction2": total_comm_window / (pk.DAY2SEC * days_to_simulate),
            "shortest_comm_window": min(comm_windows),
            "average_comm_window": total_comm_window / len(comm_windows),
            "longest_comm_window": max(comm_windows),
            "number_of_contacts_per_day": len(comm_windows) / days_to_simulate,
            "maximum_onboard_data": max_onboard_data,
            "minimum_onboard_data": min_onboard_data,
        }

        if verbose:
            # print end time of simulation
            print(
                "-----------------------------------------------------\n"
                f" simulation ended at: {simulation_results['simulation_start']}   \n"
                f" simulation duration: {simulation_results['simulation_duration']} \n"
                "-----------------------------------------------------")
            print(
                f" avg comms window per orbit: {round(simulation_results['comm_window_per_orbit'], 2)} [s/orbit]  \n"
                f" avg comms percentage of orbit: {round( simulation_results['comm_window_fraction'], 4)} %  \n"
                "-----------------------------------------------------"
            )
            print(
                f" total comms window per day: {round(simulation_results['comm_window_per_day'], 1)} [s/day]  \n"
                "-----------------------------------------------------"
            )
            print(
                f" shortest comms window: {simulation_results['shortest_comm_window']} [s]  \n"
                "-----------------------------------------------------"
            )
            print(
                f" average comms window: {round(simulation_results['average_comm_window'], 2)} [s] \n"
                "-----------------------------------------------------"
            )
            print(
                f" longest comms window: {simulation_results['longest_comm_window']} [s] \n"
                "-----------------------------------------------------"
            )
            # print number of contacts
            print(
                f" number of contacts: {len(comm_windows)} ----------\n"
                "-----------------------------------------------------"
            )
        return status_dict
    
    @Attribute
    def required_onboard_data_storage(self):
        """
        Calculate the required onboard data storage based on the maximum onboard data and the margin.
        """
        return self.simulate_second_orbit["maximum_onboard_data"]*(1 + constants.SystemConfig.system_margin)
    
    @Attribute
    def system_max_allowed_temperature(self):
        """
        Calculate the maximum allowed temperature of the CubeSat based on the maximum allowed temperature of the subsystems.
        """
        pl_max_temp = self.payload.instrument_max_operating_temp
        comm_max_temp = self.communication.comm_selection['Max_Temp']
        power_max_temp = self.power.battery_selection['Max_Temp']
        obc_max_temp = self.obc.obc_selection['Max_Temp']

        return min(pl_max_temp, comm_max_temp, power_max_temp, obc_max_temp)  # deg C
    
    @Attribute
    def system_min_allowed_temperature(self):
        """
        Calculate the minimum allowed temperature of the CubeSat based on the minimum allowed temperature of the subsystems.
        """
        pl_min_temp = self.payload.instrument_min_operating_temp
        comm_min_temp = self.communication.comm_selection['Min_Temp']
        power_min_temp = self.power.battery_selection['Min_Temp']
        obc_min_temp = self.obc.obc_selection['Min_Temp']

        return max(pl_min_temp, comm_min_temp, power_min_temp, obc_min_temp)  # deg C

    @Attribute
    def plot_simulation_data(self):
        """
        Plot the simulation data for the first orbit.
        """
        
        status_dict = self.simulate_last_orbit
        # Extracting data
        time = status_dict["time_s"]
        hours = status_dict["time_h"]
        eclipse = status_dict["eclipse"]
        contact = status_dict["contact"]
        power_consumption = status_dict["power_consumption"]
        battery_SoC = status_dict["battery_SoC"]
        onboard_data = status_dict["onboard_data"]
        comm_windows = status_dict["comm_windows"]

        # Plotting the data
        fig = plt.figure(figsize=(12, 8))

        # Plot eclipse
        plt.subplot(3, 3, 1)
        plt.plot(hours, eclipse, label="Eclipse")
        plt.xlabel("Time [hours]")
        plt.ylabel("Eclipse")
        plt.title("Eclipse over Time")
        plt.grid(True)

        # Plot contact
        plt.subplot(3, 3, 2)
        plt.plot(hours, contact, label="Contact", color='orange')
        plt.xlabel("Time [hours]")
        plt.ylabel("Contact")
        plt.title("Contact over Time")
        plt.grid(True)

        # Plot power consumption
        plt.subplot(3, 3, 3)
        plt.plot(hours, power_consumption, label="Power Consumption", color='green')
        plt.xlabel("Time [hours]")
        plt.ylabel("Power Consumption (W)")
        plt.title("Power Consumption over Time")
        plt.grid(True)

        # Plot battery DoD
        plt.subplot(3, 3, 4)
        plt.plot(hours, battery_SoC, label="battery SoC", color='red')
        plt.xlabel("Time [hours]")
        plt.ylabel("Battery SoC (%)")
        plt.title("Battery State of Charge over Time")
        plt.grid(True)

        # Plot comms window duration
        plt.subplot(3, 3, 6)
        plt.hist(comm_windows, bins=10, color='blue')
        plt.xlabel("Comm Window Duration (s)")
        plt.ylabel("Frequency")
        plt.title("Comm Window Duration Histogram")
        plt.grid(False)

        # Plot onboard data
        plt.subplot(3, 3, 5)
        plt.plot(hours, onboard_data, label="Onboard Data", color='purple')
        plt.xlabel("Time [hours]")
        plt.ylabel("Onboard Data (kbits)")
        plt.title("Onboard Data over Time")
        plt.grid(True)

        # Plot temperature
        plt.subplot(3, 3, 7)
        plt.plot(hours, status_dict["temperature"], label="Temperature", color='black')
        plt.xlabel("Time [hours]")
        plt.ylabel("Temperature (C)")
        plt.title("Temperature over Time")
        plt.grid(True)

        # Sample path to the map of the earth, replace with the actual path to your map image
        earth_map_path = r"src\cubesat_configurator\images\earth.jpg"

        # Load the image of the Earth
        img = plt.imread(earth_map_path)

        # Plot the ground station locations
        plt.subplot(3, 3, 8)
        plt.imshow(img, extent=[-180, 180, -90, 90])
        for gs in self.parent.groundstation:
            plt.scatter(gs.longitude, gs.latitude, label=gs.name, color='red')
            plt.text(gs.longitude, gs.latitude, gs.name, fontsize=9, ha='right', color='blue')

        plt.xlabel("Longitude")
        plt.ylabel("Latitude")
        plt.title("Ground Station Locations")
        plt.grid(False)

        plt.tight_layout()

        plt.savefig(constants.PaseosConfig.simulation_plots_location)
        plt.close()

        return status_dict



    @Part
    def payload(self):
        """
        Returns an instance of the Payload class.
        """
        return subsys.Payload(instrument_min_operating_temp=-10, # deg C
                              instrument_max_operating_temp=50, # deg C
                              instrument_focal_length=40, # mm
                              instrument_pixel_size=7,  # µm - Typical values for industrial cameras range from 1.5 to 15 µm ( bigger --> better SNR, but larger (worse) GSD )
                              power = 1, # W
                              mass = 500, # g
                              height=50, # mm
                              cost=10000, # USD
                              instrument_pixel_resolution = [1260, 1260], # pixels
                              instrument_bit_depth=8 #range to be defined (1-24) Check gs for inputvalidator
                              )
    
    @Part
    def communication(self):
        """
        Returns an instance of the COMM class.
        """
        return subsys.COMM(required_downlink_data_rate=self.min_downlink_data_rate)
    
    @Part
    def power(self):
        """
        Returns an instance of the EPS class.
        """
        return subsys.EPS(eclipse_time=self.simulate_first_orbit["eclipse_time_per_orbit"])
    
    @Part
    def obc(self):
        """
        Returns an instance of the OBC class.
        """
        return subsys.OBC(required_onboard_data_storage=self.required_onboard_data_storage*1.25E-7) # kbits to GB (GigaBytes)
    
    @Part
    def adcs(self):
        """
        Returns an instance of the ADCS class.
        """
        return subsys.ADCS(required_pointing_accuracy=self.parent.req_pointing_accuracy)
    
    @Part
    def structure(self):
        """
        Returns an instance of the Structure class.
        """
        return Structure()

    @Part
    def thermal(self):
        """
        Returns an instance of the Thermal class.
        """
        return subsys.Thermal(T_max_in_C=self.system_max_allowed_temperature, 
                              T_min_in_C=self.system_min_allowed_temperature,
                              _has_geometry=False)