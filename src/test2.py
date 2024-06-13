import itertools
from scipy.optimize import minimize

# Subsystems data
payload = {'name': 'payload', 'mass': 500, 'height': 70, 'CoM_height': 35}
adcs = {'name': 'adcs', 'mass': 250, 'height': 60, 'CoM_height': 30}
power = {'name': 'power', 'mass': 200, 'height': 50, 'CoM_height': 25}
obc = {'name': 'obc', 'mass': 100, 'height': 30, 'CoM_height': 15}
comms = {'name': 'comms', 'mass': 100, 'height': 30, 'CoM_height': 15}

subsystems = [payload, adcs, power, obc, comms]

# Function to calculate the center of mass for a given stack
def calculate_CoM(stack, positions):
    total_mass = sum(sub['mass'] for sub in stack)
    weighted_sum = 0
    
    for sub, pos in zip(stack, positions):
        weighted_sum += sub['mass'] * pos
    
    CoM = weighted_sum / total_mass
    return CoM

# Objective function for optimization
def objective(positions, stack, total_height):
    CoM = calculate_CoM(stack, positions)
    geometric_center = total_height / 2
    return abs(CoM - geometric_center)

# Function to find the optimal stacking configuration with spread
def find_optimal_stacking_order_with_spread(subsystems, total_height, fixed_at_bottom=None):
    min_distance = float('inf') # Initialize minimum distance to infinity
    optimal_stack = None
    
    # Generate all permutations of subsystems
    permutations = itertools.permutations(subsystems)
    
    for perm in permutations:
        if fixed_at_bottom and perm[0]['name'] != fixed_at_bottom['name']:
            continue  # Skip permutations that don't have the fixed subsystem at the bottom
        
        heights = [sub['height'] for sub in perm]
        num_subsystems = len(heights)
        
        # Initial guess: even spread across the total height
        initial_positions = [sum(heights[:i+1]) - heights[i]/2 for i in range(num_subsystems)]
        
        # Bounds: each subsystem must be within its height range
        bounds = [(0, total_height) for _ in range(num_subsystems)]
        
        # Constraint: the positions must sum up to total height minus individual heights
        constraints = [{'type': 'eq', 'fun': lambda x: sum(x) - total_height}]
        
        # Optimization
        result = minimize(objective, initial_positions, args=(perm, total_height), bounds=bounds, constraints=constraints)
        
        if result.success:
            distance = objective(result.x, perm, total_height)
            if distance < min_distance:
                min_distance = distance
                optimal_stack = (perm, result.x)
    
    return optimal_stack, min_distance

# Total height based on form factor (example: 200 units)
total_height = 200

optimal_stacking_order_with_spread, min_distance_with_spread = find_optimal_stacking_order_with_spread(subsystems, total_height, fixed_at_bottom=payload)

def display_stacking_with_spread(stack, positions):
    # Print stacking order, showing the subsystem name and its position; the top one first
    for sub, pos in sorted(zip(stack, positions), key=lambda x: x[1], reverse=True):
        print(f"{sub['name']} (Position: {pos})")
    
    # Print the total height of the stack 
    total_height = sum(sub['height'] for sub in stack)
    print(f"\nTotal height: {total_height}")
    # Print the geometric center of the stack
    geometric_center = total_height / 2
    print(f"Geometric center: {geometric_center}")
    # Print the calculated CoM of the stack
    CoM_total = calculate_CoM(stack, positions)
    print(f"Calculated CoM of the stack: {CoM_total}")
    # Print the minimum distance between the CoM and the geometric center
    CoM_distance = CoM_total - geometric_center
    print(f"Minimum distance from CoM to geometric center: {CoM_distance}")

display_stacking_with_spread(*optimal_stacking_order_with_spread)
