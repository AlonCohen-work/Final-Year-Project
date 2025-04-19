from constraint import Problem
from Algo import run_algo

def run_scheduler_manager(algo_result):
    print("\n=== Data from Algo ===")
    
    # Get and print basic data
    variables = algo_result['variables']
    shift_managers = algo_result['workers']['shift_managers']
    
    print(f"Total shift managers: {len(shift_managers)}")

    # find all shift supervisors variables
    manager_slot = {}
    for var_name, var_info in variables.items():
        if var_info['position'] == 'Shift Supervisor':
            manager_slot[var_name] = var_info
    print(f'found {len(manager_slot)} manger variables')        

if __name__ == "__main__":
    manager_id = 4
    algo_result = run_algo(manager_id)
    if algo_result:
        run_scheduler_manager(algo_result)

    
