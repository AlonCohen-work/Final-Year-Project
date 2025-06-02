from ortools.sat.python import cp_model
from Algo import run_algo, available_workers
from OrTools import available_shift, variables_for_shifts, print_possible_workers_per_shift
from datetime import datetime, timedelta
from MongoConnection import connect_to_mongo, mongo_db, connect

import schedule
import time
import argparse

DUMMY_ID = -1

def one_shift_per_day(variables, model, workers, variable_model, days):
    for worker in workers:
        worker_id = worker['_id']
        if worker_id == DUMMY_ID:
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
    worker_ids = [w['_id'] for w in workers if w['_id'] != DUMMY_ID]
    availability_limits = {w['_id']: sum(len(day['shifts']) for day in w.get('selectedDays', [])) for w in workers if w['_id'] != DUMMY_ID}

    worker_shifts = {wid: [] for wid in worker_ids}
    for var_name, var_info in variables.items():
        for worker_id in worker_ids:
            if worker_id in [w['_id'] for w in var_info['possible_workers']]:
                cp_var = variable_model[var_name]
                is_assigned = model.NewBoolVar(f"{var_name}_assigned_to_{worker_id}_fairness")
                model.Add(cp_var == worker_id).OnlyEnforceIf(is_assigned)
                model.Add(cp_var != worker_id).OnlyEnforceIf(is_assigned.Not())
                worker_shifts[worker_id].append(is_assigned)

    shift_sums = {}
    for wid in worker_ids:
        var = model.NewIntVar(0, availability_limits.get(wid, len(variables)), f"shifts_for_{wid}")
        model.Add(var == sum(worker_shifts[wid]))
        max_allowed = availability_limits.get(wid, len(variables))
        model.Add(var <= max_allowed)
        shift_sums[wid] = var

    shift_sum_list = list(shift_sums.values())
    for i in range(len(shift_sum_list)):
        for j in range(i + 1, len(shift_sum_list)):
            diff = model.NewIntVar(-len(variables), len(variables), f"diff_{i}_{j}")
            model.Add(diff == shift_sum_list[i] - shift_sum_list[j])
            model.AddAbsEquality(model.NewIntVar(0, len(variables), f"abs_diff_{i}_{j}"), diff)
            model.Add(diff <= 3).OnlyEnforceIf(model.NewBoolVar(f"fair_soft_{i}_{j}"))
            model.Add(diff >= -3).OnlyEnforceIf(model.NewBoolVar(f"fair_soft_{j}_{i}"))

def prevent_sunday_morning_after_saturday_evening_last_week(variables, model, variable_model, workers_to_restrict):
    if not workers_to_restrict:
        print(" No workers to restrict for Sunday Morning based on last week's Saturday Evening.")
        return

    print(f" Applying 'No Sunday Morning after last week Saturday Evening' constraint for workers: {workers_to_restrict}")

    for worker_id in workers_to_restrict:
        for var_name, var_info in variables.items():
            if var_name not in variable_model:
                continue

            if var_info['day'] == 'Sunday' and var_info['shift'] == 'Morning':
                original_possible_ids = [w['_id'] for w in var_info['possible_workers'] if w['_id'] > 0]

                if worker_id in original_possible_ids:
                    cp_var = variable_model[var_name]
                    model.Add(cp_var != worker_id)

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
    print(" Final Schedule")
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
    penalty_vars = []
    for var_name, cp_var in variable_model.items():
        dummy_id = dummy_ids.get(var_name)
        if dummy_id is None:
            continue
        is_dummy = model.NewBoolVar(f"{var_name}_is_dummy")
        model.Add(cp_var == dummy_id).OnlyEnforceIf(is_dummy)
        model.Add(cp_var != dummy_id).OnlyEnforceIf(is_dummy.Not())
        penalty_vars.append(is_dummy)
    model.Minimize(sum(penalty_vars))

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
    w['_id']: len(w.get('selectedDays', []))
    for w in real_workers if w['_id'] != DUMMY_ID}

    worker_assigned = {}

    for var_name, cp_var in variable_model.items():
        worker_id = solver.Value(cp_var)
        if worker_id not in worker_assigned:
            worker_assigned[worker_id] = 0
        worker_assigned[worker_id] += 1

        if var_name in dummy_ids and worker_id == dummy_ids[var_name]:
            dummy_count += 1
    
    print("\n Solution Evaluation")
    print(f"Total shifts: {total_shifts}")
    print(f"Dummy assignments: {dummy_count}")
    if dummy_count == 0:
        print(" This is a full solution (no dummy workers used).")
    else:
        print(" This is a partial solution (some shifts assigned to dummy workers).")

    print("\n Worker Assignment Summary:")
    for wid, assigned in worker_assigned.items():
        max_allowed = worker_limits.get(wid, 'unlimited')
        print(f" Worker {wid}: assigned {assigned} shift, max allowed: {max_allowed}")

def main(previous_week_schedule_data=None, run_for_manager_id=None, target_week_start_date_str=None):
    model = cp_model.CpModel()
    manager_id = run_for_manager_id if run_for_manager_id is not None else 4
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    # === Handle Target Week Date ===
    try:
        if isinstance(target_week_start_date_str, datetime):
            target_week_str = target_week_start_date_str.strftime('%Y-%m-%d')
        elif isinstance(target_week_start_date_str, str):
            target_week_str = datetime.strptime(target_week_start_date_str.strip(), '%Y-%m-%d').strftime('%Y-%m-%d')
        else:
            raise ValueError("Invalid date format")
    except Exception as e:
        print(f"[Main] Invalid or missing target week: {target_week_start_date_str}. Exception: {e}")
        return

    # === Extract workers from previous week ===
    previous_evening_workers = set()
    if previous_week_schedule_data:
        saturday_evening = previous_week_schedule_data.get("Saturday", {}).get("Evening", [])
        for assignment in saturday_evening:
            if isinstance(assignment, dict):
                worker_id = assignment.get("worker_id")
                if isinstance(worker_id, int) and worker_id > 0:
                    previous_evening_workers.add(worker_id)
        print(f"[Info] Workers identified from last week's Saturday Evening: {previous_evening_workers}" if previous_evening_workers else "[Info] No workers identified from last week's Saturday Evening shifts.")

    result = run_algo(manager_id)
    if not result:
        print(f"[Main] run_algo failed for manager {manager_id}")
        return

    workers_data = result['workers']
    available_employee, id_to_worker = available_workers(workers_data)
    variables = available_shift(result['variables'], available_employee, id_to_worker)
    dummy_ids = add_per_shift_dummies(variables, id_to_worker)
    variable_model = variables_for_shifts(variables, model)

    real_workers = (
        workers_data['shift_managers'] +
        workers_data['with_weapon'] +
        workers_data['without_weapon']
    )

    one_shift_per_day(variables, model, real_workers, variable_model, days)
    at_least_one_day_off(variables, model, real_workers, variable_model, days)
    no_morning_after_evening(variables, model, real_workers, variable_model, days)
    fairness_constraint(variables, model, real_workers, variable_model)
    prevent_sunday_morning_after_saturday_evening_last_week(variables, model, variable_model, previous_evening_workers)
    minimize_dummy_usage(model, variable_model, dummy_ids)

    # === Solve ===
    solver = cp_model.CpSolver()
    print(f"\n[Main] Solving for manager {manager_id}, week {target_week_str}...")
    status = solver.Solve(model)

    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print(f"\n❌ No solution found. Status: {solver.StatusName(status)}")
        return

    print("\n Solution found!")
    schedule_by_day, shift_counts = solution_by_day(solver, variable_model, variables, days)
    print_solution(schedule_by_day)
    evaluate_solution_type(solver, variable_model, variables, real_workers, dummy_ids)

    # === Save to MongoDB ===
    if not connect_to_mongo():
        print("[Main] Failed DB connection.")
        return

    db = connect()

    # Update all previous schedules for this hotel from 'Now' to 'Old'
    db["result"].update_many(
        {
            "hotelName": result["hotel"]["name"],
            "Week": "Now"
        },
        {
            "$set": {"Week": "Old"}
        }
    )

    partial_notes = []
    for day, shifts in schedule_by_day.items():
        for shift_type, assignments in shifts.items():
            for assignment in assignments:
                var_name = assignment['var_name']
                worker_id = assignment['worker_id']
                position = assignment['position']
                if var_name in dummy_ids and worker_id == dummy_ids[var_name]:
                    is_supervisor = position.lower() == 'shift supervisor'
                    partial_notes.append({
                        "shift": f"{day} {shift_type}",
                        "position": position,
                        "weapon": variables[var_name].get("required_weapon", False) or is_supervisor
                    })

    result_doc = {
        "hotelName": result["hotel"]["name"],
        "generatedAt": datetime.now(),
        "schedule": schedule_by_day,
        "status": "partial" if partial_notes else "full",
        "notes": partial_notes,
        "Week": "Now",
        "relevantWeekStartDate": target_week_str,
        "idToName": {str(k): v["name"] for k, v in id_to_worker.items() if "name" in v}
    }

    db["result"].replace_one(
    {
        "hotelName": result["hotel"]["name"],
        "relevantWeekStartDate": target_week_str
    },
    result_doc,
    upsert=True)
    print(f"Schedule saved to MongoDB (collection: result) for week {target_week_str}")

def scheduled_auto():
    print(f"\n--- Starting scheduled_auto run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    db = connect()
    if db is None:
        print(" [Scheduled Auto] Failed to connect to MongoDB. Aborting.")
        return

    result_collection = db["result"]
    MANAGER_ID_FOR_AUTO_RUN = 4
    manager_doc_for_hotel = db["people"].find_one({"_id": MANAGER_ID_FOR_AUTO_RUN})
    
    if not manager_doc_for_hotel or not manager_doc_for_hotel.get("Workplace"):
        print(f" [Scheduled Auto] Cannot determine hotel for auto run (Manager ID: {MANAGER_ID_FOR_AUTO_RUN}). Aborting.")
        return

    hotel_name_for_auto_run = manager_doc_for_hotel.get("Workplace")
    last_now_schedule_doc = result_collection.find_one(
        {"hotelName": hotel_name_for_auto_run, "Week": "Now"},
        sort=[("generatedAt", -1)]
    )

    previous_week_schedule_data_for_main = None
    if last_now_schedule_doc and "schedule" in last_now_schedule_doc:
        previous_week_schedule_data_for_main = last_now_schedule_doc["schedule"]
    else:
        print(f"[Info] No previous 'Now' schedule found for {hotel_name_for_auto_run}.")
    today = datetime.now()
    start_of_this_calendar_week = today - timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)
    start_of_this_calendar_week = start_of_this_calendar_week.replace(hour=0, minute=0, second=0, microsecond=0)
    target_week_for_run = start_of_this_calendar_week + timedelta(days=7)
    target_week_for_run_str = target_week_for_run.strftime('%Y-%m-%d')


    if hotel_name_for_auto_run:
        print(f"\n [Scheduled Auto] Checking worker availability freshness for hotel: '{hotel_name_for_auto_run}'...")
    

    main(
        previous_week_schedule_data=previous_week_schedule_data_for_main,
        run_for_manager_id=MANAGER_ID_FOR_AUTO_RUN,
        target_week_start_date_str=target_week_for_run_str
    )
    print(f"--- Finished scheduled_auto run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shift Scheduler Orchestrator")
    parser.add_argument("--mode", 
                        choices=["manual", "auto"], 
                        default="auto",
                        help="Run mode: 'manual' (typically triggered by API) or 'auto' (scheduled task)")
    parser.add_argument("--manager-id", 
                        type=int, 
                        help="Manager ID to run for (required if mode is manual and not called from scheduled_auto)")
    parser.add_argument("--target-week", 
                        type=str, 
                        help="Target week start date (YYYY-MM-DD) for the schedule (required if mode is manual)")
    
    args = parser.parse_args()

    if args.mode == "manual":
        print(f" Manual mode run initiated.")
        if not args.manager_id or not args.target_week:
            manual_manager_id = args.manager_id if args.manager_id else 4
            
            manual_target_week = args.target_week
            if not manual_target_week:
                today_manual = datetime.now()
                start_of_this_week_manual = today_manual - timedelta(days=today_manual.weekday() + 1 if today_manual.weekday() != 6 else 0)
                start_of_this_week_manual = start_of_this_week_manual.replace(hour=0, minute=0, second=0, microsecond=0)
                manual_target_week_dt = start_of_this_week_manual + timedelta(days=7)
                manual_target_week = manual_target_week_dt.strftime('%Y-%m-%d')
                print(f"Defaulting target week to: {manual_target_week}")

            db_manual = connect()
            prev_data_manual = None
            if db_manual is not None:
                manager_for_prev_data = db_manual["people"].find_one({"_id": manual_manager_id})
                if manager_for_prev_data and manager_for_prev_data.get("Workplace"):
                    hotel_for_prev_data = manager_for_prev_data.get("Workplace")
                    last_old = db_manual["result"].find_one(
                        {"hotelName": hotel_for_prev_data, "Week": "Old"},
                        sort=[("generatedAt", -1)]
                    )
                    if not last_old:
                        last_old = db_manual["result"].find_one(
                            {"hotelName": hotel_for_prev_data, "Week": "Now"},
                            sort=[("generatedAt", -1)]
                        )
                    if last_old and last_old.get("schedule"):
                        prev_data_manual = last_old.get("schedule")
                      

            main(previous_week_schedule_data=prev_data_manual,
                 run_for_manager_id=manual_manager_id, 
                 target_week_start_date_str=manual_target_week)
        else:
            main(run_for_manager_id=args.manager_id, 
                 target_week_start_date_str=args.target_week)

    elif args.mode == "auto":
        schedule.every().sunday.at("02:00").do(scheduled_auto)
        print(f" Auto mode active. Scheduler started. Next run: {schedule.next_run()}")
        while True:
            schedule.run_pending()
            time.sleep(30)
# cd Python
# python Constraints.py --mode auto     