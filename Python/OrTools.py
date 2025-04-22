from Algo import run_algo, available_workers 
from ortools.sat.python import cp_model

# information of all the workers that can work in a shift 
def available_shift(variables, available_employee):
    for var_name, var_info in variables.items():
        day = var_info['day']
        shift = var_info['shift']

        if day in available_employee and shift in available_employee[day]:
            possible_workers = (available_employee[day][shift]['shift_managers']+
                                available_employee[day][shift]['with_weapon']+
                                available_employee[day][shift]['without_weapon'])
        else:
            possible_workers = []

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