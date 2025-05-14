from ortools.sat.python import cp_model
from Algo import run_algo, available_workers
from OrTools import available_shift, variables_for_shifts, print_possible_workers_per_shift
from datetime import datetime
from MongoConnection import connect_to_mongo, mongo_db,connect

import schedule
import time
import argparse

DUMMY_ID = -1

def one_shift_per_day(variables, model, workers, variable_model, days):
    for worker in workers:
        worker_id = worker['_id']
        if worker_id == DUMMY_ID: #where DUMMY_ID = -1
            continue
        for day in days:
            assignments = []
            for var_name, var_info in variables.items():
                if var_info['day'] == day:
                    possible_ids = [w['_id'] for w in var_info['possible_workers']]
                    if worker_id in possible_ids:
                        cp_var = variable_model[var_name]
                        assigned = model.NewBoolVar(f"{var_name}_assigned_to_{worker_id}")
                        model.Add(cp_var == worker_id).OnlyEnforceIf(assigned)
                        model.Add(cp_var != worker_id).OnlyEnforceIf(assigned.Not())
                        assignments.append(assigned)
            if assignments:
                model.Add(sum(assignments) <= 1)

def at_least_one_day_off(variables, model, workers, variable_model, days):
    for worker in workers:
        worker_id = worker['_id']
        if worker_id == DUMMY_ID:
            continue
        works_that_day_list = []
        for day in days:
            assignments = []
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
                works_that_day = model.NewBoolVar(f"worker_{worker_id}_works_on_{day}")
                model.AddMaxEquality(works_that_day, assignments)
                works_that_day_list.append(works_that_day)
        model.Add(sum(works_that_day_list) <= 6)

def no_morning_after_evening(variables, model, workers, variable_model, days):
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
                    continue
                cp_var = variable_model[var_name]
                if var_info['day'] == day_evening and var_info['shift'] == 'Evening':
                    assigned = model.NewBoolVar(f"{var_name}_assigned_to_{worker_id}_night")
                    model.Add(cp_var == worker_id).OnlyEnforceIf(assigned)
                    model.Add(cp_var != worker_id).OnlyEnforceIf(assigned.Not())
                    evening_vars.append(assigned)
                elif var_info['day'] == day_morning and var_info['shift'] == 'Morning':
                    assigned = model.NewBoolVar(f"{var_name}_assigned_to_{worker_id}_morning")
                    model.Add(cp_var == worker_id).OnlyEnforceIf(assigned)
                    model.Add(cp_var != worker_id).OnlyEnforceIf(assigned.Not())
                    morning_vars.append(assigned)
            for ev in evening_vars:
                for mo in morning_vars:
                    model.AddBoolOr([ev.Not(), mo.Not()])

def fairness_constraint(variables, model, workers, variable_model):
    worker_ids = [w['_id'] for w in workers if w['_id'] > 0] # Real workers
    if not worker_ids or len(worker_ids) < 2: # No fairness constraint if less than 2 workers
        return []

    availability_limits = {
        w['_id']: sum(len(day.get('shifts', [])) for day in w.get('selectedDays', []))
        for w in workers if w['_id'] > 0
    }

    # 1. Count shifts assigned to each worker
    worker_shifts_assigned_vars = {wid: [] for wid in worker_ids}
    for var_name, var_info in variables.items():
        cp_var = variable_model[var_name]
        for worker_id in worker_ids:
            if worker_id in [w['_id'] for w in var_info['possible_workers']]:
                is_assigned_to_this_shift = model.NewBoolVar(f"{var_name}_assigned_to_{worker_id}_fairness")
                model.Add(cp_var == worker_id).OnlyEnforceIf(is_assigned_to_this_shift)
                model.Add(cp_var != worker_id).OnlyEnforceIf(is_assigned_to_this_shift.Not())
                worker_shifts_assigned_vars[worker_id].append(is_assigned_to_this_shift)

    num_shifts_per_worker = {}
    for wid in worker_ids:
        if not worker_shifts_assigned_vars[wid]:
            num_shifts_per_worker[wid] = model.NewConstant(0)
        else:
            total_shifts_var = model.NewIntVar(
                0,
                availability_limits.get(wid, len(variables)), # Max shifts worker can take
                f"total_shifts_for_{wid}"
            )
            model.Add(total_shifts_var == sum(worker_shifts_assigned_vars[wid]))
            num_shifts_per_worker[wid] = total_shifts_var
        
        # Hard constraint: worker cannot be assigned more shifts than they are available for
        max_allowed = availability_limits.get(wid, len(variables))
        model.Add(num_shifts_per_worker[wid] <= max_allowed)

    # 2. Calculate fairness penalty terms
    fairness_penalty_terms = []
    # This is the desired maximum difference. We penalize deviations *above* this.
    PREFERRED_MAX_DIFFERENCE = 3 # Example: ideally, difference is <= 3

    shift_count_vars_list = [num_shifts_per_worker[wid] for wid in worker_ids if wid in num_shifts_per_worker]

    if len(shift_count_vars_list) > 1:
        for i in range(len(shift_count_vars_list)):
            for j in range(i + 1, len(shift_count_vars_list)):
                worker_i_shifts = shift_count_vars_list[i]
                worker_j_shifts = shift_count_vars_list[j]

                # Calculate absolute difference in shifts
                abs_diff = model.NewIntVar(0, len(variables), f"abs_diff_{worker_ids[i]}_{worker_ids[j]}")
                diff = model.NewIntVar(-len(variables), len(variables), f"diff_{worker_ids[i]}_{worker_ids[j]}")
                model.Add(diff == worker_i_shifts - worker_j_shifts)
                model.AddAbsEquality(abs_diff, diff)

                penalty_for_pair = model.NewIntVar(0, len(variables), f"fairness_penalty_{worker_ids[i]}_{worker_ids[j]}")
                
                model.AddMaxEquality(penalty_for_pair, [abs_diff - PREFERRED_MAX_DIFFERENCE, model.NewConstant(0)])
                
                fairness_penalty_terms.append(penalty_for_pair)
    
    return fairness_penalty_terms

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
        schedule_by_day[day][shift].append({
            "position": position,
            "var_name": var_name,
            "worker_id": worker_id
        })
        worker_shift_count[worker_id] = worker_shift_count.get(worker_id, 0) + 1
    return schedule_by_day, worker_shift_count

def print_solution(schedule_by_day):
    print("📅 Final Schedule")
    for day, shifts in schedule_by_day.items():
        print(f"\n==={day}===")
        for shift, assignments in shifts.items():
            print(f"--{shift}--")
            for assignment in assignments:
                position = assignment["position"]
                worker_id = assignment["worker_id"]
                print(f"{position}: {worker_id}")

    

def add_per_shift_dummies(variables, id_to_worker):
    dummy_ids = {}
    for idx, (var_name, var_info) in enumerate(variables.items()):
        dummy_id = -(idx + 1)
        dummy_worker = {'_id': dummy_id, 'name': f'No Worker ({var_name})'}
        id_to_worker[dummy_id] = dummy_worker
        var_info['possible_workers'].append(dummy_worker)
        dummy_ids[var_name] = dummy_id
    return dummy_ids

def minimize_dummy_usage(model, variable_model, dummy_ids):
    dummy_penalty_vars = []
    for var_name, cp_var in variable_model.items():
        dummy_id_for_shift = dummy_ids.get(var_name) 
        if dummy_id_for_shift is None: 
            continue
        
        is_dummy_assigned = model.NewBoolVar(f"{var_name}_is_dummy_assigned")
        model.Add(cp_var == dummy_id_for_shift).OnlyEnforceIf(is_dummy_assigned)
        model.Add(cp_var != dummy_id_for_shift).OnlyEnforceIf(is_dummy_assigned.Not())
        
        dummy_penalty_vars.append(is_dummy_assigned) # Each dummy assignment is a penalty of 1

    return dummy_penalty_vars

def print_variable_domains(variables):
    print("=== Variable Domains (possible worker IDs for each shift) ===")
    for var_name, var_info in variables.items():
        worker_ids = [w['_id'] for w in var_info['possible_workers']]
        print(f"{var_name}: {worker_ids}")
        if not worker_ids:
            print(f"  !! WARNING: No possible workers for {var_name} !!")

def evaluate_solution_type(solver, variable_model, variables, real_workers, dummy_ids):
    total_shifts = len(variable_model)
    dummy_count = 0
    worker_limits = {
    w['_id']: sum(len(d.get('shifts',[])) for d in w.get('selectedDays', []))
    for w in real_workers if w['_id'] != DUMMY_ID}

    worker_assigned = {}

    for var_name, cp_var in variable_model.items():
        worker_id = solver.Value(cp_var)
        if worker_id not in worker_assigned:
            worker_assigned[worker_id] = 0
        worker_assigned[worker_id] += 1

        if var_name in dummy_ids and worker_id == dummy_ids[var_name]:
            dummy_count += 1
    
    print("\n📊 Solution Evaluation")
    print(f"Total shifts: {total_shifts}")
    print(f"Dummy assignments: {dummy_count}")
    if dummy_count == 0:
        print("✅ This is a full solution (no dummy workers used).")
    else:
        print("⚠️ This is a partial solution (some shifts assigned to dummy workers).")

    print("\n📋 Worker Assignment Summary:")
    for wid, assigned in worker_assigned.items():
        max_allowed = worker_limits.get(wid, 'not specific')
        print(f"🧍 Worker {wid}: assigned {assigned} shift, max allowed: {max_allowed}")


def scheduled_auto():
    db = connect()
    result = db["result"]

    update_result = result.update_many(
        {"Week": "Now"},
        {"$set": {"Week": "Old"}}
    )

    if update_result.modified_count > 0:
        print(f"🔁 Rotated: {update_result.modified_count} schedules changed from Week Now to Old")
    else:
        print("⚠️ No Week Now schedules found to rotate.")

    main()
    test_cross_week_constraint()

def no_morning_after_evening_new_schedule(model, variable_model, workers, old_schedule, variables):
    if not old_schedule:
        return
    
    saturday_evening_workers = []
    
    # מצא את כל העובדים שעבדו במשמרת ערב בשבת בשבוע הישן
    for assignment in old_schedule.get('Saturday', {}).get('Evening', []):
        worker_id = assignment.get('worker_id')
        if worker_id is not None and worker_id>0:
            saturday_evening_workers.append(worker_id)
    
    # מנע מהם לעבוד במשמרת בוקר ביום ראשון
    for var_name, var_info in variables.items():
        if var_info['day'] == 'Sunday' and var_info['shift'] == 'Morning':
            cp_var = variable_model[var_name]
            for worker_id in saturday_evening_workers:
                if worker_id in [w['_id'] for w in var_info['possible_workers']]:
                    model.Add(cp_var != worker_id)

def test_cross_week_constraint():
    print("\n🔍 check between weeks")
    
    # התחבר למונגו
    if not connect_to_mongo():
        print("❌ cant coonect to mongo")
        return
        
    db = connect()
    
    # שליפת לוח הזמנים הישן
    old_result = db["result"].find_one({"Week": "Old"})
    if not old_result or 'schedule' not in old_result:
        print("❌ didnt find old schedule ")
        return
        
    old_schedule = old_result.get('schedule')
    
    # שליפת לוח הזמנים החדש
    new_result = db["result"].find_one({"Week": "Now"})
    if not new_result or 'schedule' not in new_result:
        print("❌didnt find new schedule")
        return
        
    new_schedule = new_result.get('schedule')
    
    # מצא את העובדים שעבדו במשמרת ערב בשבת בשבוע הישן
    saturday_evening_workers = []
    if 'Saturday' in old_schedule and 'Evening' in old_schedule['Saturday']:
        for assignment in old_schedule['Saturday']['Evening']:
            worker_id = assignment.get('worker_id')
            if worker_id > 0:  # לא עובד דמה
                saturday_evening_workers.append(worker_id)
                
    if not saturday_evening_workers:
        print("ℹ️ didnt find solution")
        return
        
    print(f"👨‍💼 work in old_schedule : {saturday_evening_workers}")
    
    # בדוק אם מישהו מהם עובד במשמרת בוקר ביום ראשון בשבוע החדש
    sunday_morning_workers = []
    if 'Sunday' in new_schedule and 'Morning' in new_schedule['Sunday']:
        for assignment in new_schedule['Sunday']['Morning']:
            worker_id = assignment.get('worker_id')
            if worker_id > 0:  # לא עובד דמה
                sunday_morning_workers.append(worker_id)
                
    print(f"👨‍💼 work in the new schedule {sunday_morning_workers}")
    
    # בדוק את החפיפה בין שתי הקבוצות
    overlap = [worker for worker in saturday_evening_workers if worker in sunday_morning_workers]
    
    if not overlap:
        print("✅ its working ")
    else:
        print(f"⚠️ oh noooo {overlap} ")

def main(): # This function now ONLY runs the scheduling logic once
    print("🌟 Starting schedule generation process...")
    model = cp_model.CpModel()
    manager_id = 4 # Or get from config/args if needed for main()
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    result = run_algo(manager_id)
    if not result or 'workers' not in result or 'variables' not in result:
        print("❌ Error: Algo did not return expected data. Aborting.")
        return

    workers_data = result['workers']
    available_employee, id_to_worker = available_workers(workers_data)

    variables_input_data = result['variables']
    variables = available_shift(variables_input_data, available_employee, id_to_worker)
    
    dummy_ids_map = add_per_shift_dummies(variables, id_to_worker)
    variable_model = variables_for_shifts(variables, model)

    # Prepare real_workers list carefully
    real_workers_sources = []
    if 'shift_managers' in workers_data:
        real_workers_sources.append(workers_data['shift_managers'])
    if 'with_weapon' in workers_data:
        real_workers_sources.append(workers_data['with_weapon'])
    if 'without_weapon' in workers_data:
        real_workers_sources.append(workers_data['without_weapon'])

    raw_real_workers = [w for w_list in real_workers_sources for w in w_list if w.get('_id', DUMMY_ID -1) > 0] # ensure _id exists and is positive

    seen_ids = set()
    real_workers = []
    for worker in raw_real_workers:
        if worker['_id'] not in seen_ids:
            real_workers.append(worker)
            seen_ids.add(worker['_id'])
    
    if not real_workers:
        print("⚠️ Warning: No real workers found after processing. Check worker data.")
        # Decide if you want to proceed or abort if no real workers

    old_schedule = None
    if connect_to_mongo(): # Ensure this doesn't try to connect if already connected
        db = connect() # Ensure connect() is efficient
        old_result = db["result"].find_one({"Week": "Old"})
        if old_result:
            old_schedule = old_result.get('schedule')
            if old_schedule:
                print("📄 Found old schedule to consider for cross-week constraints.")
            else:
                print("📄 Old schedule record found, but no 'schedule' field. Proceeding without it.")
        else:
            print("📄 No 'Old' week schedule found. Proceeding without cross-week constraints based on old schedule.")
    else:
        print("⚠️ Could not connect to MongoDB to fetch old schedule.")


    one_shift_per_day(variables, model, real_workers, variable_model, days)
    at_least_one_day_off(variables, model, real_workers, variable_model, days)
    no_morning_after_evening(variables, model, real_workers, variable_model, days)
    if old_schedule: # Only add this constraint if old_schedule was successfully fetched
        no_morning_after_evening_new_schedule(model, variable_model, real_workers, old_schedule, variables)
    
    dummy_penalty_terms = minimize_dummy_usage(model, variable_model, dummy_ids_map)
    fairness_penalty_terms = fairness_constraint(variables, model, real_workers, variable_model)

    DUMMY_PENALTY_WEIGHT = 100
    FAIRNESS_PENALTY_WEIGHT = 1

    objective_terms = []
    for term in dummy_penalty_terms:
        objective_terms.append(term * DUMMY_PENALTY_WEIGHT)
    for term in fairness_penalty_terms:
        objective_terms.append(term * FAIRNESS_PENALTY_WEIGHT)

    if objective_terms:
        model.Minimize(sum(objective_terms))
    else:
        print("🤔 No objective terms defined. Solver will seek any feasible solution.")

    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = True # Good for seeing what the solver is doing
    solver.parameters.max_time_in_seconds = 60.0 # Example: Set a time limit

    print("\n🔄 Solving the model...")
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print(f"\n✅ Solution found! Status: {solver.StatusName(status)}")
        schedule_by_day, worker_shift_counts = solution_by_day(solver, variable_model, variables, days)
        print_solution(schedule_by_day)
        evaluate_solution_type(solver, variable_model, variables, real_workers, dummy_ids_map)

        if connect_to_mongo():
            db = connect() # Get DB connection
            partial_notes = []
            # ... (your logic for partial_notes as before)
            for day_name, shifts_in_day in schedule_by_day.items():
                for shift_name, assignments_in_shift in shifts_in_day.items():
                    for assignment in assignments_in_shift:
                        var_name = assignment['var_name']
                        assigned_id = assignment['worker_id']
                        position = assignment['position']
                        
                        if var_name in dummy_ids_map and assigned_id == dummy_ids_map[var_name]:
                            is_supervisor = "supervisor" in position.lower() # More robust check
                            weapon_required = variables[var_name].get("required_weapon", False)
                            partial_notes.append({
                                "shift": f"{day_name} {shift_name}",
                                "position": position,
                                "weapon": weapon_required or is_supervisor
                            })
            status_label = "partial" if partial_notes else "full"
            result_doc = {
                "hotelName": result.get("hotel", {}).get("name", "Unknown Hotel"), # Safer access
                "generatedAt": datetime.now(),
                "schedule": schedule_by_day,
                "status": status_label,
                "notes": partial_notes,
                "Week": "Now"
            }
            try:
                db["result"].insert_one(result_doc)
                print("🗂️ Schedule saved to MongoDB (collection: result)")
            except Exception as e:
                print(f"❌ Error saving schedule to MongoDB: {e}")
            
            # test_cross_week_constraint is called after saving the "Now" schedule
            # so it can compare the newly saved "Now" with "Old"
            test_cross_week_constraint() 
        else:
            print("⚠️ Could not connect to MongoDB to save results.")
    else:
        print(f"\n❌ No solution found. Solver status: {solver.StatusName(status)}")
        if status == cp_model.MODEL_INVALID:
            print("🔍 Model is invalid. Validation error: ")
            print(model.Validate()) # This can give more detailed errors
            # Consider printing variable domains or other debugging info
            # print_variable_domains(variables)

    print("🌟 Schedule generation process finished.")

# scheduled_auto() function remains the same
def scheduled_auto():
    print(f"🕰️ Scheduled task started at {datetime.now()}")
    db = connect() # Ensure connect() is efficient
    if not db:
        print("❌ Cannot connect to MongoDB for scheduled task. Aborting.")
        return

    result_collection = db["result"]

    try:
        update_result = result_collection.update_many(
            {"Week": "Now"},
            {"$set": {"Week": "Old"}}
        )
        if update_result.modified_count > 0:
            print(f"🔁 Rotated: {update_result.modified_count} schedules changed from Week Now to Old")
        else:
            print("ℹ️ No 'Week: Now' schedules found to rotate to 'Old'.")
    except Exception as e:
        print(f"❌ Error rotating schedules in MongoDB: {e}")
        return # Stop if rotation fails

    main() # Call the main scheduling logic
    # test_cross_week_constraint() is now called at the end of main()
    print(f"🕰️ Scheduled task finished at {datetime.now()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shift Scheduler")
    parser.add_argument("--mode", choices=["manual", "auto"], default="manual", help="Run mode: manual or auto")
    args = parser.parse_args()

    if args.mode == "manual":
        print("🚀 Manual mode: Running main() once.")
        main()

    elif args.mode == "auto":
        schedule.every().sunday.at("18:34").do(scheduled_auto)
        print("⏳ Auto mode active. Will run every Saturday at 20:30.")
        while True:
            schedule.run_pending()
            time.sleep(60)

    
   