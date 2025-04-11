from pymongo import MongoClient
mongo_client = None
mongo_db = None

# connect to the mongo_db 
def connect_to_mongo():
    global mongo_client, mongo_db
    if mongo_client is None:
        try:
            mongo_client = MongoClient("mongodb+srv://alon123179:23892389Aa@cluster0.arcpa.mongodb.net/people?retryWrites=true&w=majority")
            mongo_db = mongo_client["people"]
            print("Connected to MongoDB successfully")
            return True
        except Exception as e:
            print("Error connecting to MongoDB")
            return False

# get the data from the mongo_db accordingliy to the manager hotel 
def getData(user_id):
    try:   
        result_is_manager, hotel_data = is_manager(user_id)
        if result_is_manager:
            return hotel_data
        return None
    except Exception as e:
        print("Error getting data")
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
            hotel = mongo_db["workplace"].find_one({"hotelName": user.get("workplace")})
            if not hotel:
                print("Hotel not found")
                return False, None
            return True, hotel
                    
        return False, None
                    
    except Exception as e:
        print(f"Error checking if user is manager: {e}")
        return False, None

if __name__ == "__main__":
    connect_to_mongo()  # מתחבר למונגו
    close_mongo_connection()  # סוגר את החיבור בסוף
