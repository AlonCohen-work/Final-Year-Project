from ortools.sat.python import cp_model
from Algo import run_algo, available_workers
from OrTools import available_shift, variables_for_shifts


def one_shift_per_day(variables, model, workers, variable_model,days):
    for worker in workers:
        worker_id = worker['_id']

        for day in days:
            worker_assignments = []
            for var_name, var_info in variables.items():
                if var_info['day'] == day:
                    possible_ids = [w['_id'] for w in var_info['possible_workers']]
                    if worker_id in possible_ids:
                        cp_var = variable_model[var_name]
                        assigned = model.NewBoolVar(f"{var_name}_assigned_to_{worker_id}")
                        model.Add(cp_var == worker_id).OnlyEnforceIf(assigned)
                        model.Add(cp_var != worker_id).OnlyEnforceIf(assigned.Not())
                        worker_assignments.append(assigned)
            if worker_assignments:
                model.Add(sum(worker_assignments) <= 1)

def at_least_one_day_off(variables, model, workers, variable_model,days):

    for worker in workers:
        worker_id = worker['_id']
        works_that_day_list = []  # נשמור כאן את משתני הבוליאן שאומרים אם עבד ביום מסוים

        for day in days:
            assignments = []  # משתני בוליאן ליום הזה

            for var_name, var_info in variables.items():
                if var_info['day'] == day:
                    possible_ids = [w['_id'] for w in var_info['possible_workers']]
                    if worker_id in possible_ids:
                        cp_var = variable_model[var_name]
                        assigned = model.NewBoolVar(f"{var_name}_assigned_to_{worker_id}_for_dayoff")
                        model.Add(cp_var == worker_id).OnlyEnforceIf(assigned)
                        model.Add(cp_var != worker_id).OnlyEnforceIf(assigned.Not())
                        assignments.append(assigned)

            if assignments:
                # משתנה בוליאני שאומר אם העובד עבד ביום הזה
                works_that_day = model.NewBoolVar(f"worker_{worker_id}_works_on_{day}")
                model.AddMaxEquality(works_that_day, assignments)
                works_that_day_list.append(works_that_day)

        # לפחות יום חופשי => מקסימום 6 ימים עבודה
        model.Add(sum(works_that_day_list) <= 6)


def no_morning_after_evening(variables, model, workers, variable_model,days):
    
    for worker in workers:
        worker_id = worker['_id']
        
        for i in range(len(days) - 1):
            day_evening = days[i]
            day_morning = days[i + 1]
            
            evening_vars = []
            morning_vars = []

            for var_name, var_info in variables.items():
                if worker_id not in [w['_id'] for w in var_info['possible_workers']]:
                    continue  # worker can't do this shift

                if var_info['day'] == day_evening and var_info['shift'] == 'Evening':
                    cp_var = variable_model[var_name]
                    assigned = model.NewBoolVar(f"{var_name}_assigned_to_{worker_id}_night")
                    model.Add(cp_var == worker_id).OnlyEnforceIf(assigned)
                    model.Add(cp_var != worker_id).OnlyEnforceIf(assigned.Not())
                    evening_vars.append(assigned)

                elif var_info['day'] == day_morning and var_info['shift'] == 'Morning':
                    cp_var = variable_model[var_name]
                    assigned = model.NewBoolVar(f"{var_name}_assigned_to_{worker_id}_morning")
                    model.Add(cp_var == worker_id).OnlyEnforceIf(assigned)
                    model.Add(cp_var != worker_id).OnlyEnforceIf(assigned.Not())
                    morning_vars.append(assigned)

            # כל זוג ערב → בוקר: אם הוא עובד בערב אסור לו לעבוד בבוקר
            for ev in evening_vars:
                for mo in morning_vars:
                    model.AddBoolOr([ev.Not(), mo.Not()])



def print_solution_by_day(solver, variable_model, variables, days):
    shifts = ['Morning', 'Afternoon', 'Evening']
    schedule_by_day = {day: {shift: [] for shift in shifts} for day in days}
    worker_shift_count = {}

    for var_name, var in variable_model.items():
        info = variables[var_name]
        day = info['day']
        shift = info['shift']
        position = info['position']
        worker_id = solver.Value(var)

        schedule_by_day[day][shift].append((position, var_name, worker_id))
        worker_shift_count[worker_id] = worker_shift_count.get(worker_id, 0) + 1

    for day in days:
        print(f"\n=== {day} ===")
        for shift in shifts:
            print(f"  → {shift}")
            for position, var_name, worker_id in schedule_by_day[day][shift]:
                print(f"    {position}: {worker_id}")

    print("\n===Worker shift count===")
    for worker_id, count in worker_shift_count.items():
        print(f"🧍 worker id : {worker_id}: shift count : {count} ")


                
if __name__ == "__main__":
    model = cp_model.CpModel()
    manager_id = 4
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
 
    result = run_algo(manager_id)
    workers_data = result['workers']
    available_employee = available_workers(workers_data)
    variables = available_shift(result['variables'], available_employee)
    print("✅ Processed shifts")
    variable_model = variables_for_shifts(variables, model)

    # אילוץ: כל עובד יכול לעבוד מקסימום משמרת אחת ביום
    one_shift_per_day(variables, model, workers_data['shift_managers'] + workers_data['with_weapon'] + workers_data['without_weapon'], variable_model,days)
    #אילוץ יום חופש אחד בשבוע
    at_least_one_day_off(variables, model, workers_data['shift_managers'] + workers_data['with_weapon'] + workers_data['without_weapon'], variable_model,days)
    #אילוץ לא ערב ובוקר למוחרת
    no_morning_after_evening(variables, model, workers_data['shift_managers'] + workers_data['with_weapon'] + workers_data['without_weapon'], variable_model,days)


    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("\n✅ found solution!")
        #הדפסה בסיגנון הקודם
        #for var_name, var in variable_model.items():
         #   print(f"{var_name}: {solver.Value(var)}")
        print_solution_by_day(solver, variable_model, variables, days)

    else:
        print("\n❌ didnt found solution")     
        
 