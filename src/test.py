import itertools
from parapy.core import *
import parapy
from cubesat_configurator import subsystem as ac
from parapy.gui import display
from pprint import pprint
import math


class Structure(ac.Subsystem):
    form_factor = Input(1.5)
    number_of_spacers = Input(6, validator=LessThan(0))

    @Attribute
    def subsystem_data_for_stacking(self):
        """
        Returns a list of dictionaries with the height, mass and name of each subsystem.
        """
        # Subsystems data
        payload = {'name': 'Payload', 'mass': 500, 'height': 50, 'CoM_Location': None}
        adcs = {'name': 'ADCS', 'mass': 400, 'height': 32, 'CoM_Location': None}
        power = {'name': 'EPS', 'mass': 130, 'height': 12, 'CoM_Location': None}
        obc = {'name': 'OBC', 'mass': 25, 'height': 10, 'CoM_Location': None}
        comms = {'name': 'COMM', 'mass': 25, 'height': 7, 'CoM_Location': None}

        subsystems = [payload, adcs, power, obc, comms]
        
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

        
if __name__ == "__main__":

    structure = Structure()
    structure.optimal_stacking_order
    
    display(structure)