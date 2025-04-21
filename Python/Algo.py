from MongoConnection import getData
#מביא את כל המידע ממונגו ע פי הID של המנהל 
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
                if position == "shift supervisor":
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
                            "requi red_weapon": True,
                            "possible_workers": with_weapon
                        }
                      #העובדים שאין להם נשק
                    for i in range(no_weapon_needed):
                        var_name = f"{shift}_{position}_{day}_noweapon{i}"
                        variables[var_name] = {
                            "shift": shift,
                            "position": position,
                            "day": day,
                            "required_weapon": False,
                            "possible_workers": without_weapon
                        }   
#החזרת כל המידע להמשך הבעיה כאן נוצרו רק המשתנים 
    return {
        "variables": variables,
        "workers": {
            "shift_managers": shift_managers,
            "with_weapon": with_weapon,
            "without_weapon": without_weapon
        }
    }
#find all workers who ia available by day
def available_workers(workers):
    availability ={}
    for worker in workers:
        has_weapon = worker.get("WeaponCertified", False)
        is_manager = worker.get("ShiftManager", False)

        for day_info in worker.get("selectedDays", []):
            day = day_info["day"]
            for shift in day_info["shifts"]:
                if day not in availability :
                    availability[day] = {}
                if shift not in availability[day]:
                    availability[day][shift] ={
                        "with_weapon":[],
                        "without_weapon":[],
                        "shift_managers":[]
                    }
                if has_weapon:
                    availability[day][shift]["with_weapon"].append(worker)
                    availability[day][shift]["without_weapon"].append(worker)
                else:
                    availability[day][shift]["without_weapon"].append(worker)

                if is_manager:
                    availability[day][shift]["shift_managers"].append(worker)
    return availability                

def print_availability(availability):
    print("\n=== Workers Availability ===")
    for day in availability:
        print(f"\nDay: {day}")
        for shift in availability[day]:
            print(f"\n  Shift: {shift}")
            print("    Shift Managers:")
            for worker in availability[day][shift]["shift_managers"]:
                print(f"      - {worker['name']}")
            
            print("    Workers with weapon:")
            for worker in availability[day][shift]["with_weapon"]:
                print(f"      - {worker['name']}")
            
            print("    Workers without weapon:")
            for worker in availability[day][shift]["without_weapon"]:
                print(f"      - {worker['name']}")

def print_workers_schedule(workers):
    for worker in workers:
        print(f"\n👤 {worker.get('name', 'Unknown')}")
        for day_info in worker.get("selectedDays", []):
            day = day_info["day"]
            shifts = ", ".join(day_info["shifts"])
            print(f"  📅 {day}: {shifts}")

if __name__ == "__main__":
    manager_id = 4
    result = run_algo(manager_id)
    if result:
        all_workers = (result['workers']['shift_managers'] + 
                      result['workers']['with_weapon'] + 
                      result['workers']['without_weapon'])
        
        availability = available_workers(all_workers)
    #    print_availability(availability)
        print_workers_schedule(all_workers)
        print("--------------")
        print_availability(availability)




