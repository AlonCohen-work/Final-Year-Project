from constraint import Problem
from Algo import run_algo

def run_scheduler_manager(algo_result):    
    # Get and print basic data
    variables = algo_result['variables']
    shift_managers = algo_result['workers']['shift_managers']
    manager_map = {manager['_id']: manager for manager in shift_managers}
    
    print(f"Total shift managers: {len(shift_managers)}")

    # find all shift supervisors variables
    manager_slot = {}
    for var_name, var_info in variables.items():
        if var_info['position'] == 'Shift Supervisor':
            manager_slot[var_name] = var_info
    print(f'found {len(manager_slot)} manger variables')     

    # קורא לפונקציה ומדפיס את התוצאה
    solution = find_manager_that_avaliable(manager_slot, shift_managers)
    
    if solution:
        for var_name, manager_id in solution.items():
            manager = manager_map[manager_id]
            slot_info = manager_slot[var_name]
            print(f"filed: {var_name}")
            print(f"manager: {manager['name']}")
            print(f"shift: {slot_info['day']} - {slot_info['shift']}")
            print("---")
    else:
        print("No solution found!")

#add variables to problem
# עובר על כל יום ומשמרת ובודק שהיום והמשמרת שהאחראי בחר מתאימה ליום שדרוש אצל המנהל 
def find_manager_that_avaliable(manager_slot, shift_managers):
    problem = Problem() 
 
    for var_name, var_info in manager_slot.items():
        avaliable_managers = [] 
        for manager in shift_managers:
            for day_info in manager['selectedDays']:
                if day_info['day'] == var_info['day'] and var_info['shift'] in day_info['shifts']:
                    avaliable_managers.append(manager['_id'])
                    break

        problem.addVariable(var_name, avaliable_managers) 

    

    solution = problem.getSolution()

    return solution   

if __name__ == "__main__":
    manager_id = 4
    algo_result = run_algo(manager_id)
    if algo_result:
        run_scheduler_manager(algo_result)

    
