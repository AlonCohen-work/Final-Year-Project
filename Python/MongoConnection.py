from pymongo import MongoClient

# connect to the mongo 
def getData():
    client = MongoClient("mongodb+srv://alon123179:23892389Aa@cluster0.arcpa.mongodb.net/people?retryWrites=true&w=majority")
    db = client["people"]
    people = list(db["people"].find())
    hotels = list(db["Workplace"].find())
    return people, hotels

# each position is the key 
def extractPositions(workplace_data):
    positions_set = set()
    schedule = workplace_data.get("schedule", {})
    for shift in schedule:
        positions_set.update(schedule[shift].keys())
    return list(positions_set)

# each hotel has his own constraints 
def extractHotel(hotels, hotel_name):
    for hotel in hotels:
        if hotel['hotelName'] == hotel_name:
            return hotel.get('schedule', {})
    return None

#print 
def printWorkplaceData():
    people, hotels = getData()
    for hotel in hotels:
        print(f"Hotel: {hotel['hotelName']}")
        schedule = hotel.get('schedule', {})
        for shift in schedule:
            print(f"Shift: {shift}")
            for day, day_data in schedule[shift].items():
                print(f"  Day: {day}")
                no_weapon = day_data.get('noWeapon', 0)
                weapon = day_data.get('weapon', 0)
                print(f"    No Weapon Required: {no_weapon}")
                print(f"    Weapon Required: {weapon}")
        print("-" * 40)

if __name__ == "__main__":
    printWorkplaceData()
