# --- START OF FILE Algo.py ---

from MongoConnection import getData

# Function to run the algorithm and create variables for each shift, position, and day
# This function retrieves data for a specific user (manager) and constructs a set of variables
def run_algo(user_id):    
    data = getData(user_id)
    
    if data is None:
        print("Manager not found")
        return 
   
    # Store the retrieved data in separate variables for clarity
    hotel_schedule = data["hotel"]["schedule"]
    shift_managers = data["workers"]["shift_managers"]
    with_weapon = data["workers"]["with_weapon"]
    without_weapon = data["workers"]["without_weapon"]

    variables = {}
    # Loop through each shift, position, and day to create a variable for each required slot.
    # These variables represent the individual shifts that need to be filled.
    for shift, positions in hotel_schedule.items():
        for position, days in positions.items():
            for day, requirements in days.items():
                if position == "Shift Supervisor":
                    var_name = f'{shift}_{position}_{day}'
                    variables[var_name] = {
                        "shift": shift,
                        "position": position,
                        "day": day,
                        "possible_workers": shift_managers  # Only shift managers can be supervisors
                    }
                else:
                    # For other positions, check weapon requirements
                    weapon_needed = requirements.get("weapon", 0)
                    no_weapon_needed = requirements.get("noWeapon", 0)

                    # Create variables for slots requiring a weapon
                    for i in range(weapon_needed):
                        var_name = f"{shift}_{position}_{day}_weapon{i}"
                        variables[var_name] = {
                            "shift": shift,
                            "position": position,
                            "day": day,
                            "required_weapon": True,
                            # Workers with weapons and shift managers can fill these slots
                            "possible_workers": shift_managers + with_weapon
                        }
                    
                    # Create variables for slots not requiring a weapon
                    for i in range(no_weapon_needed):
                        var_name = f"{shift}_{position}_{day}_noweapon{i}"
                        variables[var_name] = {
                            "shift": shift,
                            "position": position,
                            "day": day,
                            "required_weapon": False,
                            # Any worker can fill these slots
                            "possible_workers": without_weapon + shift_managers + with_weapon
                        }   

    # Return all the necessary data for the constraint solver
    return {
        "variables": variables,
        "workers": {
            "shift_managers": shift_managers,
            "with_weapon": with_weapon,
            "without_weapon": without_weapon
        },
        "hotel": {
            "name": data["hotel"]["name"]
        }
    }

# Find all workers who are available for each specific day and shift
def available_workers(workers):
    available_employee = {}
    id_to_worker = {}
    
    all_worker_groups = [
        (workers["shift_managers"], "shift_managers"),
        (workers["with_weapon"], "with_weapon"),
        (workers["without_weapon"], "without_weapon")
    ]

    for worker_group, group_name in all_worker_groups:
        for worker in worker_group:
            # Create a map from worker ID to worker object for easy lookup
            if worker['_id'] not in id_to_worker:
                id_to_worker[worker['_id']] = worker
            
            worker_id = worker['_id']
            # Loop through the days and shifts the worker has marked as available
            for day_info in worker.get("selectedDays", []):
                day = day_info["day"]
                for shift in day_info["shifts"]:
                    # Use setdefault to create nested dictionaries if they don't exist
                    shift_availability = available_employee.setdefault(day, {}).setdefault(shift, {
                        "with_weapon": [],
                        "without_weapon": [],
                        "shift_managers": []
                    })
                    
                    # Add worker ID to the appropriate lists based on their qualifications
                    is_manager = worker.get("ShiftManager", False)
                    has_weapon = worker.get("WeaponCertified", False)
                    
                    # A manager can work any shift, including with/without weapon roles
                    if is_manager:
                        shift_availability["shift_managers"].append(worker_id)
                        shift_availability["with_weapon"].append(worker_id)
                        shift_availability["without_weapon"].append(worker_id)
                    # A non-manager with a weapon can work with/without weapon roles
                    elif has_weapon:
                        shift_availability["with_weapon"].append(worker_id)
                        shift_availability["without_weapon"].append(worker_id)
                    # A non-manager without a weapon can only work without weapon roles
                    else:
                        shift_availability["without_weapon"].append(worker_id)

    # Remove duplicates that might occur (e.g., manager added multiple times)
    for day, shifts in available_employee.items():
        for shift, categories in shifts.items():
            for category, worker_ids in categories.items():
                available_employee[day][shift][category] = list(set(worker_ids))
                
    return available_employee, id_to_worker               

# Main execution block for testing purposes
if __name__ == "__main__":
    manager_id = 4
    result = run_algo(manager_id)
    if result:
        # Combine all worker lists into one for processing
        all_workers = (result['workers']['shift_managers'] + 
                       result['workers']['with_weapon'] + 
                       result['workers']['without_weapon'])
        
        availability, id_to_worker_map = available_workers(result['workers'])
        
        # Example of how to print the results
        # print("--- Availability Map ---")
        # import json
        # print(json.dumps(availability, indent=2))
        # print("\n--- ID to Worker Map ---")
        # print(json.dumps(id_to_worker_map, indent=2))