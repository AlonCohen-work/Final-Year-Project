from constraint import Problem
from Algo import run_algo, available_workers

def print_solution_by_day(solution, variables):
    if solution:
        print("\n=== Schedule By Day ===")
        
        # ארגון לפי ימים
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        shifts = ['Morning', 'Afternoon', 'Evening']
        
        for day in days:
            print(f"\nDay: {day}")
            for shift in shifts:
                print(f"\n  Shift: {shift}")
                # מיון לפי משמרות ותפקידים
                shift_assignments = [(var_name, worker_id) for var_name, worker_id in solution.items() 
                                  if variables[var_name]['day'] == day and 
                                  variables[var_name]['shift'] == shift]
                
                for var_name, worker_id in shift_assignments:
                    position = variables[var_name]['position']
                    print(f"    {position}: Worker {worker_id}")
    else:
        print("\nNo solution found!")

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
    print_solution_by_day(solution, variables)
    return solution

if __name__ == "__main__":
    manager_id = 4
    algo_result = run_algo(manager_id)
    if algo_result:
        run_scheduler_manager(algo_result)

    
