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

   



