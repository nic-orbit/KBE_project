import pykep as pk
import paseos
from paseos import ActorBuilder, SpacecraftActor, GroundstationActor
import numpy as np
import os
import pandas as pd
from parapy.core.sequence import Sequence


def keplerian_to_eci(a, e, i, RAAN, argument_of_periapsis, true_anomaly):
    # Gravitational parameter for Earth (km^3/s^2)
    mu = 398600.4418
    
    # Convert angles from degrees to radians
    i = np.radians(i)
    RAAN = np.radians(RAAN)
    argument_of_periapsis = np.radians(argument_of_periapsis)
    true_anomaly = np.radians(true_anomaly)
    
    # Calculate the distance r
    r = a * (1 - e**2) / (1 + e * np.cos(true_anomaly))
    
    # Position in the orbital plane
    r_orb = np.array([r * np.cos(true_anomaly), r * np.sin(true_anomaly), 0.0])
    
    # Orbital parameter p
    p = a * (1 - e**2)
    
    # Velocity in the orbital plane
    v_r = np.sqrt(mu / p) * e * np.sin(true_anomaly)
    v_theta = np.sqrt(mu / p) * (1 + e * np.cos(true_anomaly))
    v_orb = np.array([v_r * np.cos(true_anomaly) - v_theta * np.sin(true_anomaly),
                      v_r * np.sin(true_anomaly) + v_theta * np.cos(true_anomaly),
                      0.0])
    
    # Rotation matrices
    R3_RAAN = np.array([[np.cos(RAAN), np.sin(RAAN), 0],
                        [-np.sin(RAAN), np.cos(RAAN), 0],
                        [0, 0, 1]])
    
    R1_i = np.array([[1, 0, 0],
                     [0, np.cos(i), np.sin(i)],
                     [0, -np.sin(i), np.cos(i)]])
    
    R3_argument_of_periapsis = np.array([[np.cos(argument_of_periapsis), np.sin(argument_of_periapsis), 0],
                                         [-np.sin(argument_of_periapsis), np.cos(argument_of_periapsis), 0],
                                         [0, 0, 1]])
    
    # Combined rotation matrix
    Q = R3_RAAN @ R1_i @ R3_argument_of_periapsis
    
    # Transform position and velocity to ECI frame
    r_eci = Q @ r_orb
    v_eci = Q @ v_orb
    
    return r_eci, v_eci


class GroundContactInfo():
    def __init__(self, spacecraft: SpacecraftActor, station: GroundstationActor):
        self.first_contact = True
        self.lost_contact = False
        self.stored_first_contact_time = None
        self.comm_window_list = []
        self.spacecraft = spacecraft
        self.station = station

    def test(self):
        print("Hello World")


    def has_link_to_ground_station(self):
        """
        Checks if the actor is in contact with any of the ground stations.

        Parameters:
        actor: The satellite or space object being monitored.
        ground_stations: A list of ground station objects.

        Returns:
        bool: True if contact is established with any ground station, False otherwise.
        """
        time = self.spacecraft.local_time
        
        # Check contact with each station
        contact = self.spacecraft.is_in_line_of_sight(self.station, time)  # bool
        if contact:
            if self.first_contact:
                self.first_contact = False
                self.lost_contact = False
                self.stored_first_contact_time = time
                print(f"--- CONTACT with {self.station} at: {time}")
            return True  # Returns True if contact is established with any ground station

        elif not self.first_contact:
            self.lost_contact = True

            comm_window = round(
                (time.mjd2000 - self.stored_first_contact_time.mjd2000) * pk.DAY2SEC  # pk.DAY2SEC = 86400
            )
            self.comm_window_list.append(comm_window)

            print(f"--- CONTACT LOST with {self.station} at: {time}")
            print(f"--- Communication window: {comm_window} [s]")
            print("-----------------------------------------------------")

        self.first_contact = True
        return False  # Returns False if contact is not established with any ground station


    def total_contact_time(self):
        """
        Calculates the total contact time from the communication windows.

        Returns:
        float: Total contact time in seconds.
        """
        return sum(self.comm_window_list)
    

def set_ground_station_old(epoch, simulation, index_list:list):
    """Give indexes of groundstations in sheet and add them to the sim"""
    stations = read_ground_stations_from_csv()
    stations_list = []

    for i in index_list:
        # check that index is within the list
        if 0 <= i <= stations.last_valid_index():
            lat = stations.loc[i, "Lat"]
            lon = stations.loc[i, "Lon"]
            company = stations.loc[i, "Company"]
            location = stations.loc[i, "Location"]
            gs_name = f"gs_actor_{i}"
            locals()[gs_name] = ActorBuilder.get_actor_scaffold(
                name=f"gs_{i} ({location})", actor_type=GroundstationActor, epoch=epoch
            )

            ActorBuilder.set_ground_station_location(
                locals()[gs_name],
                latitude=lat,
                longitude=lon,
                elevation=90,
                minimum_altitude_angle=5,
            )
            # add the gs to simulation
            simulation.add_known_actor(locals()[gs_name])

            stations_list.append(locals()[gs_name])

            print(f"Added '{company}' groundstation {i} located at {location}")
        else:
            print(f"No ground station with index {i} in data.")

    return stations_list


def set_ground_station(epoch, simulation, ground_stations:Sequence):
    """Give indexes of groundstations in sheet and add them to the sim"""
    stations_list = []

    for station in ground_stations:
        locals()[station.name] = ActorBuilder.get_actor_scaffold(
            name=station.name, actor_type=GroundstationActor, epoch=epoch
        )

        ActorBuilder.set_ground_station_location(
            locals()[station.name],
            latitude=station.latitude,
            longitude=station.longitude,
            elevation=station.elevation,
            minimum_altitude_angle=5,
        )
        # add the gs to simulation
        simulation.add_known_actor(locals()[station.name])

        stations_list.append(locals()[station.name])

    return stations_list


def read_ground_stations_from_csv():
    # Get the current directory of the script
    script_dir = os.path.dirname(__file__)
    relative_path = os.path.join('data', 'ground_stations.csv')

    # Construct the full relative file path
    gs_info_path = os.path.join(script_dir, relative_path)

    all_gs_import = pd.read_csv(gs_info_path)
    return all_gs_import


if __name__ == '__main__':
    # import progressbar
    # from time import sleep

    # bar = progressbar.ProgressBar(maxval=20, \
    #     widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
    # bar.start()
    # for i in range(20):
    #     bar.update(i+1)
    #     sleep(0.1)
        
    # bar.finish()
    t0 = pk.epoch_from_string("2024-august-01 08:00:00")
    print(t0.mjd2000)