from constraint import Problem
from MongoConnection import getData, get_workers, connect_to_mongo, close_mongo_connection

def run_algo(user_id):    
    print(f"\n1. id manager : {user_id}")
    hotel_data = getData(user_id)
    
    if hotel_data is None:
        print("manager not found")
        return
    
    # 2. בדיקת שם מלון
    hotel_name = hotel_data.get('hotelName')
    
    # 3. בדיקת עובדים - נשמור את התוצאה לשימוש בהמשך
    all_workers = get_workers(hotel_name)
    print(f"number of workers: {len(all_workers) if all_workers else 0}")
    
    # 4. בדיקת schedule
    schedule = hotel_data.get("schedule", {})
    print(f"\n4. schedule: {schedule}")
    if not schedule:
        print("SCHEDULE IS EMPTY")
        return

    if not hotel_name:
        print("Error: hotel name not found")
        return

    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    shifts = ['Morning', 'Afternoon', 'Evening']

    problem = Problem()
    variables = []
   
    # קריאה לפונקציה עם כל הפרמטרים + העובדים
    add_variables(problem, variables, schedule, hotel_name, days, shifts, all_workers)

    return {
        "problem": problem,
        "variables": variables,
        "schedule": schedule,
        "hotel_name": hotel_name
    }

def add_variables(problem, variables, schedule, hotel_name, days, shifts, workers):
    for shift in shifts:
        shift_data = schedule.get(shift, {})
        for position_name, position_days in shift_data.items():
            for day in days:
                variable_name = f"{position_name}_{day}_{shift}"
                # בדיקת עובדים זמינים - משתמש ברשימת העובדים שכבר הבאנו
                available_workers = check_workers_for_shift(workers, position_name, day, shift)
                print(f"Found {len(available_workers)} available workers for {variable_name}")
                problem.addVariable(variable_name, available_workers)
                variables.append(variable_name)
                

def check_workers_for_shift(workers, position_name, day, shift):
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
            has_weapon = worker_info.get("weaponCertifified", False)
            if not has_weapon:
                continue
        
        available_workers.append(worker_id)
    
    return available_workers

if __name__ == "__main__":
    manager_id = 4
    result = run_algo(manager_id)


                 




