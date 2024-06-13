import itertools
from parapy.core import *
import parapy
from cubesat_configurator import subsystem as ac
from parapy.gui import display
from pprint import pprint
import math


class Structure(ac.Subsystem):
    form_factor = Input(3)
    
    @Attribute
    def subsystem_data_for_stacking(self):
        """
        Returns a list of dictionaries with the height, mass and name of each subsystem.
        """
        # Subsystems data
        payload = {'name': 'Payload', 'mass': 300, 'height': 70, 'CoM_Location': None}
        adcs = {'name': 'ADCS', 'mass': 500, 'height': 60, 'CoM_Location': None}
        power = {'name': 'EPS', 'mass': 100, 'height': 50, 'CoM_Location': None}
        obc = {'name': 'OBC', 'mass': 100, 'height': 30, 'CoM_Location': None}
        comms = {'name': 'COMM', 'mass': 100, 'height': 30, 'CoM_Location': None}

        subsystems = [payload, adcs, power, obc, comms]
        
        return subsystems
    
    @Attribute
    def optimal_stacking_order(self):
        """
        Returns the optimal stacking order of the subsystems based on the form factor of the satellite.
        """
        # find 'Payload' subsystem and fix it at the bottom of the stack
        fixed_at_bottom = next(sub for sub in self.subsystem_data_for_stacking if sub['name'] == 'Payload')
        
        optimal_stack = self._find_optimal_stacking_order(self.subsystem_data_for_stacking, self.form_factor, fixed_at_bottom)
        

    
    def _find_optimal_stacking_order(self, subsystems, form_factor, fixed_at_bottom=None):

        min_distance = float('inf') # Initialize minimum distance to infinity
        optimal_stack = None

        subsystems_list = subsystems.copy()

        # calculate leftover space for spacers
        space_for_spacers = 100*form_factor - sum(sub['height'] for sub in subsystems_list)
        # round down to the nearest integer
        spacer_size = 10 # mm
        num_spacers = int(space_for_spacers // spacer_size)
        print(f"Space for spacers: {space_for_spacers} mm")
        
        # append spacers to the end of the subsystems list
        for i in range(num_spacers):
            subsystems_list.append({'name': f'Spacer_{i}', 'mass': 0, 'height': spacer_size, 'CoM_Location': None})

        print('\nstart permutating...')

        permutations = itertools.permutations(subsystems_list)
        
        perm_list = []
        i = 0
        
        # Iterate through all permutations
        for perm in permutations:
            i += 1
            if fixed_at_bottom and perm[0]['name'] != fixed_at_bottom['name']:
                continue  # Skip permutations that don't have the fixed subsystem at the bottom
            
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
        
            # stop when the optimal stacking order is zero
            if min_distance == 0:
                break

        # calculate number of permutations
        N_perm = math.factorial(len(subsystems_list)) 
        
        # print the number of permutations
        print(f"Number of permutations: {N_perm}\n"
              f"\nNumber of iterations: {i}")
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

    # @Attribute
    # def CoM(self):
    #     return Point(x=0.5*self.width, y=0.5*self.length, z=0.5*self.height)

    

if __name__ == "__main__":

    structure = Structure()
    structure.optimal_stacking_order
    
    # display(structure)