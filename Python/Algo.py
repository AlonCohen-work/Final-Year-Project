from MongoConnection import getData
# Function to run the algorithm and create variables for each shift, position, and day
# This function retrieves data for a specific user (manager) and constructs a set of variables
def run_algo(user_id):    
    data = getData(user_id)
    
    if data is None:
        print("manager not found")
        return 
   #שומר את המשתנים שקיבלנו במשתנים נפרדים 
    hotel = data["hotel"]["schedule"]
    shift_managers = data["workers"]["shift_managers"]
    with_weapon = data["workers"]["with_weapon"]
    without_weapon = data["workers"]["without_weapon"]

    variables = {}
    #לולאה שעוברת על כל המשמרות ועל כל העמודות ויוצרת משתנים עבור כל יום וכל עמדה ועבור כל 
    #עמדה עם נשק ובלי נשק 
    for shift in hotel:
        for position in hotel[shift]:
            for day in hotel[shift][position]:
                if position == "Shift Supervisor":
                    var_name = f'{shift}_{position}_{day}'
                    variables[var_name] = {
                        "shift": shift,
                        "position": position,
                        "day": day,
                        "possible_workers": shift_managers
                    }
                    #במידה וה שאר העמדות ולא העמדה של המנהל משמרת 
                else:
                    requirements = hotel[shift][position][day]
                    weapon_needed = requirements.get("weapon", 0)
                    no_weapon_needed = requirements.get("noWeapon", 0)
                    #העובדים שיש להם נשק 
                    for i in range(weapon_needed):
                        var_name = f"{shift}_{position}_{day}_weapon{i}"
                        variables[var_name] = {
                            "shift": shift,
                            "position": position,
                            "day": day,
                            "required_weapon": True,
                            "possible_workers": shift_managers + with_weapon
                        }
                      #העובדים שאין להם נשק
                    for i in range(no_weapon_needed):
                        var_name = f"{shift}_{position}_{day}_noweapon{i}"
                        variables[var_name] = {
                            "shift": shift,
                            "position": position,
                            "day": day,
                            "required_weapon": False,
                            "possible_workers": without_weapon + shift_managers + with_weapon
                        }   
#החזרת כל המידע להמשך הבעיה כאן נוצרו רק המשתנים 
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
#find all workers who ia available by day
def available_workers(workers):
    available_employee ={}
    shift_managers = workers["shift_managers"]
    with_weapon = workers["with_weapon"]
    without_weapon = workers["without_weapon"]

    id_to_worker ={}
    
    for worker_group in [shift_managers, with_weapon, without_weapon]:
       for worker in worker_group:
        id_to_worker[worker['_id']] = worker
        worker_id = worker['_id']
        for day_info in worker.get("selectedDays", []):
            day = day_info["day"]
            for shift in day_info["shifts"]:
                if day not in available_employee :
                    available_employee[day] = {}
                if shift not in available_employee[day]:
                    available_employee[day][shift] ={
                        "with_weapon":[],
                        "without_weapon":[],
                        "shift_managers":[]
                    }
                if worker in with_weapon:
                    if worker_id not in available_employee[day][shift]["with_weapon"]:
                        available_employee[day][shift]["with_weapon"].append(worker['_id'])
                    if worker_id not in available_employee[day][shift]["without_weapon"]:   
                        available_employee[day][shift]["without_weapon"].append(worker['_id'])
                else:
                    if worker_id not in available_employee[day][shift]["without_weapon"]:   
                        available_employee[day][shift]["without_weapon"].append(worker['_id'])

                if worker in shift_managers:
                    if worker_id not in available_employee[day][shift]["shift_managers"]:   
                       available_employee[day][shift]["shift_managers"].append(worker['_id'])
                    if worker_id not in available_employee[day][shift]["with_weapon"]:   
                        available_employee[day][shift]["with_weapon"].append(worker['_id'])
                    if worker_id not in available_employee[day][shift]["without_weapon"]:   
                        available_employee[day][shift]["without_weapon"].append(worker['_id'])
    return available_employee, id_to_worker               

# Function to run the algorithm and print the results
if __name__ == "__main__":
    manager_id = 4
    result = run_algo(manager_id)
    if result:
        all_workers = (result['workers']['shift_managers'] + 
                      result['workers']['with_weapon'] + 
                      result['workers']['without_weapon'])
        
        availability, id_to_name = available_workers(result['workers'])
        #print_workers_schedule(all_workers)
        #print("--------------")
        #print_availability(availability)




