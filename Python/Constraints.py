from ortools.sat.python import cp_model
from Algo import run_algo, available_workers
from OrTools import available_shift, variables_for_shifts

DUMMY_ID = -1

def one_shift_per_day(variables, model, workers, variable_model, days):
    # Create a dictionary to store assignments for each worker per day
    worker_assignments_per_day = {}
    
    for worker in workers:
        worker_id = worker['_id']
        if worker_id == DUMMY_ID:
            continue
        
        # Initialize assignments dictionary for this worker
        if worker_id not in worker_assignments_per_day:
            worker_assignments_per_day[worker_id] = {}
        
        for day in days:
        #    print(f"Checking day {day}")
            # Initialize list for this day if not exists
            if day not in worker_assignments_per_day[worker_id]:
                worker_assignments_per_day[worker_id][day] = []
            
            # Collect all possible assignments for this worker on this day
            day_assignments = []
            for var_name, var_info in variables.items():
                if var_info['day'] == day:
                    # Get all possible workers for this shift
                    possible_workers = var_info['possible_workers']
                    possible_ids = [w['_id'] if isinstance(w, dict) else w for w in possible_workers]
                    
                    if worker_id in possible_ids:
                        cp_var = variable_model[var_name]
                        # Create a boolean variable for this assignment
                        assigned = model.NewBoolVar(f"{var_name}_assigned_to_{worker_id}")
                        # Link the assignment variable to the actual assignment
                        model.Add(cp_var == worker_id).OnlyEnforceIf(assigned)
                        model.Add(cp_var != worker_id).OnlyEnforceIf(assigned.Not())
                        day_assignments.append(assigned)
            #            print(f"Worker {worker_id} can be assigned to {var_name}")
            
            # If there are any possible assignments for this day
            if day_assignments:
                # Add constraint: worker can only be assigned to one shift per day
                model.Add(sum(day_assignments) <= 1)
                worker_assignments_per_day[worker_id][day].extend(day_assignments)
            #    print(f"Added constraint for worker {worker_id} on day {day}: max one shift")
            #    print(f"Total possible assignments for this day: {len(day_assignments)}")

def at_least_one_day_off(variables, model, workers, variable_model,days):

    for worker in workers:
        worker_id = worker['_id']
        if worker_id == DUMMY_ID:
            continue
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
        if worker_id == DUMMY_ID:
            continue
        
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

def solution_by_day(solver, variable_model, variables, days):
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

    return schedule_by_day, worker_shift_count    

def print_solution(schedule_by_day, worker_shift_count):
    for day, shifts in schedule_by_day.items():
        print(f"\n==={day}===")
        for shift, assignments in shifts.items():
            print(f"--{shift}--")
            for position, var_name, worker_id in assignments:
                print(f"{position}: {worker_id}")

    print(f"\n === worker shift count ===")
    for worker_id, count in worker_shift_count.items():
            print(f"🧍 worker id : {worker_id}: shift count : {count} ")

def missing_workers(schedule_by_day):
    missing_workers = {}
    for day, shifts in schedule_by_day.items():
        for shift, assignments in shifts.items():
            for assignment in assignments:
                position, var_name, worker_id = assignment

                if position is None or var_name is None:
                    if day not in missing_workers:
                        missing_workers[day]= {}
                    if shift not in missing_workers[day]:   
                        missing_workers[day][shift]= [] 

                    missing_workers[day][shift].append((position, var_name))       
    return missing_workers

def print_missing_workers(missing_workers):
    if not missing_workers:
        print(" no missing workers")

    for day, shifts in missing_workers.items():
        print(f"\n == {day} ==")
        for shift, assignments in shifts.items():
            print(f"--{shift}--")
            for position, var_name in assignments:
                print(f" missing worker for {position} : {var_name}")    

def add_dummy_worker(variables, id_to_worker):
    id_to_worker[DUMMY_ID] = {'_id': DUMMY_ID, 'name': 'No Worker'}
    for var_name, var_info in variables.items():
        if DUMMY_ID not in [w['_id'] if isinstance(w, dict) else w for w in var_info['possible_workers']]:
            var_info['possible_workers'].append(id_to_worker[DUMMY_ID])

# --- Add per-shift dummy workers ---
def add_per_shift_dummies(variables, id_to_worker):
    dummy_ids = {}
    for idx, (var_name, var_info) in enumerate(variables.items()):
        dummy_id = -(idx + 1)  # Unique negative ID for each dummy
        dummy_worker = {'_id': dummy_id, 'name': f'No Worker ({var_name})'}
        id_to_worker[dummy_id] = dummy_worker
        var_info['possible_workers'].append(dummy_worker)
        dummy_ids[var_name] = dummy_id
    return dummy_ids

if __name__ == "__main__":
    model = cp_model.CpModel()
    manager_id = 4
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    result = run_algo(manager_id)
    workers_data = result['workers']
    available_employee , id_of_worker= available_workers(workers_data)
    variables = available_shift(result['variables'], available_employee, id_of_worker)
    print("✅ Processed shifts")
    variable_model = variables_for_shifts(variables, model)

    # Print number of workers and variables
    num_shift_managers = len(workers_data['shift_managers'])
    num_with_weapon = len(workers_data['with_weapon'])
    num_without_weapon = len(workers_data['without_weapon'])
    num_workers = num_shift_managers + num_with_weapon + num_without_weapon
    num_variables = len(variables)
    print(f"Total number of workers: {num_workers}")
    print(f"  Shift managers: {num_shift_managers}")
    print(f"  With weapon: {num_with_weapon}")
    print(f"  Without weapon: {num_without_weapon}")
    print(f"Total number of variables (shifts/positions): {num_variables}")

    # Print number of available workers per day
    print("\n=== Available workers per day ===")
    for day in days:
        available_ids = set()
        if day in available_employee:
            for shift in available_employee[day]:
                for group in ["shift_managers", "with_weapon", "without_weapon"]:
                    available_ids.update(available_employee[day][shift][group])
        print(f"{day}: {len(available_ids)} unique available workers")

    # Print number of applicants per shift per day
    print("\n=== Applicants per shift per day ===")
    for day in days:
        if day in available_employee:
            for shift in available_employee[day]:
                applicants = set()
                for group in ["shift_managers", "with_weapon", "without_weapon"]:
                    applicants.update(available_employee[day][shift][group])
                print(f"{day} {shift}: {len(applicants)} applicants")

    # FLAGS FOR CONSTRAINTS
    active_constraints = {
        "one_shift_per_day": True,
        "at_least_one_day_off": True,
        "no_morning_after_evening": True,
        "allow_partial_solution": True,
    }
    print("Active constraints:", [k for k, v in active_constraints.items() if v])

    # Add per-shift dummy workers for partial solution mode
    dummy_ids = None
    if active_constraints["allow_partial_solution"]:
        dummy_ids = add_per_shift_dummies(variables, id_of_worker)
        print(f"\nAdded per-shift dummy workers")

    # Print initial variable information
    print("\n=== Initial Variable Information ===")
    for var_name, var_info in variables.items():
        possible_workers = var_info['possible_workers']
        worker_ids = [w['_id'] if isinstance(w, dict) else w for w in possible_workers]
        print(f"{var_name}: {len(worker_ids)} possible workers (including dummy: {DUMMY_ID in worker_ids})")

    # Apply constraints based on flags
    if active_constraints["one_shift_per_day"]:
        one_shift_per_day(variables, model, workers_data['shift_managers'] + workers_data['with_weapon'] + workers_data['without_weapon'], variable_model,days)
    if active_constraints["at_least_one_day_off"]:
        at_least_one_day_off(variables, model, workers_data['shift_managers'] + workers_data['with_weapon'] + workers_data['without_weapon'], variable_model,days)
    if active_constraints["no_morning_after_evening"]:
        no_morning_after_evening(variables, model, workers_data['shift_managers'] + workers_data['with_weapon'] + workers_data['without_weapon'], variable_model,days)

    # Objective: maximize real assignments (not dummy)
    if active_constraints["allow_partial_solution"]:
        filled_vars = []
        for var_name, var_info in variables.items():
            cp_var = variable_model[var_name]
            dummy_id = dummy_ids[var_name]
            filled = model.NewBoolVar(f"{var_name}_filled")
            model.Add(cp_var != dummy_id).OnlyEnforceIf(filled)
            model.Add(cp_var == dummy_id).OnlyEnforceIf(filled.Not())
            filled_vars.append(filled)
        model.Maximize(sum(filled_vars))

    solver = cp_model.CpSolver()    
    # Try to find a solution with per-shift dummies
    print("\nTrying to find solution with per-shift dummy workers...")
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("\n✅ Solution found!")
        schedule_by_day, worker_shift_counts = solution_by_day(solver, variable_model, variables, days)
        print_solution(schedule_by_day, worker_shift_counts)
        
        # Count how many shifts were filled by real workers vs dummies
        real_worker_shifts = 0
        dummy_shifts = 0
        for var_name, var in variable_model.items():
            assigned_id = solver.Value(var)
            if dummy_ids and assigned_id == dummy_ids[var_name]:
                dummy_shifts += 1
            else:
                real_worker_shifts += 1
        print(f"\nShifts filled by real workers: {real_worker_shifts}")
        print(f"Shifts filled by dummy workers: {dummy_shifts}")
        print(f"Total shifts: {len(variables)}")
        if dummy_shifts > 0:
            print("\n⚠️ PARTIAL SOLUTION: Not enough real workers to cover all shifts. Some shifts are unfilled (assigned to dummy workers). Consider adding more workers or relaxing constraints.")
    else:
        print("\n❌ No solution found (even with per-shift dummies)")
        print("Active constraints:", [k for k, v in active_constraints.items() if v])
        print("\nNOTE: If this happens, there may be another hard constraint (not related to worker count) making the model infeasible.")   