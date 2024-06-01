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



# Define an actor of type SpacecraftActor of name mySat
sat_actor = ActorBuilder.get_actor_scaffold(name="myCubeSat",
                                       actor_type=SpacecraftActor,
                                       epoch=pk.epoch(0))

# Define the central body as Earth by using pykep APIs.
earth = pk.planet.jpl_lp("earth")

# Let's set the orbit of sat_actor.
ActorBuilder.set_orbit(actor=sat_actor,
                       position=[10000000, 0, 0],
                       velocity=[0, 8000.0, 0],
                       epoch=pk.epoch(0), central_body=earth)