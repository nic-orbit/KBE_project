from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo, IsInstance, Range
import subsystems as subsys
import subsystem as ac
import numpy as np
import pykep as pk
import yaml
import os
from pprint import pprint
import paseos_parser as pp
import paseos
from paseos import ActorBuilder, SpacecraftActor, GroundstationActor
import constants
from orbit import Orbit




class CubeSat(GeomBase):
    cost_factor = Input(0, validator=Range(0, 1))
    mass_factor = Input(0, validator=Range(0, 1))
    power_factor = Input(0, validator=Range(0, 1))

    @Attribute
    def total_mass(self): # Do we need overall mass and power using a margin first?
        """
        Calculate the total mass of the CubeSat based on the mass of the subsystems (bottom-up approach) for final reporting. 
        """
        mass = 0
        for child in self.children:
            if isinstance(child, ac.Subsystem):
                mass += child.mass
        return mass

    @Attribute
    def total_power_consumption(self):
        """
        Calculate the total power consumption of the CubeSat based on the average power consumption of the subsystems (bottom-up approach) for final reporting. 
        """
        power = 0
        for child in self.children:
            if isinstance(child, ac.Subsystem):
                power += child.power
        return power

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
    
    #to be deleted! - Try to implement separately for each subsystem
    @Attribute
    def subsystem_dict(self):
        # Get the current directory of the script
        script_dir = os.path.dirname(__file__)
        relative_path = os.path.join('..', 'Subsystem_Library')

        # Construct the full relative file path to subsystems library
        file_path_trunk = os.path.join(script_dir, relative_path)

        subsystems = {"OBC": "OBC.yaml", "EPS": "EPS.yaml", "COMM": "COMM.yaml"}

        for key, value in subsystems.items():
            file_path = os.path.join(file_path_trunk, value)

            # Check if the file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"The file '{file_path}' does not exist.")

            with open(file_path) as f:
                try:
                    subsystems[key] = yaml.safe_load(f)
                except yaml.YAMLError as exc:
                    print(exc)

        pprint(subsystems)
        return subsystems
    
    
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
        # number of orbits to simulate = 1 day / orbital period = Number of orbits in a day
        orbits_to_simulate = np.ceil(pk.DAY2SEC / T)
        # number of runs = number of seconds in a day / simulation timestep
        runs = int(pk.DAY2SEC / dt)
        # print(f"runs: {runs}")

        if plotting:
            plotter = paseos.plot(sim, paseos.PlotType.SpacePlot)
        
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
            "simulation_start": t0,
            "simulation_end": sat_actor.local_time,
            "simulation_duration": round((sat_actor.local_time.mjd2000 - t0.mjd2000)*pk.DAY2SEC,1),
            "eclipse_time": eclipse_time,
            "comm_window_per_day": total_comm_window,
            "comm_window_per_orbit": total_comm_window / orbits_to_simulate,
            "comm_window_fraction": total_comm_window / (orbits_to_simulate * T),
            "shortest_comm_window": min(comm_windows),
            "average_comm_window": total_comm_window / len(comm_windows),
            "longest_comm_window": max(comm_windows),
            "number_of_contacts_per_day": len(comm_windows)
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
        
        return simulation_results


    @Part
    def payload(self):
        """
        Returns an instance of the Payload class.
        """
        return subsys.Payload(instrument_min_operating_temp=-10, # deg C
                              instrument_max_operating_temp=50, # deg C
                              instrument_focal_length=40, # mm
                              instrument_pixel_size=7,  # µm - Typical values for industrial cameras range from 1.5 to 15 µm ( bigger --> better SNR, but larger (worse) GSD )
                              instrument_power_consumption=10, # W
                              instrument_mass=0.5, # kg
                              instrument_height=50, # mm
                              instrument_width=100, # mm
                              instrument_length=100, # mm
                              instrument_cost=10000, # USD
                              instrument_images_per_day=1, #number
                              instrument_pixel_resolution=[1280, 720], #range to be defined or we split this into w and h, consider list
                              instrument_bit_depth=8 #range to be defined (1-24) Check gs for inputvalidator
                              )
    
    @Part
    def communication(self):
        """
        Returns an instance of the COMM class.
        """
        return subsys.COMM()
    
    @Part
    def power(self):
        """
        Returns an instance of the EPS class.
        """
        return subsys.EPS()
    
    @Part
    def obc(self):
        """
        Returns an instance of the OBC class.
        """
        return subsys.OBC()
    
    @Part
    def adcs(self):
        """
        Returns an instance of the ADCS class.
        """
        return subsys.ADCS()
    
    @Part
    def structure(self):
        """
        Returns an instance of the Structure class.
        """
        return subsys.Structure()

    @Part
    def thermal(self):
        """
        Returns an instance of the Thermal class.
        """
        return subsys.Thermal()