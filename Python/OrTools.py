from Algo import run_algo, available_workers 
from ortools.sat.python import cp_model

# information of all the workers that can work in a shift 
def available_shift(variables, available_employee, id_to_worker):
    for var_name, var_info in variables.items():
        day = var_info['day']
        shift = var_info['shift']
        position = var_info['position']
        
        # Initialize empty list for possible workers
        possible_workers = []
        
        # Check if we have available workers for this day and shift
        if day in available_employee and shift in available_employee[day]:
            # Get the appropriate worker list based on position requirements
            if position == 'Shift Supervisor':
                # Only shift managers can be supervisors
                worker_ids = available_employee[day][shift]['shift_managers']
            elif var_info.get('required_weapon', True):
                # For positions requiring weapons, can use:
                # 1. Shift managers (they can do any position)
                # 2. Workers with weapons
                worker_ids = set(
                    available_employee[day][shift]['shift_managers'] +
                    available_employee[day][shift]['with_weapon']
                )
            else:
                # For positions not requiring weapons, can use:
                # 1. Shift managers (they can do any position)
                # 2. Workers with weapons (they can do both)
                # 3. Workers without weapons
                worker_ids = set(
                    available_employee[day][shift]['shift_managers'] +
                    available_employee[day][shift]['with_weapon'] +
                    available_employee[day][shift]['without_weapon']
                )
            
            # Convert IDs to worker objects
            possible_workers = [id_to_worker[worker_id] for worker_id in worker_ids]
            
            print(f"\nFor {day} {shift} {position}:")
            print(f"Found {len(possible_workers)} possible workers:")
            for worker in possible_workers:
                print(f"- {worker.get('name', 'Unknown')} (ID: {worker['_id']})")
                # Print worker's qualifications
                if worker['_id'] in available_employee[day][shift]['shift_managers']:
                    print("  * Can be shift manager")
                if worker['_id'] in available_employee[day][shift]['with_weapon']:
                    print("  * Can work with weapon")
                if worker['_id'] in available_employee[day][shift]['without_weapon']:
                    print("  * Can work without weapon")
        
        var_info['possible_workers'] = possible_workers
        
    return variables
#creating the variables for the algo that he can use them 
def variables_for_shifts(variables, model):
    variablesModel = {}
    for var_name, var_info in variables.items():
        workers = var_info['possible_workers']
        worker_id = [w['_id'] for w in workers]

        if not worker_id:
            continue
         
        variablesKey = model.NewIntVarFromDomain(
            cp_model.Domain.FromValues(worker_id), var_name
        )
        variablesModel[var_name] = variablesKey

    return variablesModel