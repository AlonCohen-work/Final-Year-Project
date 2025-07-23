# --- START OF FILE Algo.py ---

from MongoConnection import getData
import logging

logger = logging.getLogger(__name__)

def run_algo(user_id):    
    """
    Fetches data and creates the initial "variables" for the scheduling problem.
    Each variable represents a single shift slot that needs to be filled.
    """
    logger.info(f"Starting run_algo for user_id: {user_id}")
    data = getData(user_id)
    
    if data is None:
        logger.error(f"Could not retrieve data for user_id {user_id}. Aborting run_algo.")
        return None
    
    try:
        hotel_schedule = data["hotel"]["schedule"]
        shift_managers = data["workers"]["shift_managers"]
        with_weapon = data["workers"]["with_weapon"]
        without_weapon = data["workers"]["without_weapon"]

        variables = {}
        # Loop through the schedule defined for the hotel to create a variable for each slot.
        for shift, positions in hotel_schedule.items():
            for position, days in positions.items():
                for day, requirements in days.items():
                    # Create a variable for the shift supervisor role
                    if position == "Shift Supervisor":
                        var_name = f'{shift}_{position}_{day}'
                        variables[var_name] = {
                            "shift": shift, "position": position, "day": day,
                            "possible_workers": shift_managers
                        }
                    # Create variables for other roles based on weapon needs
                    else:
                        weapon_needed = requirements.get("weapon", 0)
                        no_weapon_needed = requirements.get("noWeapon", 0)

                        for i in range(weapon_needed):
                            var_name = f"{shift}_{position}_{day}_weapon{i}"
                            variables[var_name] = {
                                "shift": shift, "position": position, "day": day, "required_weapon": True,
                                "possible_workers": shift_managers + with_weapon
                            }
                        
                        for i in range(no_weapon_needed):
                            var_name = f"{shift}_{position}_{day}_noweapon{i}"
                            variables[var_name] = {
                                "shift": shift, "position": position, "day": day, "required_weapon": False,
                                "possible_workers": without_weapon + shift_managers + with_weapon
                            }

        logger.info(f"Successfully created {len(variables)} shift variables.")
        return {
            "variables": variables,
            "workers": data["workers"],
            "hotel": data["hotel"]
        }
    except KeyError as e:
        logger.error(f"Missing expected key in data structure from getData: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred in run_algo: {e}", exc_info=True)
        return None

def available_workers(workers):
    """
    Processes worker data to create a lookup structure for availability.
    Result: {day: {shift: {qualification: [worker_id]}}}
    Also returns a map of worker_id to the full worker object.
    """
    logger.info("Processing worker availability...")
    available_employee = {}
    id_to_worker = {}
    
    try:
        all_worker_groups = [
            workers.get("shift_managers", []),
            workers.get("with_weapon", []),
            workers.get("without_weapon", [])
        ]

        for worker_group in all_worker_groups:
            for worker in worker_group:
                worker_id = worker['_id']
                if worker_id not in id_to_worker:
                    id_to_worker[worker_id] = worker
                
                for day_info in worker.get("selectedDays", []):
                    day = day_info.get("day")
                    if not day: continue

                    for shift in day_info.get("shifts", []):
                        # setdefault is a clean way to initialize nested dicts
                        shift_availability = available_employee.setdefault(day, {}).setdefault(shift, {
                            "with_weapon": set(), "without_weapon": set(), "shift_managers": set()
                        })
                        
                        is_manager = worker.get("ShiftManager", False)
                        has_weapon = worker.get("WeaponCertified", False)
                        
                        # Add worker ID to all categories they are qualified for. Using sets to handle duplicates automatically.
                        if is_manager:
                            shift_availability["shift_managers"].add(worker_id)
                            shift_availability["with_weapon"].add(worker_id)
                            shift_availability["without_weapon"].add(worker_id)
                        elif has_weapon:
                            shift_availability["with_weapon"].add(worker_id)
                            shift_availability["without_weapon"].add(worker_id)
                        else:
                            shift_availability["without_weapon"].add(worker_id)

        # Convert sets back to lists for consistent data structure
        for day, shifts in available_employee.items():
            for shift, categories in shifts.items():
                for category, worker_ids_set in categories.items():
                    available_employee[day][shift][category] = list(worker_ids_set)
        
        logger.info("Successfully processed worker availability.")
        return available_employee, id_to_worker
    except Exception as e:
        logger.error(f"An error occurred while processing available_workers: {e}", exc_info=True)
        return {}, {}