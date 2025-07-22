# --- START OF FILE OrTools.py ---

from ortools.sat.python import cp_model

def available_shift(variables, available_employee, id_to_worker):
    """
    Filters the list of possible workers for each shift variable.
    It refines the list from run_algo to only include workers who have explicitly
    stated they are available for that specific day and shift.
    """
    for var_name, var_info in variables.items():
        day = var_info['day']
        shift = var_info['shift']
        position = var_info['position']
        
        possible_worker_ids = set()
        
        # Check if availability data exists for this day and shift
        if day in available_employee and shift in available_employee[day]:
            availability_data = available_employee[day][shift]
            
            # Determine the required qualifications for the position
            if position == 'Shift Supervisor':
                # Only shift managers can be supervisors
                possible_worker_ids.update(availability_data['shift_managers'])
            elif var_info.get('required_weapon'):
                # For positions requiring a weapon, shift managers and workers with weapons are eligible
                possible_worker_ids.update(availability_data['shift_managers'])
                possible_worker_ids.update(availability_data['with_weapon'])
            else:
                # For positions not requiring a weapon, anyone available can work
                possible_worker_ids.update(availability_data['shift_managers'])
                possible_worker_ids.update(availability_data['with_weapon'])
                possible_worker_ids.update(availability_data['without_weapon'])
        
        # Update the variable's possible workers with the filtered list of worker objects
        var_info['possible_workers'] = [id_to_worker[worker_id] for worker_id in possible_worker_ids]
        
    return variables

def variables_for_shifts(variables, model):
    """
    Creates the core OR-Tools variables for the constraint satisfaction problem.
    Each variable represents a shift to be filled, and its domain is the set of
    IDs of workers who can be assigned to it.
    """
    variable_model = {}
    for var_name, var_info in variables.items():
        possible_worker_ids = [w['_id'] for w in var_info['possible_workers']]

        # Only create a variable if there is at least one possible worker (including dummies later)
        if not possible_worker_ids:
            print(f"Warning: No possible workers for {var_name}. This shift cannot be filled.")
            continue
         
        # Create an integer variable whose value must be one of the possible worker IDs.
        domain = cp_model.Domain.FromValues(possible_worker_ids)
        variable_model[var_name] = model.NewIntVarFromDomain(domain, var_name)

    return variable_model

def print_possible_workers_per_shift(variables):
    """
    A helper function for debugging to print the potential candidates for each shift.
    """
    print("\n--- Possible Workers for Each Shift (After Availability Filter) ---")
    for var_name, var_info in sorted(variables.items()):
        real_workers = [w for w in var_info['possible_workers'] if w['_id'] > 0]
        
        if not real_workers:
            print(f"{var_name}: !! No real workers available for this shift !!")
        else:
            worker_names = [w.get('name', 'Unknown') for w in real_workers]
            print(f"{var_name}: {len(worker_names)} possible workers -> {', '.join(worker_names)}")