# --- START OF FILE Constraints.py ---

import logging
import argparse
import time
from datetime import datetime, timedelta

# Import third-party libraries
try:
    from ortools.sat.python import cp_model
    import schedule
except ImportError as e:
    print(f"Error: Missing required library. Please install it using pip. Details: {e}")
    exit(1)

# Import custom modules
from Algo import run_algo, available_workers
from OrTools import available_shift, variables_for_shifts
from MongoConnection import connect_to_mongo, connect

# --- Logging Setup ---
# This basic configuration will log to the console.
# For production, you might want to configure logging to a file.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s'
)
# Get a logger instance for this module
logger = logging.getLogger(__name__)

# A constant to represent an unassigned shift in the model
DUMMY_ID = -1

# ==============================================================================
# --- CONSTRAINT FUNCTIONS ---
# These functions define the rules of the schedule. Their internal logic is
# preserved from the original version.
# ==============================================================================

def one_shift_per_day(variables, model, workers, variable_model, days):
   # """Constraint: Ensures each worker is assigned to at most one shift per day."""
    for worker in workers:
        worker_id = worker['_id']
        if worker_id == DUMMY_ID:
            continue
        for day in days:
            daily_assignments = []
            for var_name, var_info in variables.items():
                if var_info['day'] == day and worker_id in [w['_id'] for w in var_info['possible_workers']]:
                    cp_var = variable_model[var_name]
                    assigned = model.NewBoolVar(f"{var_name}_assigned_to_{worker_id}")
                    model.Add(cp_var == worker_id).OnlyEnforceIf(assigned)
                    model.Add(cp_var != worker_id).OnlyEnforceIf(assigned.Not())
                    daily_assignments.append(assigned)
            if daily_assignments:
                model.Add(sum(daily_assignments) <= 1)


def at_least_one_day_off(variables, model, workers, variable_model, days):
    #"""Constraint: Ensures each worker has at least one day off in the 7-day week (works max 6 days)."""
    for worker in workers:
        worker_id = worker['_id']
        if worker_id == DUMMY_ID:
            continue
        works_day_list = []
        for day in days:
            daily_assignments = []
            for var_name, var_info in variables.items():
                if var_info['day'] == day and worker_id in [w['_id'] for w in var_info['possible_workers']]:
                    cp_var = variable_model[var_name]
                    assigned = model.NewBoolVar(f"{var_name}_assigned_to_{worker_id}_for_dayoff")
                    model.Add(cp_var == worker_id).OnlyEnforceIf(assigned)
                    model.Add(cp_var != worker_id).OnlyEnforceIf(assigned.Not())
                    daily_assignments.append(assigned)
            
            if daily_assignments:
                works_that_day = model.NewBoolVar(f"worker_{worker_id}_works_on_{day}")
                model.AddMaxEquality(works_that_day, daily_assignments)
                works_day_list.append(works_that_day)
        
        if works_day_list:
            model.Add(sum(works_day_list) <= 6)

def no_morning_after_evening(variables, model, workers, variable_model, days):
    #"""Constraint: Prevents a worker from being assigned to a morning shift the day after an evening shift."""
    for worker in workers:
        worker_id = worker['_id']
        if worker_id == DUMMY_ID:
            continue
            
        for i in range(len(days) - 1):
            evening_day = days[i]
            morning_day = days[i + 1]
            
            # Create boolean variables for each possible assignment in the evening
            evening_bools = []
            for var_name, var_info in variables.items():
                if var_info['day'] == evening_day and var_info['shift'] == 'Evening':
                    if worker_id in [w['_id'] for w in var_info['possible_workers']]:
                        is_assigned = model.NewBoolVar(f"worker_{worker_id}_in_{var_name}_evening")
                        model.Add(variable_model[var_name] == worker_id).OnlyEnforceIf(is_assigned)
                        model.Add(variable_model[var_name] != worker_id).OnlyEnforceIf(is_assigned.Not())
                        evening_bools.append(is_assigned)

            # Create boolean variables for each possible assignment in the morning
            morning_bools = []
            for var_name, var_info in variables.items():
                if var_info['day'] == morning_day and var_info['shift'] == 'Morning':
                     if worker_id in [w['_id'] for w in var_info['possible_workers']]:
                        is_assigned = model.NewBoolVar(f"worker_{worker_id}_in_{var_name}_morning")
                        model.Add(variable_model[var_name] == worker_id).OnlyEnforceIf(is_assigned)
                        model.Add(variable_model[var_name] != worker_id).OnlyEnforceIf(is_assigned.Not())
                        morning_bools.append(is_assigned)

            if evening_bools and morning_bools:
                # `works_evening` is true if the worker is assigned to ANY of the evening shifts.
                works_evening = model.NewBoolVar(f"worker_{worker_id}_works_{evening_day}_evening")
                model.AddBoolOr(evening_bools).OnlyEnforceIf(works_evening)

                # ** THE FIX IS HERE **
                # Instead of AddImplication(works_evening.Not(), model.AddBoolAnd(...)),
                # we create direct implications for each boolean variable.
                for b in evening_bools:
                    # This says: If the worker does NOT work any evening shift (works_evening is False),
                    # then they must not be assigned to this specific evening shift (b is False).
                    model.AddImplication(works_evening.Not(), b.Not())
                
                # `works_morning` is true if the worker is assigned to ANY of the next morning shifts.
                works_morning = model.NewBoolVar(f"worker_{worker_id}_works_{morning_day}_morning")
                model.AddBoolOr(morning_bools).OnlyEnforceIf(works_morning)

                for b in morning_bools:
                    # Same logic for morning shifts.
                    model.AddImplication(works_morning.Not(), b.Not())
                
                # The core constraint remains the same and is correct:
                # If they work in the evening, they cannot work the next morning.
                model.AddImplication(works_evening, works_morning.Not())

def fairness_constraint(variables, model, workers, variable_model):
    #"""Constraint: Attempts to balance the number of shifts assigned to each worker."""
    worker_ids = [w['_id'] for w in workers if w['_id'] != DUMMY_ID]
    if len(worker_ids) < 2:
        return # No need for fairness with one or zero workers

    shift_counts = {}
    for worker_id in worker_ids:
        num_shifts = model.NewIntVar(0, len(variables), f"shifts_for_{worker_id}")
        assigned_bools = []
        for var_name, cp_var in variable_model.items():
             if worker_id in [w['_id'] for w in variables[var_name]['possible_workers']]:
                is_assigned = model.NewBoolVar(f"{var_name}_assigned_to_{worker_id}_fairness")
                model.Add(cp_var == worker_id).OnlyEnforceIf(is_assigned)
                model.Add(cp_var != worker_id).OnlyEnforceIf(is_assigned.Not())
                assigned_bools.append(is_assigned)
        
        model.Add(num_shifts == sum(assigned_bools))
        shift_counts[worker_id] = num_shifts

    # Add constraints on the difference between shift counts of any two workers
    shift_counts_list = list(shift_counts.values())
    for i in range(len(shift_counts_list)):
        for j in range(i + 1, len(shift_counts_list)):
            diff = shift_counts_list[i] - shift_counts_list[j]
            # This is a soft constraint; the difference should be at most 3.
            model.Add(-3 <= diff)
            model.Add(diff <= 3)

def prevent_sunday_morning_after_saturday_evening_last_week(variables, model, variable_model, workers_to_restrict):
    #"""Constraint: Prevents workers who worked Sat evening last week from working Sun morning this week."""
    if not workers_to_restrict:
        logger.info("No workers from last week's Sat evening to restrict for Sun morning.")
        return

    logger.info(f"Applying 'No Sun Morning' constraint for workers: {workers_to_restrict}")
    for worker_id in workers_to_restrict:
        for var_name, var_info in variables.items():
            if var_info['day'] == 'Sunday' and var_info['shift'] == 'Morning':
                if worker_id in [w['_id'] for w in var_info['possible_workers']]:
                    model.Add(variable_model[var_name] != worker_id)

# ==============================================================================
# --- SOLUTION PROCESSING & DUMMY MANAGEMENT ---
# ==============================================================================

def solution_by_day(solver, variable_model, variables, days):
    #"""Structures the solved schedule by day and shift for easier use."""
    shifts = ['Morning', 'Afternoon', 'Evening']
    schedule_by_day = {day: {shift: [] for shift in shifts} for day in days}
    for var_name, var in variable_model.items():
        info = variables[var_name]
        day, shift, position = info['day'], info['shift'], info['position']
        worker_id = solver.Value(var)
        schedule_by_day[day][shift].append({"position": position, "var_name": var_name, "worker_id": worker_id})
    return schedule_by_day

def print_solution(schedule_by_day, id_to_name_map):
    #"""Logs the final schedule to the console in a readable format."""
    logger.info("--- Final Generated Schedule ---")
    for day, shifts in schedule_by_day.items():
        day_str = f"\n=== {day.upper()} ==="
        has_assignments = False
        for shift, assignments in shifts.items():
            if not assignments: continue
            
            day_str += f"\n  -- {shift} --"
            has_assignments = True
            for assignment in assignments:
                worker_name = id_to_name_map.get(str(assignment["worker_id"]), f"Unknown ID {assignment['worker_id']}")
                day_str += f"\n    {assignment['position']:<20}: {worker_name}"
        
        if has_assignments:
            logger.info(day_str)

def add_per_shift_dummies(variables, id_to_worker):
    #"""Creates a unique dummy worker for each shift to ensure a solution can always be found."""
    dummy_ids = {}
    for idx, (var_name, var_info) in enumerate(variables.items()):
        dummy_id = -(idx + 1) # Use unique negative IDs
        dummy_worker = {'_id': dummy_id, 'name': f'Dummi ({var_name})'}
        # This modification happens in-place
        var_info['possible_workers'].append(dummy_worker)
        id_to_worker[dummy_id] = dummy_worker
        dummy_ids[var_name] = dummy_id
    return dummy_ids

def minimize_dummy_usage(model, variable_model, dummy_ids):
    #"""Adds an objective to the model to minimize the use of dummy workers."""
    penalty_vars = []
    for var_name, cp_var in variable_model.items():
        if var_name in dummy_ids:
            is_dummy = model.NewBoolVar(f"{var_name}_is_dummy")
            model.Add(cp_var == dummy_ids[var_name]).OnlyEnforceIf(is_dummy)
            model.Add(cp_var != dummy_ids[var_name]).OnlyEnforceIf(is_dummy.Not())
            penalty_vars.append(is_dummy)
    model.Minimize(sum(penalty_vars))

# ==============================================================================
# --- MAIN ORCHESTRATION FUNCTION ---
# ==============================================================================

def main(previous_week_schedule_data=None, run_for_manager_id=None, target_week_start_date_str=None):
    #"""The main function that orchestrates the entire scheduling process."""
    try:
        model = cp_model.CpModel()
        manager_id = run_for_manager_id if run_for_manager_id is not None else 4
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

        # === 1. Data Fetching and Preparation ===
        logger.info(f"Running for Manager ID: {manager_id}, Target Week: {target_week_start_date_str}")
        result = run_algo(manager_id)
        if not result:
            logger.critical(f"run_algo failed. Cannot retrieve essential data. Aborting.")
            return

        workers_data = result['workers']
        available_employee, id_to_worker = available_workers(workers_data)
        variables = available_shift(result['variables'], available_employee, id_to_worker)
        
        dummy_ids = add_per_shift_dummies(variables, id_to_worker)
        variable_model = variables_for_shifts(variables, model)

        if not variable_model:
            logger.critical("No variables were created for the model. Check hotel schedule definition. Aborting.")
            return

        real_workers = workers_data['shift_managers'] + workers_data['with_weapon'] + workers_data['without_weapon']
        
        # === 2. Applying Constraints ===
        logger.info("Applying constraints to the model...")
        one_shift_per_day(variables, model, real_workers, variable_model, days)
        at_least_one_day_off(variables, model, real_workers, variable_model, days)
        no_morning_after_evening(variables, model, real_workers, variable_model, days)
        fairness_constraint(variables, model, real_workers, variable_model)
        
        previous_evening_workers = set()
        if previous_week_schedule_data:
            saturday_evening = previous_week_schedule_data.get("Saturday", {}).get("Evening", [])
            for assignment in saturday_evening:
                if isinstance(assignment, dict) and assignment.get("worker_id", 0) > 0:
                    previous_evening_workers.add(assignment["worker_id"])
        
        prevent_sunday_morning_after_saturday_evening_last_week(variables, model, variable_model, previous_evening_workers)
        minimize_dummy_usage(model, variable_model, dummy_ids)
        logger.info("All constraints and objective function have been applied.")

        # === 3. Solving the Model ===
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 60.0 # Safety timeout for the solver
        status = solver.Solve(model)

        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            logger.error(f"❌ No solution found. Solver status: {solver.StatusName(status)}. The problem might be over-constrained.")
            return

        # === 4. Processing and Saving the Solution ===
        logger.info(f"✅ Solution found! Solver status: {solver.StatusName(status)}.")
        id_to_name_map = {str(k): v.get("name", "Unknown") for k, v in id_to_worker.items()}
        schedule_by_day = solution_by_day(solver, variable_model, variables, days)
        print_solution(schedule_by_day, id_to_name_map)
        
        db = connect()
        if db is None: 
            logger.error("Failed to connect to DB. Solution will not be saved.")
            return
        
        try:
            logger.info("Saving solution to MongoDB...")
            hotel_name = result["hotel"]["name"]
            
            db["result"].update_many({"hotelName": hotel_name, "Week": "Now"}, {"$set": {"Week": "Old"}})

            # Identify unassigned shifts for the 'notes' field
            partial_notes = []
            for day, shifts in schedule_by_day.items():
                for shift, assignments in shifts.items():
                    for assignment in assignments:
                        if assignment['worker_id'] < 0: # Dummies have negative IDs
                            partial_notes.append({"shift": f"{day} {shift}", "position": assignment['position']})

            # Increment the relevantWeekStartDate by one day
            relevant_week_start_date = datetime.strptime(target_week_start_date_str, "%Y-%m-%d") + timedelta(days=1)
            relevant_week_start_date_str_plus1 = relevant_week_start_date.strftime("%Y-%m-%d")

            result_doc = {
                "hotelName": hotel_name,
                "generatedAt": datetime.now(),
                "schedule": schedule_by_day,
                "status": "partial" if partial_notes else "full",
                "notes": partial_notes,
                "Week": "Now",
                "relevantWeekStartDate": relevant_week_start_date_str_plus1,
                "idToName": id_to_name_map
            }

            db["result"].replace_one(
                {"hotelName": hotel_name, "relevantWeekStartDate": relevant_week_start_date_str_plus1},
                result_doc,
                upsert=True
            )
            logger.info(f"Successfully saved schedule to MongoDB for week starting {target_week_start_date_str}.")

        except Exception as e:
            logger.error(f"Failed to save solution to MongoDB: {e}", exc_info=True)

    except Exception as e:
        logger.critical(f"A critical, unhandled error occurred in the main function: {e}", exc_info=True)

# ==============================================================================
# --- SCHEDULED RUN AND COMMAND-LINE INTERFACE ---
# ==============================================================================

def scheduled_auto():
    """Function designed to be run on a schedule (e.g., weekly)."""
    logger.info(f"--- Starting AUTONOMOUS scheduled run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    db = connect()
    if not db:
        logger.error("[Scheduled Auto] Failed to connect to MongoDB. Aborting run.")
        return

    # In a real-world app, this might loop through all hotels or be configured elsewhere
    MANAGER_ID_FOR_AUTO_RUN = 4
    
    try:
        manager_doc = db["people"].find_one({"_id": MANAGER_ID_FOR_AUTO_RUN})
        if not manager_doc or not manager_doc.get("Workplace"):
            logger.error(f"[Scheduled Auto] Cannot find hotel for Manager ID: {MANAGER_ID_FOR_AUTO_RUN}. Aborting.")
            return

        hotel_name = manager_doc["Workplace"]
        last_now_schedule = db["result"].find_one({"hotelName": hotel_name, "Week": "Now"}, sort=[("generatedAt", -1)])
        
        # Determine the start date for the upcoming week's schedule
        today = datetime.now()
        start_of_current_week = today - timedelta(days=today.weekday()) # Sunday as start of week
        target_week_start_date = start_of_current_week + timedelta(days=7)
        target_week_str = target_week_start_date.strftime('%Y-%m-%d')

        main(
            previous_week_schedule_data=last_now_schedule.get("schedule") if last_now_schedule else None,
            run_for_manager_id=MANAGER_ID_FOR_AUTO_RUN,
            target_week_start_date_str=target_week_str
        )
    except Exception as e:
        logger.error(f"[Scheduled Auto] An error occurred during the scheduled run: {e}", exc_info=True)
    
    logger.info(f"--- Finished AUTONOMOUS scheduled run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shift Scheduler Orchestrator")
    parser.add_argument("--mode", choices=["manual", "auto"], default="manual", help="Run mode")
    parser.add_argument("--manager-id", type=int, help="Manager ID for manual run")
    parser.add_argument("--target-week", type=str, help="Target week start date (YYYY-MM-DD) for manual run")
    args = parser.parse_args()

    if args.mode == "manual":
        logger.info("--- MANUAL mode run initiated ---")
        manual_manager_id = args.manager_id if args.manager_id else 4
        
        if args.target_week:
            manual_target_week = args.target_week
        else:
            # Default to the next full week if not specified
            today = datetime.now()
            start_of_current_week = today - timedelta(days=today.weekday())
            manual_target_week_dt = start_of_current_week + timedelta(days=7)
            manual_target_week = manual_target_week_dt.strftime('%Y-%m-%d')
            logger.info(f"Target week not specified, defaulting to next week: {manual_target_week}")
        

        db = connect()
        prev_data = None
        if db is not None:
            try:
                manager_doc = db["people"].find_one({"_id": manual_manager_id})
                if manager_doc and manager_doc.get("Workplace"):
                    hotel_name = manager_doc.get("Workplace")
                    last_schedule = db["result"].find_one({"hotelName": hotel_name}, sort=[("generatedAt", -1)])
                    if last_schedule:
                        prev_data = last_schedule.get("schedule")
                        logger.info(f"Found previous schedule data from {last_schedule.get('generatedAt')}")
            except Exception as e:
                logger.error(f"Could not fetch previous schedule data: {e}", exc_info=True)

        main(
            previous_week_schedule_data=prev_data,
            run_for_manager_id=manual_manager_id, 
            target_week_start_date_str=manual_target_week
        )

    elif args.mode == "auto":
        # This will run the task once. For continuous running, a loop is needed.
        # schedule.every().sunday.at("02:00").do(scheduled_auto)
        logger.info("--- AUTO mode initiated. Setting up scheduler... ---")
        logger.info(f"Scheduler active. Next run at: {schedule.next_run()}")
        while True:
            try:
                schedule.run_pending()
                time.sleep(30)
            except KeyboardInterrupt:
                logger.info("Scheduler stopped manually.")
                break
            except Exception as e:
                logger.error(f"An error occurred in the scheduler loop: {e}", exc_info=True)
                time.sleep(60) # Wait a bit longer after an error