# --- START OF FILE MongoConnection.py ---

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
import logging

# Get a logger instance for this module
logger = logging.getLogger(__name__)

mongo_client = None
mongo_db = None

def connect_to_mongo():
    """
    Establishes a persistent connection to MongoDB if one doesn't already exist.
    Uses robust error handling and logging.
    """
    global mongo_client, mongo_db
    if mongo_client is None:
        try:
            logger.info("Attempting to connect to MongoDB...")
            # It's highly recommended to use environment variables for connection strings in production
            MONGO_URI = "mongodb+srv://alon123179:23892389Aa@cluster0.arcpa.mongodb.net/people?retryWrites=true&w=majority"
            mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) # Added timeout
            # The ismaster command is cheap and does not require auth.
            mongo_client.admin.command('ismaster')
            mongo_db = mongo_client["people"]
            logger.info("MongoDB connection successful.")
            return True
        except (ConnectionFailure, ConfigurationError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}", exc_info=True)
            mongo_client = None # Reset on failure
            mongo_db = None
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during MongoDB connection: {e}", exc_info=True)
            mongo_client = None
            mongo_db = None
            return False
    return True

def connect():
    """
    Returns the database instance, attempting to connect if necessary.
    """
    if mongo_db is None:
        connect_to_mongo()
    return mongo_db

def getData(user_id):
    """
    Retrieve all required data from MongoDB for a given manager ID.
    This includes manager, hotel, schedule requirements, and categorized workers.
    """
    if not connect_to_mongo():
        # The error is already logged in connect_to_mongo
        return None

    try:
        logger.info(f"Attempting to fetch data for manager_id: {user_id}")
        
        # 1. Fetch manager info
        manager = mongo_db["people"].find_one({"_id": int(user_id)})
        if not manager:
            logger.warning(f"Manager not found with ID: {user_id}")
            return None

        # 2. Fetch hotel (workplace) info
        hotel_name = manager.get("Workplace")
        if not hotel_name:
            logger.warning(f"Manager ID {user_id} has no workplace assigned.")
            return None
            
        hotel = mongo_db["Workplace"].find_one({"hotelName": hotel_name})
        if not hotel:
            logger.warning(f"Hotel not found with name: '{hotel_name}'")
            return None

        # 3. Get all workers associated with the hotel
        all_workers = list(mongo_db["people"].find({"Workplace": hotel_name}))
        logger.info(f"Found {len(all_workers)} total workers for hotel '{hotel_name}'.")

        # 4. Categorize workers based on their qualifications
        categorized_workers = {
            "shift_managers": [], "with_weapon": [], "without_weapon": []
        }
        for worker in all_workers:
            # A shift manager can also have a weapon, but for the initial grouping,
            # their primary role as a manager takes precedence.
            if worker.get("ShiftManager"):
                categorized_workers["shift_managers"].append(worker)
            elif worker.get("WeaponCertified"):
                categorized_workers["with_weapon"].append(worker)
            else:
                categorized_workers["without_weapon"].append(worker)

        logger.info(f"Categorized workers: {len(categorized_workers['shift_managers'])} managers, "
                    f"{len(categorized_workers['with_weapon'])} with weapon, "
                    f"{len(categorized_workers['without_weapon'])} without weapon.")

        return {
            "manager": manager,
            "hotel": {
                "name": hotel_name,
                "schedule": hotel.get("schedule", {})
            },
            "workers": categorized_workers
        }
    except ValueError:
        logger.error(f"Invalid user_id format: '{user_id}'. Must be a number.")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred in getData for user_id {user_id}: {e}", exc_info=True)
        return None

def close_mongo_connection():
    """Closes the MongoDB connection if it's open."""
    global mongo_client, mongo_db
    if mongo_client:
        try:
            mongo_client.close()
            mongo_client = None
            mongo_db = None
            logger.info("MongoDB connection closed.")
        except Exception as e:
            logger.error(f"Error while closing MongoDB connection: {e}", exc_info=True)