from parapy.core import *
from parapy.geom import *
from parapy.core.validate import OneOf, LessThan, GreaterThan, GreaterThanOrEqualTo, IsInstance
import abstract_classes as ac
from concrete_classes import subsystems as subsys
import numpy as np
import pykep as pk
import yaml
import os
from pprint import pprint
import paseos_parser as pp
import paseos
from paseos import ActorBuilder, SpacecraftActor, GroundstationActor
import constants


class Mission(GeomBase): 
    #mission requirements
    mission_lifetime = Input(doc="Mission Lifetime in months") # months
    reqiured_GSD = Input() # m
    orbit_type = Input() # SSO, Polar, Equatorial, custom
    custom_inclination = Input(0) # deg TBD if we use this!
    # Ground Stations selection
    ground_station_indeces = Input(validator=IsInstance(list))
    #system requirements
    req_pointing_accuracy = Input(validator= GreaterThan(0)) # deg
    #instrument requirements
    instrument_min_operating_temp = Input() # deg C
    instrument_max_operating_temp = Input() # deg C
    #instrument characteristics
    instrument_data_rate = Input() # kbps
    instrument_focal_length = Input() # mm
    instrument_pixel_size = Input() # µm
    instrument_power_consumption = Input() # W
    instrument_mass = Input() # kg
    instrument_height = Input() # mm
    instrument_width = Input() # mm
    instrument_length = Input() # mm

    @Attribute
    def ground_station_dataframe(self):
        stations = pp.read_ground_stations_from_csv()
        stations_list = []

        for i in self.ground_station_indeces:
            # check that index is within the list
            if 0 <= i <= stations.last_valid_index():
                lat = stations.loc[i, "Lat"]
                lon = stations.loc[i, "Lon"]
                company = stations.loc[i, "Company"]
                location = stations.loc[i, "Location"]
                gs_name = f"gs_actor_{i}"
                stations_list.append(stations.loc[i])
                print(f"Added '{company}' groundstation {i} located at {location}")
            else:
                print(f"No ground station with index {i} in data.")
        return stations_list

    @Attribute
    def number_of_ground_stations(self):
        return len(self.ground_station_indeces)
    
    @Attribute
    def orbit_inclination(self):
        inc_SSO = np.round(0.0087033*self.max_orbit_altitude+90.2442419, 2) # deg, derived from linear regression of SSO altitudes and inclinations from wikipedia
        return 90 if self.orbit_type == "Polar" else inc_SSO if self.orbit_type == "SSO" else 0 if self.orbit_type == "Equatorial" else self.custom_inclination
    
    
    @Attribute
    def max_orbit_altitude(self):
        """
        Calculate the maximum orbit altitude based on the required ground sample distance (GSD) and the instrument
        characteristics.
        """
        h = (self.reqiured_GSD / (self.instrument_pixel_size * 10**-6) ) * self.instrument_focal_length * 10**-6  # km
        return h

    @Part
    def cubesat(self):
        return CubeSat(orbit_altitude=self.max_orbit_altitude)
    
    @Part
    def groundstation(self):
        return GroundStation(quantify=self.number_of_ground_stations,
                             latitude=self.ground_station_dataframe[child.index]['Lat'],
                             longitude=self.ground_station_dataframe[child.index]['Lon'],
                             elevation=self.ground_station_dataframe[child.index]['Elevation'],
                             location=self.ground_station_dataframe[child.index]['Location'],
                             number=self.ground_station_dataframe[child.index]['Number']
                             )


class CubeSat(GeomBase):
    orbit_altitude = Input() # km

    @Attribute
    def system_data_rate(self):
        return self.parent.instrument_data_rate*1.05 # assume 5% of additional bus data rate
    
    @Attribute
    def min_downlink_data_rate(self):
        return self.system_data_rate/(self.simulate_first_orbit["comm_window_fraction"])

    @Attribute
    def orbit(self):
        return Orbit(altitude=self.orbit_altitude,
                inclination=self.parent.orbit_inclination)
    
    @Attribute
    def mass(self):
        mass = 0
        for child in self.children:
            if isinstance(child, ac.Subsystem):
                mass += child.mass
        return mass

    @Attribute
    def power_consumption(self):
        power = 0
        for child in self.children:
            if isinstance(child, ac.Subsystem):
                power += child.power
        return power
    
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
        plotting = True
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
        return subsys.Payload(width=self.parent.instrument_width,
                       height=self.parent.instrument_height,
                       length=self.parent.instrument_length,
                       mass=self.parent.instrument_mass,
                       power=self.parent.instrument_power_consumption
                       )
    
    @Part
    def communication(self):
        return subsys.COMM()
    
    @Part
    def power(self):
        return subsys.EPS()
    
    @Part
    def obc(self):
        return subsys.OBC()
    

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


class Orbit(Base):
    altitude = Input() # km
    inclination = Input() # deg
    eccentricity = Input(0) # dimensionless
    RAAN = Input(0) # deg
    argument_of_periapsis = Input(0) # deg
    true_anomaly = Input(0) # deg

    @Attribute
    def apoapsis(self):
        return (self.altitude*1000 + pk.EARTH_RADIUS)*(1+self.eccentricity) # in m

    @Attribute
    def periapsis(self):
        return (self.altitude*1000 + pk.EARTH_RADIUS)*(1-self.eccentricity) # in m
    
    @Attribute
    def period(self):
        return 2 * np.pi * np.sqrt(self.semi_major_axis**3 / pk.MU_EARTH) # in s
    
    @Attribute
    def semi_major_axis(self):
        return 0.5*(self.apoapsis+self.periapsis) # in m
    
    @Attribute
    def position_vector(self):
        """
        Convert the Keplerian elements to a position vector in the ECI frame for this orbit in meters.
        Returns:    
            r_eci: np.array
                Position vector in the ECI frame
        """        
        # convert km in m
        r_eci, v_eci = pk.par2ic([self.semi_major_axis, self.eccentricity, self.inclination, self.RAAN, self.argument_of_periapsis, self.true_anomaly], pk.MU_EARTH)
        return r_eci
    
    @Attribute
    def velocity_vector(self):
        """
        Convert the Keplerian elements to a velocity vector in the ECI frame for this orbit in meters per second.
        Returns:    
            v_eci: np.array
                Velocity vector in the ECI frame
        """     
        # convert km in m
        r_eci, v_eci = pk.par2ic([self.semi_major_axis, self.eccentricity, self.inclination, self.RAAN, self.argument_of_periapsis, self.true_anomaly], pk.MU_EARTH)
        return v_eci
    
    def __str__(self):
        return ("------ Orbit ------  \n"
                # print keplerian elements
                f"semi-major axis: {self.semi_major_axis} m\n"
                f"inclination: {self.inclination} deg\n"
                f"eccentricity: {self.eccentricity}\n"
                f"RAAN: {self.RAAN} deg\n"
                f"argument of periapsis: {self.argument_of_periapsis} deg\n"
                f"true anomaly: {self.true_anomaly} deg\n"
                #print orbital period
                f"orbital period: {self.period} s \n"
                f"position vector: {self.position_vector} \n"
                f"velocity vector: {self.velocity_vector} \n"
                "-------------------\n"
        )