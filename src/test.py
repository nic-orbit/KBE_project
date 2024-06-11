import numpy as np
import pandas as pd
import scipy as sp
from scipy.optimize import fsolve
from cubesat_configurator import thermal_helpers as th
from pprint import pprint

# solar array type
sa_type = 'Body-mounted'    # 'Body-mounted' or 'Deployable'
form_factor = 1  # 1, 2 or 3

earth_radius = 6371e3  # m
periapsis = earth_radius + 500e3  # m
apoapsis = earth_radius + 500e3  # m

sat_mass = 2  # kg mass of satellite
sat_cp = 900  # J/kgK specific heat capacity of aluminum

T_max_in_C = 50  # deg C
T_min_in_C = 13  # K
T_margin = 5  # K

T_max = T_max_in_C + 273.15 - T_margin # K
T_min = T_min_in_C + 273.15 + T_margin # K

t_eclipse = 940  # s

############
U = np.array([1, 2, 3], dtype=float)  # form factors

# max cross sectional area for all u in U
A_C_max = np.sqrt(2) * U * 0.01 # m^2

# min cross sectional area for all u in U, same for all form factors
A_C_min = 0.01 # m^2

# surface area for all u in U
A_S = (2+4*U) * 0.01 # m^2

# import solar cell coatings from xlsx file
path_to_sa_coatings = r'C:\Users\nicol\Documents\000SAFE\Git\KBE_project\src\cubesat_configurator\data\thermal_coatings\coatings_NASA_solarcells.csv'
path_to_body_coatings = r'C:\Users\nicol\Documents\000SAFE\Git\KBE_project\src\cubesat_configurator\data\thermal_coatings\coatings_SMAD_no_dupl.csv'

if sa_type == 'Body-mounted':
    coatings_df = pd.read_csv(path_to_sa_coatings)
elif sa_type == 'Deployable':
    coatings_df = pd.read_csv(path_to_body_coatings)
else:
    raise ValueError('Invalid solar array type. Choose "Body-mounted" or "Deployable".')

# set internal heater power to 0 for now
P_heaters =  0 # W
Q_internal = 3  # W

####### loop coatings
for i in range(0, len(coatings_df)):
    ####### loop form factors
    for u in range(0, len(U)):
        T_hot_eq = th.calculate_equilibrium_hot_temp(P_heaters, 
                                                    Q_internal,
                                                    coatings_df.loc[i, 'Absorptivity'], 
                                                    coatings_df.loc[i, 'Emissivity'], 
                                                    periapsis, 
                                                    apoapsis, 
                                                    A_C_max[u], 
                                                    A_C_min, 
                                                    A_S[u])  # K
        T_cold_eq = th.calculate_equilibrium_cold_temp(P_heaters, 
                                                    Q_internal,
                                                    coatings_df.loc[i, 'Absorptivity'], 
                                                    coatings_df.loc[i, 'Emissivity'], 
                                                    periapsis, 
                                                    apoapsis, 
                                                    A_C_max[u], 
                                                    A_C_min, 
                                                    A_S[u])  # K

        # final temperatures for design
        T_hot = T_hot_eq
        # print(f"for test {T_cold_eq} < {T_hot}")
        T_cold = th.exact_transient_solution_cooling(T_cold_eq, T_hot, sat_mass, sat_cp, coatings_df.loc[i, 'Emissivity'], A_S[u], t_eclipse)  # K

        coatings_df.loc[i, f'Hot Case {u+1}U'] = T_hot  # K
        coatings_df.loc[i, f'Cold Case {u+1}U'] = T_cold  # K
        coatings_df.loc[i, f'Hot Margin {u+1}U'] = T_max - T_hot  # K
        coatings_df.loc[i, f'Cold Margin {u+1}U'] = T_cold - T_min  # K

# print coatings_df only the margins
print(coatings_df[['Coating' , 'Hot Margin 1U', 'Cold Margin 1U','Hot Margin 2U', 'Cold Margin 2U', 'Hot Margin 3U',  'Cold Margin 3U']])
selected_coating = th.select_coating(3, coatings_df)

print(f"Max temp: {T_max} K = {T_max - 273.15} °C")
print(f"Min temp: {T_min} K = {T_min - 273.15} °C")

pprint(selected_coating)

T_hot = selected_coating['Hot Case']
T_cold = selected_coating['Cold Case']

def iterate_heater_power(T_initial, T_target, u):
    T = T_initial
    P = 0
    while T < T_target:
        T_hot_eq = th.calculate_equilibrium_hot_temp(P, 
                                                    Q_internal,
                                                    selected_coating['Absorptivity'], 
                                                    selected_coating['Emissivity'], 
                                                    periapsis, 
                                                    apoapsis, 
                                                    A_C_max[u], 
                                                    A_C_min, 
                                                    A_S[u])  # K
        T_cold_eq = th.calculate_equilibrium_cold_temp(P, 
                                                    Q_internal,
                                                    selected_coating['Absorptivity'], 
                                                    selected_coating['Emissivity'], 
                                                    periapsis, 
                                                    apoapsis, 
                                                    A_C_max[u], 
                                                    A_C_min, 
                                                    A_S[u])  # K
        T_hot = T_hot_eq
        # print(f"for test {T_cold_eq} < {T_hot}")
        T = th.exact_transient_solution_cooling(T_cold_eq, T_hot, sat_mass, sat_cp, selected_coating['Emissivity'], A_S[u], t_eclipse)  # K
        P += 0.001  # increase heater power by 1mW

    return round(P,3)

u = 2

P_heater_iter = iterate_heater_power(T_cold, T_min, u)


def test_heater_power(P, selected_coating):
    T_hot_eq = th.calculate_equilibrium_hot_temp(P, 
                                                Q_internal,
                                                selected_coating['Absorptivity'], 
                                                selected_coating['Emissivity'], 
                                                periapsis, 
                                                apoapsis, 
                                                A_C_max[u], 
                                                A_C_min, 
                                                A_S[u])  # K
    T_cold_eq = th.calculate_equilibrium_cold_temp(P, 
                                                Q_internal,
                                                selected_coating['Absorptivity'], 
                                                selected_coating['Emissivity'], 
                                                periapsis, 
                                                apoapsis, 
                                                A_C_max[u], 
                                                A_C_min, 
                                                A_S[u])  # K
    T_hot = T_hot_eq
    # print(f"for test {T_cold_eq} < {T_hot}")
    T_cold_new = th.exact_transient_solution_cooling(T_cold_eq, T_hot, sat_mass, sat_cp, selected_coating['Emissivity'], A_S[u], t_eclipse)  # K

    assert T_cold_new >= T_min, f"Temperature too low: {T_cold_new} K < {T_min} K"

    selected_coating['Heater Power'] = P # W
    selected_coating['Cold Case with Heater'] = T_cold_new  # K
    selected_coating['Cold Margin with Heater'] = T_cold_new - T_min  # K

    print(f" new heater power:  {P} W")
    print(f" new Cold Case temperature:  {T_cold_new} K = {T_cold_new - 273.15} °C")
    print(f" new Cold Case temperature margin:  {T_cold_new - T_min} K")

    return selected_coating


final_selection = test_heater_power(P_heater_iter, selected_coating)

print("\nFinal selection:")
pprint(final_selection)