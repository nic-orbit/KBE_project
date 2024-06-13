import itertools

class Stacker:
    def __init__(self, subsystems, fixed_at_bottom=None) -> None:
        self.subsystems = subsystems
        self.fixed_at_bottom = fixed_at_bottom

    def calculate_CoM(self, stack):
        total_mass = sum(sub['mass'] for sub in stack)
        weighted_sum = 0

        for sub in stack:
            sub_CoM = sub['CoM_height'] / 2
            weighted_sum += sub['mass'] * sub_CoM

        CoM = weighted_sum / total_mass

        return CoM
    
    def find_optimal_stacking_order(self, distance_btw_subsystems):
        min_distance = float('inf') # Initialize minimum distance to infinity
        optimal_stack = None

        # Generate all permutations of subsystems
        permutations = itertools.permutations(subsystems)
        
        # Iterate through all permutations
        for perm in permutations:
            if self.fixed_at_bottom and perm[0]['name'] != self.fixed_at_bottom['name']:
                continue  # Skip permutations that don't have the fixed subsystem at the bottom
            
            current_height = 0
            # Iterate through all subsystems in the permutation
            for sub in perm:
                sub['CoM_height'] = current_height + sub['height'] / 2
                current_height += sub['height'] + distance_btw_subsystems

            total_height = current_height - distance_btw_subsystems # remove the last distance added

            geometric_center = total_height / 2
            CoM = calculate_CoM(perm)
            distance = abs(CoM - geometric_center)
            
            if distance < min_distance:
                self.min_distance = distance
                self.optimal_stack = perm
                self.total_height = total_height
        
        return optimal_stack, min_distance, total_height


# Function to calculate the center of mass for a given stack
def calculate_CoM(stack):

    total_mass = sum(sub['mass'] for sub in stack)
    weighted_sum = 0

    for sub in stack:
        sub_CoM = sub['CoM_height'] / 2
        weighted_sum += sub['mass'] * sub_CoM

    CoM = weighted_sum / total_mass

    return CoM

# Function to find the optimal stacking configuration
def find_optimal_stacking_order(subsystems, distance_btw_subsystems, fixed_at_bottom=None):

    min_distance = float('inf') # Initialize minimum distance to infinity
    optimal_stack = None
    
    # Generate all permutations of subsystems
    permutations = itertools.permutations(subsystems)
    
    # Iterate through all permutations
    for perm in permutations:
        if fixed_at_bottom and perm[0]['name'] != fixed_at_bottom['name']:
            continue  # Skip permutations that don't have the fixed subsystem at the bottom
        
        current_height = 0
        # Iterate through all subsystems in the permutation
        for sub in perm:
            sub['CoM_height'] = current_height + sub['height'] / 2
            current_height += sub['height'] + distance_btw_subsystems

        total_height = current_height - distance_btw_subsystems # remove the last distance added

        geometric_center = total_height / 2
        CoM = calculate_CoM(perm)
        distance = abs(CoM - geometric_center)
        
        if distance < min_distance:
            min_distance = distance
            optimal_stack = perm
    
    return optimal_stack, min_distance, total_height


def display_stacking(stack, total_height):
    # print stacking order, showing the subsystem name and CoM height; the top one first
    for sub in reversed(stack):
        print(f"{sub['name']} (CoM height: {sub['CoM_height']}; height: {sub['height']}; mass: {sub['mass']})")
    
    # print the total height of the stack 
    print(f"\nTotal height: {total_height}")
    # print the geometric center of the stack
    geometric_center = total_height / 2
    print(f"Geometric center: {geometric_center}")
    # print the calculated CoM of the stack
    CoM_total = calculate_CoM(stack)
    print(f"Calculated CoM of the stack: {CoM_total}")
    # print the minimum distance between the CoM and the geometric center
    CoM_distance = CoM_total - geometric_center
    print(f"Minimum distance from CoM to geometric center: {CoM_distance}")


def calculate_form_factor_and_spare_space(total_height):
    if total_height < 100:
        form_factor = 1
    elif total_height < 150:
        form_factor = 1.5
    elif total_height < 200:
        form_factor = 2
    elif total_height < 300:
        form_factor = 3
    else:
        raise ValueError("Total height exceeds maximum form factor of 3")
    spare_space = 100*form_factor - total_height
    return form_factor, spare_space
    

if __name__ == "__main__":

    # Subsystems data
    payload = {'name': 'payload', 'mass': 300, 'height': 70, 'CoM_height': None}
    adcs = {'name': 'adcs', 'mass': 500, 'height': 60, 'CoM_height': None}
    power = {'name': 'power', 'mass': 100, 'height': 50, 'CoM_height': None}
    obc = {'name': 'obc', 'mass': 100, 'height': 30, 'CoM_height': None}
    comms = {'name': 'comms', 'mass': 100, 'height': 30, 'CoM_height': None}

    subsystems = [payload, adcs, power, obc, comms]

    # calculate distance between subsystems based on stack height and spare space in the cubesat
    total_height = sum(sub['height'] for sub in subsystems)

    form_factor, spare_space = calculate_form_factor_and_spare_space(total_height)

    distance_btw_subsystems = spare_space / (len(subsystems) - 1)
    # distance_btw_subsystems = 0

    print(f"\nDistance between subsystems: {distance_btw_subsystems} mm")

    

    optimal_stacking_order, min_distance, total_height = find_optimal_stacking_order(subsystems, distance_btw_subsystems, fixed_at_bottom=payload)

    display_stacking(optimal_stacking_order, total_height)