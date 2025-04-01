from pymongo import MongoClient

def getData():
    client = MongoClient("mongodb+srv://alon123179:23892389Aa@cluster0.arcpa.mongodb.net/people?retryWrites=true&w=majority")
    db = client["people"]

    people_coll = db["people"]
    workplace_coll = db["Workplace"]

    people=list(people_coll.find())
    positions=list(workplace_coll.find())

    return people,positions

def extractPositions(workplace_data):
    positions_set=set()
    schedule = workplace_data["schedule"]

    for shift in schedule:
        positions_set.update(schedule[shift].keys())

    return list(positions_set)    

   
def printWorkplaceData():
    # שליפת הנתונים ממונגו
    people, positions = getData()

    # הדפסת כל המידע מתוך אוסף Workplace
    for position in positions:
        print(f"Hotel: {position['hotelName']}")
        
        # עבור כל משמרת בלוח הזמנים
        schedule = position.get('schedule', {})
        for shift in schedule:
            print(f"Shift: {shift}")
            
            # עבור כל יום בשבוע
            for day, day_data in schedule[shift].items():
                print(f"  Day: {day}")
                
                # הדפסת דרישות הנשק
                no_weapon = day_data.get('noWeapon', 0)
                weapon = day_data.get('weapon', 0)
                
                print(f"    No Weapon Required: {no_weapon}")
                print(f"    Weapon Required: {weapon}")
                
        print("-" * 40)  # פס מפריד בין המלונות

# הפונקציה הזו תדפיס את כל המידע הרלוונטי לעמדות
printWorkplaceData()


