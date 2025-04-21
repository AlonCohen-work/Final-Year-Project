from constraint import Problem
from Algo import run_algo, available_workers

def run_scheduler_manager(algo_result):    
    problem = Problem()
    variables = algo_result['variables']
    all_workers = (algo_result['workers']['shift_managers'] +
                  algo_result['workers']['with_weapon'] +
                  algo_result['workers']['without_weapon'])
    
    # הפעלת הפונקציה available_workers ושמירת התוצאה במשתנה
    availability = available_workers(all_workers)  # שינוי כאן
    
    # כעת אפשר להשתמש ב-availability כמילון
    for var_name, var_info in variables.items():
        day = var_info['day']
        shift = var_info['shift']
        position = var_info['position']
        
        if position == "shift supervisor":
            possible_workers = [w['_id'] for w in availability[day][shift]["shift_manager"]]
        elif var_info.get('required_weapon', False):
            possible_workers = [w['_id'] for w in availability[day][shift]["with_weapon"]]
        else:
            possible_workers = [w['_id'] for w in availability[day][shift]["without_weapon"]]
        
        problem.addVariable(var_name, possible_workers)

    solution = problem.getSolution()
    
    # הדפסת הפתרון
    if solution:
        print("\n=== Solution Found ===")
        for var_name, worker_id in solution.items():
            var_info = variables[var_name]
            print(f"Position: {var_info['position']}")
            print(f"Day: {var_info['day']}, Shift: {var_info['shift']}")
            print(f"Worker ID: {worker_id}")
            print("---")
    else:
        print("\nNo solution found!")

    return solution

if __name__ == "__main__":
    manager_id = 4
    algo_result = run_algo(manager_id)
    if algo_result:
        run_scheduler_manager(algo_result)

    
