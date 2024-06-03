import pykep as pk
import paseos
from paseos import ActorBuilder, SpacecraftActor, GroundstationActor
import numpy as np


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


class GroundContactInfo:
    def __init__(self):
        self.first_contact = True
        self.lost_contact = False
        self.stored_first_contact_time = None
        self.comm_window_list = []

    def test(self):
        print("Hello World")


    def has_link_to_ground(self, actor:SpacecraftActor, ground_station:GroundstationActor):
        """
        Checks if actor is in contact with the ground.

        Parameters:
        actor: The satellite or space object being monitored.
        ground_station: A ground station object.

        Returns:
        bool: True if contact is established with the ground station, False otherwise.
        """
        time = actor.local_time

        contact = actor.is_in_line_of_sight(ground_station, time)  # bool

        return contact


    def has_link_to_ground_station(self, actor: SpacecraftActor, station: GroundstationActor):
        """
        Checks if the actor is in contact with any of the ground stations.

        Parameters:
        actor: The satellite or space object being monitored.
        ground_stations: A list of ground station objects.

        Returns:
        bool: True if contact is established with any ground station, False otherwise.
        """
        time = actor.local_time
        
        # Check contact with each station
        contact = actor.is_in_line_of_sight(station, time)  # bool
        if contact:
            if self.first_contact:
                self.first_contact = False
                self.lost_contact = False
                self.stored_first_contact_time = time
                print(f"--- CONTACT with {station} at: {time}")
            return True  # Returns True if contact is established with any ground station

        elif not self.first_contact:
            self.lost_contact = True

            comm_window = round(
                (time.mjd2000 - self.stored_first_contact_time.mjd2000) * pk.DAY2SEC  # pk.DAY2SEC = 86400
            )
            self.comm_window_list.append(comm_window)

            print(f"--- CONTACT LOST with {station} at: {time}")
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