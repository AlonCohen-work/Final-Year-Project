from pymongo import MongoClient
from bson import ObjectId

mongo_client = None
mongo_db = None

def connect_to_mongo():
    """התחברות למונגו - פעם אחת"""
    global mongo_client, mongo_db
    if mongo_client is None:
        try:
            print("Connecting to MongoDB...")
            mongo_client = MongoClient("mongodb+srv://alon123179:23892389Aa@cluster0.arcpa.mongodb.net/people?retryWrites=true&w=majority")
            mongo_db = mongo_client["people"]
            return True
        except Exception as e:
            print("Error connecting to MongoDB:", str(e))
            return False
    return True

def getData(user_id):
    """
    מביא את כל המידע הדרוש מהמונגו:
    1. מידע על המנהל
    2. מידע על המלון והאילוצים שלו
    3. העובדים מחולקים לקטגוריות
    """
    if not connect_to_mongo():
        return None

    try:
        # המרת ID למספר אם הוא מגיע כמחרוזת
        if isinstance(user_id, str):
            try:
                user_id = int(user_id)
            except ValueError:
                print("Invalid user ID format - must be a number")
                return None

        # 1. מידע על המנהל
        manager = mongo_db["people"].find_one({"_id": user_id})
        if not manager:
            print(f"Manager not found with ID: {user_id}")
            return None

        # 2. מידע על המלון
        hotel_name = manager.get("Workplace")
        if not hotel_name:
            print("Manager has no workplace assigned")
            return None
            
        hotel = mongo_db["Workplace"].find_one({"hotelName": hotel_name})
        if not hotel:
            print(f"Hotel not found with name: {hotel_name}")
            return None

        # נדפיס את האילוצים שהמנהל הגדיר
        schedule = hotel.get("schedule", {})
        if schedule:
            print("\nHotel Schedule (defined by manager):")
            for shift in schedule:
                print(f"\n{shift} shift:")
                for position, days in schedule[shift].items():
                    print(f"  {position}:")
                    for day, requirements in days.items():
                        print(f"    {day}: {requirements}")
        else:
            print("\nNo schedule defined for this hotel yet!")

        # 3. הבאת כל העובדים של המלון
        all_workers = list(mongo_db["people"].find({"Workplace": hotel_name}))
        
        # 4. חלוקת העובדים לקטגוריות
        categorized_workers = {
            "shift_managers": [],
            "with_weapon": [],
            "without_weapon": [],
            "all_workers": all_workers
        }

        for worker in all_workers:
            if worker.get("ShiftManager") and worker.get("WeaponCertified"):
                categorized_workers["shift_managers"].append(worker)
            elif worker.get("WeaponCertified"):
                categorized_workers["with_weapon"].append(worker)
            else:
                categorized_workers["without_weapon"].append(worker)

        return {
            "manager": manager,
            "hotel": {
                "name": hotel_name,
                "details": hotel,
                "schedule": hotel.get("schedule", {})
            },
            "workers": categorized_workers
        }

    except Exception as e:
        print(f"Error getting data: {e}")
        return None

def close_mongo_connection():
    """סגירת החיבור למונגו"""
    global mongo_client, mongo_db
    if mongo_client:
        try:
            mongo_client.close()
            mongo_client = None
            mongo_db = None
            print("MongoDB connection closed")
        except Exception as e:
            print("Error closing MongoDB connection")

if __name__ == "__main__":
    connect_to_mongo()
    
    # נשתמש במספר 4 כי זה ה-ID של המנהל במונגו
    manager_id = 4  
    data = getData(manager_id)
    if data:
        print(f"Found manager: {data['manager']['name']}")
        print(f"Found hotel: {data['hotel']['name']}")
        print(f"Number of shift managers: {len(data['workers']['shift_managers'])}")
        print(f"Number of workers with weapon: {len(data['workers']['with_weapon'])}")
        print(f"Number of workers without weapon: {len(data['workers']['without_weapon'])}")
    close_mongo_connection()
    