from constraint import Problem
from MongoConnection import getData
from collections import defaultdict

# הגדרות כלליות
days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
shifts = ['Morning', 'Afternoon', 'Evening']

# שליפת נתונים ממונגו
people, hotels, supervisors = getData()
hotel = hotels[0]
hotel_name = hotel['hotelName']
schedule = hotel.get('schedule', {})

# סינון shift supervisors של המלון הנוכחי
shift_supervisors = [
    p for p in supervisors
    if p.get("Workplace") == hotel_name
]

problem = Problem()
variables = []
variable_info = {}

# יצירת משתנים עבור עמדות Shift Supervisor עם נשק בלבד
for day in days:
    for shift in shifts:
        count = schedule.get(shift, {}).get("Shift Supervisor", {}).get(day, {}).get("weapon", 0)
        for i in range(count):
            var = f"{day}_{shift}_ShiftSupervisor_{i}"
            variables.append(var)
            variable_info[var] = {"day": day, "shift": shift}

# יצירת domain לכל משתנה מתוך רשימת shift supervisors
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

# אילוץ 1: עובד לא יכול לעבוד ביותר ממשמרת אחת ביום
for day in days:
    day_vars = [v for v in variables if variable_info[v]["day"] == day]
    for i in range(len(day_vars)):
        for j in range(i + 1, len(day_vars)):
            problem.addConstraint(lambda a, b: a != b, (day_vars[i], day_vars[j]))

# אילוץ 2: אם עבד ערב, אסור לעבוד בוקר ביום למחרת
for i in range(len(days) - 1):
    today = days[i]
    next_day = days[i + 1]
    evening_vars = [v for v in variables if variable_info[v]["day"] == today and variable_info[v]["shift"] == "Evening"]
    morning_vars = [v for v in variables if variable_info[v]["day"] == next_day and variable_info[v]["shift"] == "Morning"]
    for e in evening_vars:
        for m in morning_vars:
            problem.addConstraint(lambda a, b: a != b, (e, m))

# פתרון – רק פתרון אחד
solution = problem.getSolution()
if solution:
    print("\n📋 Shift Supervisor Schedule:")
    for var, worker_id in sorted(solution.items(), key=lambda x: (days.index(variable_info[x[0]]["day"]), shifts.index(variable_info[x[0]]["shift"]))):
        print(f"{var} ➔ worker id: {worker_id}")
else:
    print("❌ No valid Shift Supervisor schedule found.")
