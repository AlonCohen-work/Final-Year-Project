from pymongo import MongoClient
from bson import ObjectId

mongo_client = None
mongo_db = None

def connect_to_mongo():
     #Connect to MongoDB (single-use connection)
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
def connect():
  #Alternative connection function to MongoDB (returns the DB instance)
    global mongo_client, mongo_db
    if mongo_client is None:
        try:
            print("Connecting to MongoDB...")
            mongo_client = MongoClient("mongodb+srv://alon123179:23892389Aa@cluster0.arcpa.mongodb.net/people?retryWrites=true&w=majority")
            mongo_db = mongo_client["people"]
            
        except Exception as e:
            print("Error connecting to MongoDB:", str(e))
            return None
    return mongo_db  # returns the DB object


def getData(user_id):
    #Retrieve all required data from MongoDB:
    #1. Manager info
    #2. Hotel (Workplace) info and defined schedule
    #3. All hotel employees categorized by roles and weapon certification
    if connect_to_mongo() is not True:
        return None

    try:
        # Convert user_id to int if it was passed as a string
        if isinstance(user_id, str):
            try:
                user_id = int(user_id)
            except ValueError:
                print("Invalid user ID format - must be a number")
                return None

        # 1. Fetch manager info
        manager = mongo_db["people"].find_one({"_id": user_id})
        if manager is None:
            print(f"Manager not found with ID: {user_id}")
            return None

        # 2. Fetch hotel (workplace) info
        hotel_name = manager.get("Workplace")
        if hotel_name is None:
            print("Manager has no workplace assigned")
            return None
            
        hotel = mongo_db["Workplace"].find_one({"hotelName": hotel_name})
        if hotel is None:
            print(f"Hotel not found with name: {hotel_name}")
            return None

       # Parse and structure the defined schedule (if exists)
        schedule = hotel.get("schedule", {})
        if schedule:
            #print("\nHotel Schedule (defined by manager):")
            days_of_schedule = {}
            for shift in schedule:
                for position in schedule[shift]:
                    for day, requirements in schedule[shift][position].items():
                        if day not in days_of_schedule:
                            days_of_schedule[day] = {}
                        if shift not in days_of_schedule[day]:
                            days_of_schedule[day][shift] = {}
                        days_of_schedule[day][shift][position] = requirements

            for day in sorted(days_of_schedule.keys()):
              #  print (f" day : {day}")
                for shift in ["Morning" , "Afternoon" , "Evening"]:
                    if shift in days_of_schedule[day]:
                        for position, requirements in days_of_schedule[day][shift].items():
                            weapon = requirements.get("weapon", 0)
                            noweapon = requirements.get("noweapon", 0)
                      #      print(f" shift: {shift} - position: {position} - weapon: {weapon} - noweapon: {noweapon}")                   
        else:
            print("\nNo schedule defined for this hotel yet!")

        # 3. Get all workers associated with the hotel
        all_workers = list(mongo_db["people"].find({"Workplace": hotel_name}))
        
        # 4. Categorize workers
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
    #Close MongoDB connection
    global mongo_client, mongo_db
    if mongo_client:
        try:
            mongo_client.close()
            mongo_client = None
            mongo_db = None
        except Exception as e:
            return None

if __name__ == "__main__":
    connect_to_mongo()
    manager_id = 4
    data = getData(manager_id)
    close_mongo_connection()