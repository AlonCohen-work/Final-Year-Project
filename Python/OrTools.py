from Algo import run_algo, available_workers 
from ortools.sat.python import cp_model

# information of all the workers that can work in a shift 
def available_shift(variables, available_employee, id_to_worker):
    for var_name, var_info in variables.items():
        day = var_info['day']
        shift = var_info['shift']
        position = var_info['position']

        if day in available_employee and shift in available_employee[day]:
            if position == 'Shift Supervisor':
                ids = available_employee[day][shift]['shift_managers']
            elif var_info.get('required_weapon', True):
                ids = (
                    available_employee[day][shift]['shift_managers'] +
                    available_employee[day][shift]['with_weapon']
                )
            else:
                ids= (
                    available_employee[day][shift]['shift_managers'] +
                    available_employee[day][shift]['with_weapon'] +
                    available_employee[day][shift]['without_weapon']
                )

        else:
            ids = []
    
        unique_ids  = set(ids)
        possible_workers = [id_to_worker[id] for id in unique_ids]        

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