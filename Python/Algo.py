from constraint import Problem
from MongoConnection import getData, get_workers, connect_to_mongo, close_mongo_connection

def run_algo(user_id):
    hotel_data = getData(user_id)
    if hotel_data is None:
        print("Error getting data")
        return

    hotel_name = hotel_data.get('hotelName')
    
    if not hotel_name:
        print("Error: hotel name not found")
        return

    print(hotel_name)

    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    shifts = ['Morning', 'Afternoon', 'Evening']

    # Initialize constraint problem
    problem = Problem()
    variables = []
   
    # create a schedule for each shift position and day 
    schedule = hotel_data.get("schedule", {})
    for shift in shifts:
        shift_data = schedule.get(shift, {})
        for position_name, position_days in shift_data.items():
            for day in days:
                day_info = position_days.get(day, {})
                nums_with_weapon = day_info.get('weapon', 0)
                nums_without_weapon = day_info.get('noWeapon', 0)

    # קריאה לפונקציה עם כל הפרמטרים
    add_variables(problem, variables, schedule, hotel_name, days, shifts)

    return {
        "problem": problem,
        "variables": variables,
        "schedule": schedule,
        "hotel_name": hotel_name
    }

# add variables for each position, each variable is a shift with a position and a day
def add_variables(problem, variables, schedule, hotel_name, days, shifts):
    for shift in shifts:
        shift_data = schedule.get(shift, {})
        for position_name, position_days in shift_data.items():
            for day in days:
                variable_name = f"{position_name}_{day}_{shift}"
                # בדיקת עובדים זמינים
                available_workers = check_workers_for_shift(hotel_name, position_name, day, shift)
                print(f"Found {len(available_workers)} available workers for {variable_name}")
                # הוספת המשתנה
                problem.addVariable(variable_name, available_workers)
                variables.append(variable_name)

# check for each worker if he is avaliable for the shift 
def check_workers_for_shift(hotel_name, position_name, day, shift):
    workers = get_workers(hotel_name)
    available_workers = []
    
    for worker_id, worker_info in workers.items():
        selected_days = worker_info.get("selectedDays", [])
        is_available = False
        
        for selected_day in selected_days:
            if selected_day["day"] == day and shift in selected_day.get("shifts", []):
                is_available = True
                break
        
        if not is_available:
            continue
            
        if position_name == "Security":
            has_weapon = worker_info.get("weaponCertifified",False)
            if not has_weapon:
                continue
        
        available_workers.append(worker_id)
    
    return available_workers

if __name__ == "__main__":
    manager_id = 4
    result = run_algo(manager_id)


                 




