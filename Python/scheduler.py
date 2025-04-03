# 📁 File: csp_scheduler.py

from constraint import Problem
from MongoConnection import getData, extractPositions
from collections import defaultdict

# הגדרות כלליות
days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
shifts = ['Morning', 'Afternoon', 'Evening']

# 1️⃣ שליפת נתונים ממונגו
people, hotels = getData()
hotel = hotels[0]
hotel_name = hotel['hotelName']
schedule = hotel.get('schedule', {})

problem = Problem()
variables = []
variable_info_map = {}

# 2️⃣ יצירת משתנים (variables)
for shift in shifts:
    shift_data = schedule.get(shift, {})
    for position_name, position_days in shift_data.items():
        for day in days:
            day_info = position_days.get(day, {})

            nums_with_weapon = day_info.get('weapon', 0)
            nums_without_weapon = day_info.get('noWeapon', 0)

            for i in range(nums_with_weapon):
                var_name = f"{hotel_name}_{day}_{shift}_{position_name}_weapon_{i}"
                variables.append(var_name)
                variable_info_map[var_name] = {
                    'hotel': hotel_name,
                    'day': day,
                    'shift': shift,
                    'position': position_name,
                    'weapon': True
                }

            for i in range(nums_without_weapon):
                var_name = f"{hotel_name}_{day}_{shift}_{position_name}_noWeapon_{i}"
                variables.append(var_name)
                variable_info_map[var_name] = {
                    'hotel': hotel_name,
                    'day': day,
                    'shift': shift,
                    'position': position_name,
                    'weapon': False
                }

# 3️⃣ יצירת תחום (Domain) לכל משתנה
for var in variables:
    var_info = variable_info_map[var]
    possible_ids = []

    for person in people:
        if person["Workplace"] != hotel_name:
            continue

        has_weapon = person.get("WeaponCertified", False)
        is_manager = person.get("ShiftManager", False)

        available = any(
            d["day"] == var_info["day"] and var_info["shift"] in d["shifts"]
            for d in person["selectedDays"]
        )

        if var_info["weapon"] and not has_weapon:
            continue

        if var_info["position"] == "Shift Supervisor" and not is_manager:
            continue

        if not available:
            continue

        possible_ids.append(person["_id"])

    if not possible_ids:
        print(f"⚠️ No possible workers for variable: {var}")
        continue  # נמשיך למרות שאין פתרון משתנה זה

    problem.addVariable(var, possible_ids)

# 4️⃣ אילוץ 1: אין כפילות באותו יום (עובד לא יעבוד פעמיים ביום)
for day in days:
    day_vars = [v for v in variables if variable_info_map[v]["day"] == day]
    for i in range(len(day_vars)):
        for j in range(i + 1, len(day_vars)):
            problem.addConstraint(lambda a, b: a != b, (day_vars[i], day_vars[j]))

# 5️⃣ אילוץ 2: אין ערב ואז בוקר למחרת
for i, day in enumerate(days[:-1]):
    next_day = days[i + 1]
    evening_vars = [v for v in variables if variable_info_map[v]["day"] == day and variable_info_map[v]["shift"] == "Evening"]
    morning_vars = [v for v in variables if variable_info_map[v]["day"] == next_day and variable_info_map[v]["shift"] == "Morning"]

    for ev in evening_vars:
        for mo in morning_vars:
            problem.addConstraint(lambda a, b: a != b, (ev, mo))

# 6️⃣ אילוץ 3: לא יותר מ-12 שעות (לא יותר מ-2 משמרות ביום)
day_groups = defaultdict(list)
for v in variables:
    day_groups[variable_info_map[v]["day"]].append(v)

for day_vars in day_groups.values():
    for i in range(len(day_vars)):
        for j in range(i + 1, len(day_vars)):
            for k in range(j + 1, len(day_vars)):
                problem.addConstraint(lambda a, b, c: len(set([a, b, c])) == 3, (day_vars[i], day_vars[j], day_vars[k]))

# פתרון 1 בודד
solution = problem.getSolution()

# הדפסת פתרון
if solution:
    print("\n📅 לוח זמנים שנוצר:")
    for var, worker in sorted(solution.items()):
        print(f"{var} ➝ עובד: {worker}")
else:
    print("❌ לא נמצא פתרון חוקי עבור אילוצי השיבוץ.")
