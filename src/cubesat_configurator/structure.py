from parapy.core import *
from parapy.geom import *
from parapy.exchange.step import STEPReader

import pandas as pd
import numpy as np
import os
import pykep as pk
from cubesat_configurator import constants
import itertools
import math

class Structure(GeomBase):
    number_of_spacers = Input(5, doc="Number of spacers to be added to the stack")

    @number_of_spacers.validator
    def number_of_spacers(self, value):
        if value < 0:
            msg = ("Number of spacers cannot be negative.")
            return False, msg
        if value > 6:
            msg = ("Number of spacers should not exceed 6, to avoid very long simulation times.")
            return False, msg 
        return True

    def read_struct_from_csv(self):
        """Read subsystem data from CSV."""
        script_dir = os.path.dirname(__file__)
        relative_path = os.path.join('data', 'Structure.csv')
        obc_info_path = os.path.join(script_dir, relative_path)
        return pd.read_csv(obc_info_path)

    @Attribute
    def form_factor(self):
        "Calculate form factor for cubesat"
        obc_selection_list = self.parent.obc.obc_selection
        adcs_selection_list = self.parent.adcs.adcs_selection
        bat_selection_list = self.parent.power.battery_selection
        comm_selection_list = self.parent.communication.comm_selection
        total_height = obc_selection_list['Height'] + adcs_selection_list['Height'] + self.parent.payload.height + bat_selection_list['Height'] + comm_selection_list['Height']
        height_factor = total_height / 100
        
        if height_factor < 1:
            form_factor = 1
        elif height_factor < 1.5:
            form_factor = 1.5
        elif height_factor < 2:
            form_factor = 2
        elif height_factor < 3:
            form_factor = 3
        else:
            form_factor = "No available Cubesat sizes found"
        self.height = form_factor*100
        return form_factor

    @Attribute
    def _read_step_file(self):
        "Choose STEP File based on the form factor"
        form_factor = self.form_factor
        script_dir = os.path.dirname(__file__)
        
        # Map form_factor to corresponding STEP file name
        # corrected step files have compatible location
        if form_factor == 1:
            subsystem_file_name = "1U_corrected.step"
        elif form_factor == 1.5:
            subsystem_file_name = "1_5U_corrected.step"
        elif form_factor == 2:
            subsystem_file_name = "2U_corrected.step"
        elif form_factor == 3:
            subsystem_file_name = "3U_corrected.step"
        else:
            raise ValueError("No STEP file available for the calculated form factor.")
        
        relative_path = os.path.join('STEP_files', subsystem_file_name)
        struct_info_path = os.path.join(script_dir, relative_path)
        return struct_info_path
    

    @Part
    def structure_representation(self):
        "Display STEP File"
        return STEPReader(filename=self._read_step_file)
    
    @Attribute
    def structure(self):
        form_factor_req = self.form_factor
        struct = self.read_struct_from_csv()
        struct_selection = []

        for index, row in struct.iterrows():
            # Compare the required Form Factor value with the requirements from the CSV 
            if row['Form_Factor'] == form_factor_req:
                struct_selection.append({
                    'index': index,
                    'Form_Factor': row['Form_Factor'],
                    'Mass': row['Mass'],
                    'Cost': row['Cost']
                })
        if len(struct_selection) == 0:
            raise ValueError("No suitable component found based on the criteria.") 
        
        selected_structure = struct_selection[0]
        
        return selected_structure
    

    @Attribute
    def mass(self):
        return self.structure['Mass']
    
    @Attribute
    def cost(self):
        return self.structure['Cost']

    @Attribute
    def subsystem_data_for_stacking(self):
        """
        Returns a list of dictionaries with the height, mass and name of each subsystem.
        """
        # Subsystems data

        subsystems = []

        payload = self.parent.payload
        adcs = self.parent.adcs
        power = self.parent.power
        obc = self.parent.obc
        comms = self.parent.communication

        subsystems_input = [payload, adcs, power, obc, comms]

        for sub in subsystems_input:
            sub_data = {'name': sub.__class__.__name__, 'mass': sub.mass, 'height': sub.height, 'CoM_Location': None}
            subsystems.append(sub_data)

        # # for testing purposes
        # payload = {'name': 'Payload', 'mass': 300, 'height': 70, 'CoM_Location': None}
        # adcs = {'name': 'ADCS', 'mass': 500, 'height': 60, 'CoM_Location': None}
        # power = {'name': 'EPS', 'mass': 100, 'height': 50, 'CoM_Location': None}
        # obc = {'name': 'OBC', 'mass': 100, 'height': 30, 'CoM_Location': None}
        # comms = {'name': 'COMM', 'mass': 100, 'height': 30, 'CoM_Location': None}
        
        return subsystems
    
    @Attribute
    def optimal_stacking_order(self):
        """
        Returns the optimal stacking order of the subsystems based on the form factor of the satellite.
        """
        # find 'Payload' subsystem and fix it at the bottom of the stack
        fixed_at_bottom = next(sub for sub in self.subsystem_data_for_stacking if sub['name'] == 'Payload')
        
        optimal_stack = self._find_optimal_stacking_order(self.subsystem_data_for_stacking, fixed_at_bottom)
        return optimal_stack
    
    @Attribute
    def CoM_location(self):
        """
        Returns the center of mass of the satellite stack.
        """
        optimal_stack = self.optimal_stacking_order
        CoM = self.calculate_CoM_of_stack(optimal_stack)
        return CoM
    
    @Attribute
    def distance_CoM_to_geometric_center(self):
        """
        Returns the distance between the center of mass and the geometric center of the satellite stack.
        """
        total_height = 100*self.form_factor
        geometric_center = total_height / 2
        distance = abs(self.CoM_location - geometric_center)
        return distance

    
    def _find_optimal_stacking_order(self, subsystems, fixed_at_bottom=None):

        min_distance = float('inf') # Initialize minimum distance to infinity
        optimal_stack = None

        subsystems_list = subsystems.copy()

        # calculate leftover space for spacers
        space_for_spacers = 100*self.form_factor - sum(sub['height'] for sub in subsystems_list)
        # round down to the nearest integer
        num_spacers = self.number_of_spacers 
        spacer_size = space_for_spacers / num_spacers if num_spacers > 0 else 0 # mm
        print(f"Space for spacers: {space_for_spacers} mm")

        # remove the fixed subsystem from the list 
        subsystems_list.remove(fixed_at_bottom)

        
        # append spacers to the end of the subsystems list
        for i in range(num_spacers):
            subsystems_list.append({'name': f'Spacer_{i}', 'mass': 0, 'height': spacer_size, 'CoM_Location': None})

        print('\nstart permutating...')

        all_permutations = itertools.permutations(subsystems_list)
        
        
        i = 0
        # Iterate through all permutations
        for perm in all_permutations:
            i += 1

            # add fixed_at_bottom to the beginning of the permutation
            perm = [fixed_at_bottom] + list(perm)
            
            current_height = 0
            # Iterate through all subsystems in the permutation
            for sub in perm:
                sub['CoM_Location'] = current_height + sub['height'] / 2
                current_height += sub['height']

            # sort subsystems by CoM_Location
            # perm_sorted = sorted(perm, key=lambda x: x['CoM_Location'])
            perm_sorted = sorted(perm, key=lambda x: x['CoM_Location'], reverse=True)

            total_height = 100*self.form_factor # remove the last distance added
            # assert total_height == 100*self.form_factor # check if the total height is equal to the form factor

            geometric_center = total_height / 2
            CoM = self.calculate_CoM_of_stack(perm)
            distance = abs(CoM - geometric_center)
            
            if distance < min_distance:
                min_distance = distance
                optimal_stack = perm_sorted
                self._display_stacking(perm_sorted, total_height)
        
            # stop when distance of Center of Mass to Geometric Center is less than 1 mm
            if abs(min_distance) <= 1:
                break

        # calculate number of permutations
        N_perm = math.factorial(len(subsystems_list)) 
        
        # print the number of permutations
        print(f"Number of permutations: {N_perm}\n"
              f"\nNumber of iterations: {i}")
        print(f"Number of considered permutations: {len(list(all_permutations))}")
        # return last item of the list, which is the optimal stacking order
        return optimal_stack

    def calculate_CoM_of_stack(self, stack):

        total_mass = sum(sub['mass'] for sub in stack)
        weighted_sum = 0

        for sub in stack:
            sub_CoM = sub['CoM_Location'] 
            weighted_sum += sub['mass'] * sub_CoM

        CoM = weighted_sum / total_mass

        return CoM
    
    
    def _display_stacking(self, stack, total_height):
        # print stacking order, showing the subsystem name and CoM height; the top one first
        for sub in (stack):
            print(f"{sub['name']} (CoM height: {sub['CoM_Location']}; height: {sub['height']}; mass: {sub['mass']})")
        
        # print the total height of the stack 
        print(f"\nTotal height: {total_height}")
        # print the geometric center of the stack
        geometric_center = total_height / 2
        print(f"Geometric center: {geometric_center}")
        # print the calculated CoM of the stack
        CoM_total = self.calculate_CoM_of_stack(stack)
        print(f"Calculated CoM of the stack: {CoM_total}")
        # print the minimum distance between the CoM and the geometric center
        CoM_distance = CoM_total - geometric_center
        print(f"Minimum distance from CoM to geometric center: {CoM_distance}")
        print('-----------------------------------\n')
