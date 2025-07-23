# --- START OF FILE OrTools.py ---

from ortools.sat.python import cp_model
import logging

logger = logging.getLogger(__name__)

def available_shift(variables, available_employee, id_to_worker):
    """
    Filters the list of possible workers for each shift variable based on their
    explicitly stated availability for that specific day and shift.
    """
    logger.info("Filtering possible workers based on specific shift availability...")
    try:
        for var_name, var_info in variables.items():
            day = var_info['day']
            shift = var_info['shift']
            position = var_info['position']
            
            possible_worker_ids = set()
            
            if day in available_employee and shift in available_employee[day]:
                availability_data = available_employee[day][shift]
                
                if position == 'Shift Supervisor':
                    possible_worker_ids.update(availability_data.get('shift_managers', []))
                elif var_info.get('required_weapon'):
                    possible_worker_ids.update(availability_data.get('shift_managers', []))
                    possible_worker_ids.update(availability_data.get('with_weapon', []))
                else:
                    possible_worker_ids.update(availability_data.get('shift_managers', []))
                    possible_worker_ids.update(availability_data.get('with_weapon', []))
                    possible_worker_ids.update(availability_data.get('without_weapon', []))
            
            # Update the variable's possible workers with the filtered list of full worker objects
            var_info['possible_workers'] = [id_to_worker[wid] for wid in possible_worker_ids if wid in id_to_worker]
        
        logger.info("Finished filtering possible workers.")
        return variables
    except Exception as e:
        logger.error(f"An error occurred in available_shift: {e}", exc_info=True)
        return variables # Return original variables on error

def variables_for_shifts(variables, model):
    """
    Creates the core OR-Tools integer variables for the constraint solver.
    Each variable's domain is the set of IDs of workers who can be assigned to it.
    """
    logger.info("Creating OR-Tools model variables for each shift...")
    variable_model = {}
    try:
        for var_name, var_info in variables.items():
            possible_worker_ids = [w['_id'] for w in var_info.get('possible_workers', [])]

            if not possible_worker_ids:
                # This case is handled by dummy workers, but a warning is useful.
                logger.warning(f"Shift '{var_name}' has no available workers. It will require a dummy assignment.")
                continue
            
            domain = cp_model.Domain.FromValues(possible_worker_ids)
            variable_model[var_name] = model.NewIntVarFromDomain(domain, var_name)
        
        logger.info(f"Created {len(variable_model)} OR-Tools variables.")
        return variable_model
    except Exception as e:
        logger.error(f"An error occurred in variables_for_shifts: {e}", exc_info=True)
        return {}