from pymongo import MongoClient
from constraint import Problem
mongo_client = None
mongo_db = None

# connect to the mongo_db 
def connect_to_mongo():
    global mongo_client, mongo_db
    if mongo_client is None:
        try:
            print("Connecting to MongoDB...")
            mongo_client = MongoClient("mongodb+srv://alon123179:23892389Aa@cluster0.arcpa.mongodb.net/people?retryWrites=true&w=majority")
            mongo_db = mongo_client["people"]
            
            # בדיקת קולקציות
            print("Available collections:", mongo_db.list_collection_names())
            
            # בדיקת תוכן הקולקציה
            workplace_docs = list(mongo_db["workplace"].find())
            print("Documents in workplace collection:", workplace_docs)
            
            return True
        except Exception as e:
            print("Error connecting to MongoDB:", str(e))
            return False

# get the data from the mongo_db accordingliy to the manager hotel 
def getData(user_id):
    if not mongo_db:
        if not connect_to_mongo():
            print("Failed to connect to MongoDB")
            return None
    
    try:
        print(f"Looking for manager with ID: {user_id}")
        manager = mongo_db["people"].find_one({"_id": user_id})
        
        if manager:
            workplace = manager.get("Workplace")  
            print(f"Found workplace: {workplace}")

            if workplace:
                schedule = get_hotel_schedule(workplace)
                print(f"Found schedule: {schedule}")
                
                return {
                    "hotelName": workplace,
                    "schedule": schedule
                }
            else:
                print("No workplace found in manager document")
        else:
            print("No manager found")
        return None

    except Exception as e:
        print(f"Error: {e}")
        return None


# close the connection to the mongo_db
def close_mongo_connection():
    global mongo_client, mongo_db
    if mongo_client:
        try:
            mongo_client.close()
            mongo_client = None
            mongo_db = None
            print("MongoDB connection closed")
        except Exception as e:
            print("Error closing MongoDB connection")   

# check if the user is manager 
def is_manager(user_id):
    try:
        if mongo_client is None:
            if not connect_to_mongo():
                print("Could not connect to MongoDB")
                return False, None
                
        user = mongo_db["people"].find_one({"_id": user_id})  
        if not user:
            print("User not found")
            return False, None
            
        if user.get("job") == "management":
            hotel = mongo_db["Workplace"].find_one({"hotelName": user.get("Workplace")})
            if not hotel:
                print("Hotel not found")
                return False, None
            return True, hotel
                    
        return False, None
                    
    except Exception as e:
        print(f"Error checking if user is manager: {e}")
        return False, None

# get the workers that working in the hotel:
def get_workers(hotelName):
    workers = mongo_db["people"].find({"Workplace": hotelName})
    return {str(worker["_id"]): worker for worker in workers}

def get_hotel_schedule(hotel_name):
    try:
        print(f"\nLooking for hotel: {hotel_name}")
        all_hotels = list(mongo_db["Workplace"].find())
        print(f"All hotels in workplace collection: {all_hotels}")
        
        hotel = mongo_db["Workplace"].find_one({"hotelName": hotel_name})
        print(f"Found hotel document: {hotel}")

        if hotel:
            schedule = hotel.get("schedule", {})
            return schedule
            
        print("No hotel found")
        return None

    except Exception as e:
        print(f"Error getting schedule: {e}")
        return None

def check_workers_for_shift(hotel_name, position_name, day, shift):
    workers = get_workers(hotel_name)
    available_workers_with_weapon = []
    available_workers_without_weapon = []
    
    for worker_id, worker_info in workers.items():
        # בדיקת זמינות
        selected_days = worker_info.get("selectedDays", [])
        is_available = False
        
        for selected_day in selected_days:
            if selected_day["day"] == day and shift in selected_day.get("shifts", []):
                is_available = True
                break
        
        if not is_available:
            continue
        
        # בדיקת נשק והוספה לרשימה המתאימה
        has_weapon = worker_info.get("weaponCertifified", False)
        if has_weapon:
            available_workers_with_weapon.append(worker_id)
        else:
            available_workers_without_weapon.append(worker_id)
    
    print(f"For {position_name} on {day} {shift}:")
    print(f"Workers with weapon: {len(available_workers_with_weapon)}")
    print(f"Workers without weapon: {len(available_workers_without_weapon)}")
    
    # אם זה תפקיד Security, מחזיר רק עובדים עם נשק
    if position_name == "Security":
        return available_workers_with_weapon
    # אחרת מחזיר את כל העובדים הזמינים
    return available_workers_with_weapon + available_workers_without_weapon

if __name__ == "__main__":
    connect_to_mongo()  # מתחבר למונגו
    close_mongo_connection()  # סוגר את החיבור בסוף
    