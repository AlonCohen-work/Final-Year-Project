# 📁 File: scheduler_shift_supervisors.py

from constraint import Problem
from MongoConnection import getData
from collections import defaultdict
from statistics import stdev
from pymongo import MongoClient

# הגדרות כלליות

days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
shifts = ['Morning', 'Afternoon', 'Evening']

# שליפת נתונים ממונגו
people, hotels, supervisors = getData()
hotel = hotels[0]
hotel_name = hotel['hotelName']
schedule = hotel.get('schedule', {})

# סינון shift supervisors של המלון שלו הוא hotel_name
shift_supervisors = [p for p in supervisors if p.get("Workplace") == hotel_name]

problem = Problem()
variables = []
variable_info = {}

# יצירת משתנים עבור עמדות Shift Supervisor עם נשק (weapon)
for day in days:
    for shift in shifts:
        count = schedule.get(shift, {}).get("Shift Supervisor", {}).get(day, {}).get("weapon", 0)
        for i in range(count):
            var = f"{day}_{shift}_ShiftSupervisor_{i}"
            variables.append(var)
            variable_info[var] = {"day": day, "shift": shift}

# בניית תחום ערכים (Domain) עבור כל משתנה, רק מי shift_supervisors
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

# אילוץ 1: עובד לא יכול לעבוד פעמיים באותו יום
for day in days:
    day_vars = [v for v in variables if variable_info[v]["day"] == day]
    for i in range(len(day_vars)):
        for j in range(i + 1, len(day_vars)):
            problem.addConstraint(lambda a, b: a != b, (day_vars[i], day_vars[j]))

# אילוץ 2: אם עבד ערב – לא יכול לעבוד בוקר למחרת
for i in range(len(days) - 1):
    today = days[i]
    next_day = days[i + 1]
    evening_vars = [v for v in variables if variable_info[v]["day"] == today and variable_info[v]["shift"] == "Evening"]
    morning_vars = [v for v in variables if variable_info[v]["day"] == next_day and variable_info[v]["shift"] == "Morning"]
    for e in evening_vars:
        for m in morning_vars:
            problem.addConstraint(lambda a, b: a != b, (e, m))

# אילוץ 3: משמרת אחת ביום
for day in days:
    day_vars = [v for v in variables if variable_info[v]["day"] == day]
    for i in range(len(day_vars)):
        for j in range(i + 1, len(day_vars)):
            problem.addConstraint(lambda a, b: a != b, (day_vars[i], day_vars[j]))

# קבל כל הפתרונות ובחיר את הכלי הכי שהתפרשו בין שונוי משמרות
all_solutions = problem.getSolutions()
best_solution = None
best_std = float('inf')

for sol in all_solutions:
    shift_counts = defaultdict(int)
    for worker_id in sol.values():
        shift_counts[worker_id] += 1
    std = stdev(shift_counts.values()) if len(shift_counts) > 1 else 0

    if std < best_std:
        best_std = std
        best_solution = sol

# הצגת פתרון ושמר
if best_solution:
    print("\n📋 Shift Supervisor Schedule:")
    for var, worker_id in sorted(best_solution.items(), key=lambda x: (days.index(variable_info[x[0]]["day"]), shifts.index(variable_info[x[0]]["shift"]))):
        print(f"{var} ➔ worker id: {worker_id}")

    # ספירה סה\u05db של משמרות לכל עובד
    shift_summary = defaultdict(int)
    for wid in best_solution.values():
        shift_summary[wid] += 1

    print("\n📊 Shift Totals per Supervisor:")
    for person in shift_supervisors:
        pid = person["_id"]
        print(f"ID: {pid}, Name: {person['name']}, Total Shifts: {shift_summary.get(pid, 0)}")

    # שימור למונגו
    client = MongoClient("mongodb+srv://alon123179:23892389Aa@cluster0.arcpa.mongodb.net/?retryWrites=true&w=majority")
    db = client["people"]
    db["scheduler_shift_supervisors"].insert_one({
        "hotel": hotel_name,
        "solution": best_solution,
        "summary": [{
            "id": p["_id"],
            "name": p["name"],
            "total_shifts": shift_summary.get(p["_id"], 0)
        } for p in shift_supervisors]
    })
else:
    print("❌ No valid Shift Supervisor schedule found.")
