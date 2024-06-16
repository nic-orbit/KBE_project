import numpy as np
import scipy as sp
import pandas as pd
from scipy.optimize import fsolve
import math    
from cubesat_configurator.constants import Thermal as T

pd.options.mode.copy_on_write = True # to avoid SettingWithCopyWarning


boltzmann_constant = T.boltzmann_constant
earth_avg_temp = T.earth_avg_temp
earth_radius = T.earth_radius
earth_albedo = T.earth_albedo
e_Earth = T.e_Earth
S = T.S


def arcoth(x):
    if abs(x) <= 1:
        raise ValueError("arcoth(x) is defined for |x| > 1")
    return 0.5 * np.log((x + 1) / (x - 1))

def calc_tau(T_eq, m, c_p, epsilon, sigma, A_SC):
    return ( m*c_p ) / ( 4* epsilon * sigma * A_SC * T_eq**3 )

def calc_C(T_0, T_eq):
    return 2 * ( arcoth(T_0 / T_eq) + np.arctan(T_0 / T_eq) )

def f(T, T_eq, C, t, tau):
    x = T / T_eq
    if x < 1:
        x = 1.001
    return 2 * ( arcoth(x) + np.arctan(x) ) - (t/tau + C)

def exact_transient_solution_cooling(T_eq:float, T_0:float, m:float, c_p:float, epsilon:float, A_Surface:float, t_eclipse:float):
    msg = f"Equilibrium temperature must be smaller than initial temperature. Got T_eq = {T_eq} and T_0 = {T_0}"
    assert T_eq / T_0 < 1, msg

    tau = calc_tau(T_eq, m, c_p, epsilon, boltzmann_constant, A_Surface)  # calculate time constant
    C = calc_C(T_0, T_eq)  # calculate integration constant from initial conditions
    T = fsolve(f, T_0, args=(T_eq, C, t_eclipse, tau))
    return T[0]

def first_order_transient_solution(Q_in, T_0, m, c_p, epsilon, A_Surface, t_eclipse, n_steps):
    dt = t_eclipse / n_steps
    T_old = T_0

    for i in range(n_steps):
        T_new = T_old + (Q_in - epsilon * A_Surface * boltzmann_constant * T_old**4) / (m * c_p) * dt
        T_old = T_new

    return T_new

def calculate_equilibrium_hot_temp(P_heaters, Q_internal, absorbtivity, emissivity, periapsis, apoapsis, max_cross_section, min_cross_section, surface_area):
    """
    Calculate equilibrium temperatures for hot and cold cases
    Hot case: max cross sectional area, shortest distance to earth (periapsis) & no heater power
    Cold case: min cross sectional area & longest distance to earth (apoapsis) & heater power
    """
    # hot case -> max Cross sectional area & shortest distance to earth
    Q_S_hot = absorbtivity * S * max_cross_section  # W
    Q_IR_hot = e_Earth * boltzmann_constant * earth_avg_temp**4 * ( earth_radius**2 ) / ( periapsis**2 ) * absorbtivity * max_cross_section  # W
    Q_A_hot = earth_albedo * S * ( earth_radius**2 ) / (2 * periapsis**2 ) * absorbtivity * max_cross_section  # W

    Q_in_hot = Q_S_hot + Q_IR_hot + Q_A_hot + Q_internal  # W

    # calculate equilibrium temperatures
    T_hot_eq = thermal_equilibrium_temp(Q_in_hot, emissivity, surface_area)  # K

    return T_hot_eq

def calculate_equilibrium_cold_temp(P_heaters, Q_internal, absorbtivity, emissivity, periapsis, apoapsis, max_cross_section, min_cross_section, surface_area):
    """
    Calculate equilibrium temperatures for hot and cold cases
    Hot case: max cross sectional area, shortest distance to earth (periapsis) & no heater power
    Cold case: min cross sectional area & longest distance to earth (apoapsis) & heater power
    """
    # cold case -> min Cross sectional area & longest distance to earth
    Q_IR_cold = e_Earth * boltzmann_constant * earth_avg_temp**4 * ( earth_radius**2 ) / ( apoapsis**2 ) * absorbtivity * min_cross_section  # W

    Q_in_cold = Q_IR_cold + Q_internal + P_heaters # W

    # calculate equilibrium temperatures
    T_cold_eq = thermal_equilibrium_temp(Q_in_cold, emissivity, surface_area)  # K

    return T_cold_eq

def thermal_equilibrium_temp(Q_in, emissivity, surface_area):
    """
    Calculate the equilibrium temperature of a satellite in orbit.
    Parameters:
    Q_internal: The in coming heat in W.
    emissivity: The emissivity of the satellite surface.
    surface_area: The surface area of the satellite in m^2.
    Returns:
    The equilibrium temperature of the satellite in K.
    """
    T_eq = (Q_in / (emissivity * boltzmann_constant * surface_area))**(1/4)  # K
    return T_eq

def select_coating(form_factor:float, coatings_df:pd.DataFrame) -> dict:
    """
    Select the best coating based on the form factor and the margin.

    Parameters:
    form_factor: The form factor of the satellite. Can be 1, 1.5, 2, or 3.
    coatings_df: A pandas dataframe containing the coating data.
    """
    # filter out coatings that are not feasible for the given form factor in the hot case
    feasible_hot = coatings_df[(coatings_df[f'Hot Margin {form_factor}U'] >= 0)]
    # make sure that there is a feasible coating for the hot case
    assert not feasible_hot.empty, "No feasible coatings found for the given form factor for the hot case."
    # from feasible hot filter out coatings that are not feasible for the given form factor in the cold case
    feasible_cold = feasible_hot[(feasible_hot[f'Cold Margin {form_factor}U'] >= 0)]
    if feasible_cold.empty:
        # if there are no feasible coatings for the cold case, select the coating with the highest cold margin
        selected_coating_df = feasible_hot.loc[[feasible_hot[f'Cold Margin {form_factor}U'].idxmax()]]
    else:
        # If there are feasible coatings for the cold case, select the coating that has the most equal hot and cold margin
        feasible_cold['margin_diff'] = (feasible_cold[f'Hot Margin {form_factor}U'] - feasible_cold[f'Cold Margin {form_factor}U']).abs()
        selected_coating_df = feasible_cold.loc[[feasible_cold['margin_diff'].idxmin()]]
    
    selected_coating = {
        'Coating': selected_coating_df['Coating'].values[0],
        # 'Type': selected_coating_df['Type'].values[0], 
        'Absorptivity': selected_coating_df['Absorptivity'].values[0],
        'Emissivity': selected_coating_df['Emissivity'].values[0],
        'Hot Case': selected_coating_df[f'Hot Case {form_factor}U'].values[0],
        'Cold Case': selected_coating_df[f'Cold Case {form_factor}U'].values[0],
        'Hot Margin': selected_coating_df[f'Hot Margin {form_factor}U'].values[0],
        'Cold Margin': selected_coating_df[f'Cold Margin {form_factor}U'].values[0]}
    # return the selected coating as a dictionary
    return selected_coating


