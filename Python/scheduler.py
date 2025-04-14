# 📁 File: scheduler_shift_supervisors.py

from constraint import Problem
from MongoConnection import getlist
from collections import defaultdict
from pymongo import MongoClient

# הגדרות כלליות
days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
shifts = ['Morning', 'Afternoon', 'Evening']

# שליפת נתונים ממונגו
people, hotels, shift_supervisors = getlist(4)
hotel = hotels[0]
hotel_name = hotel['hotelName']
schedule = hotel.get('schedule', {})

# סינון shift supervisors של המלון הרלוונטי

problem = Problem()
variables = []
variable_info = {}

# יצירת משתנים לפי דרישת משמרות Shift Supervisor עם נשק
for day in days:
    for shift in shifts:
        count = schedule.get(shift, {}).get("Shift Supervisor", {}).get(day, {}).get("weapon", 0)
        for i in range(count):
            var = f"{day}_{shift}_ShiftSupervisor_{i}"
            variables.append(var)
            variable_info[var] = {"day": day, "shift": shift}

# הגדרת domain לכל משתנה
for var in variables:
    day = variable_info[var]["day"]
    shift = variable_info[var]["shift"]
    possible_workers = []

    for person in shift_supervisors:
        available = any(
            d["day"] == day and shift in d["shifts"]
            for d in person.get("selectedDays", [])
        )
        if available:
            possible_workers.append(person["_id"])

    if not possible_workers:
        print(f"⚠️ No possible workers for variable: {var}")
    problem.addVariable(var, possible_workers)

# אילוץ: לא לעבוד פעמיים באותו יום
for day in days:
    day_vars = [v for v in variables if variable_info[v]["day"] == day]
    for i in range(len(day_vars)):
        for j in range(i + 1, len(day_vars)):
            problem.addConstraint(lambda a, b: a != b, (day_vars[i], day_vars[j]))

# אילוץ: לא לעבוד ערב ואז בוקר ביום שאחריו
for i in range(len(days) - 1):
    today = days[i]
    next_day = days[i + 1]
    evening_vars = [v for v in variables if variable_info[v]["day"] == today and variable_info[v]["shift"] == "Evening"]
    morning_vars = [v for v in variables if variable_info[v]["day"] == next_day and variable_info[v]["shift"] == "Morning"]
    for e in evening_vars:
        for m in morning_vars:
            problem.addConstraint(lambda a, b: a != b, (e, m))

# מציאת פתרון בודד (מהיר)
solution = problem.getSolution()

# הדפסת התוצאה + סיכום + שמירה למונגו
if solution:
    print("\n📋 Shift Supervisor Schedule:")
    for var, worker_id in sorted(solution.items(), key=lambda x: (days.index(variable_info[x[0]]["day"]), shifts.index(variable_info[x[0]]["shift"]))):
        print(f"{var} ➔ worker id: {worker_id}")

    # סיכום מספר משמרות לעובד
    shift_summary = defaultdict(int)
    for wid in solution.values():
        shift_summary[wid] += 1

    print("\n📊 Shift Totals per Supervisor:")
    for person in shift_supervisors:
        pid = person["_id"]
        print(f"ID: {pid}, Name: {person['name']}, Total Shifts: {shift_summary.get(pid, 0)}")

    # שמירה למסד הנתונים
    client = MongoClient("mongodb+srv://alon123179:23892389Aa@cluster0.arcpa.mongodb.net/?retryWrites=true&w=majority")
    db = client["people"]
    db["scheduler_shift_supervisors"].insert_one({
        "hotel": hotel_name,
        "solution": solution,
        "summary": [{
            "id": p["_id"],
            "name": p["name"],
            "total_shifts": shift_summary.get(p["_id"], 0)
        } for p in shift_supervisors]
    })
else:
    print("❌ No valid Shift Supervisor schedule found.")
