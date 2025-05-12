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
                # מגבלת שיבוץ לפי כמות המשמרות שביקש
        max_allowed = availability_limits.get(wid, len(variables))
        model.Add(var <= max_allowed)
        shift_sums[wid] = var

    shift_sum_list = list(shift_sums.values())
    for i in range(len(shift_sum_list)):
        for j in range(i + 1, len(shift_sum_list)):
            diff = model.NewIntVar(-len(variables), len(variables), f"diff_{i}_{j}")
            model.Add(diff == shift_sum_list[i] - shift_sum_list[j])
            model.AddAbsEquality(model.NewIntVar(0, len(variables), f"abs_diff_{i}_{j}"), diff)
            #// Soft fairness - try to keep shifts close, but not enforced
            model.Add(diff <= 3).OnlyEnforceIf(model.NewBoolVar(f"fair_soft_{i}_{j}"))
            model.Add(diff >= -3).OnlyEnforceIf(model.NewBoolVar(f"fair_soft_{j}_{i}"))

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
    
    print("\n📊 Solution Evaluation")
    print(f"Total shifts: {total_shifts}")
    print(f"Dummy assignments: {dummy_count}")
    if dummy_count == 0:
        print("✅ This is a full solution (no dummy workers used).")
    else:
        print("⚠️ This is a partial solution (some shifts assigned to dummy workers).")

    print("\n📋 Worker Assignment Summary:")
    for wid, assigned in worker_assigned.items():
        max_allowed = worker_limits.get(wid, '∞')
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



def main():
    model = cp_model.CpModel()
    manager_id = 4
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    result = run_algo(manager_id)
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
    minimize_dummy_usage(model, variable_model, dummy_ids)

    solver = cp_model.CpSolver()
    print("\n🔄 Solving the model...")
    print_variable_domains(variables)

    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print("\n✅ Solution found!")
        schedule_by_day, worker_shift_counts = solution_by_day(solver, variable_model, variables, days)
        print_solution(schedule_by_day)
        evaluate_solution_type(solver, variable_model, variables, real_workers, dummy_ids)

        # 🔄 שמירה למונגו
        if connect_to_mongo():
            partial_notes = []
            for day, shifts in schedule_by_day.items():
                for shift, assignments in shifts.items():
                    for assignment in assignments:
                        var_name = assignment['var_name']
                        assigned_id = assignment['worker_id']
                        position = assignment['position']

                     
                        is_supervisor = position.lower() == "shift supervisor"


                    if var_name in dummy_ids and assigned_id == dummy_ids[var_name]:
                        partial_notes.append({
                            "shift": f"{day} {shift}",
                            "position": position,
                            "weapon": variables[var_name].get("required_weapon", False) or is_supervisor
                         })

            status_label = "partial" if partial_notes else "full"

            result_doc = {
                "hotelName": result["hotel"]["name"],
                "generatedAt": datetime.now(),
                "schedule": schedule_by_day,
                "status": status_label,
                "notes": partial_notes,
                "Week": "Now"
            }

            db = connect()
            db["result"].insert_one(result_doc)
            print("🗂️ Schedule saved to MongoDB (collection: result)")

    else:
        print("\n❌ No solution found.")

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