from constraint import Problem
from MongoConnection import getData , extractPositions

problem = Problem()

people,positionsTable= getData()
positions=extractPositions(positionsTable[0])

days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
shifts = ['Morning', 'Afternoon', 'Evening']
variables=[]

for hotel in positionsTable:
    hotel_name=hotel['hotelName']
    schedule=hotel.get('schedule',{})

    for shift in shifts:
        shift_data=schedule.get(shift,{})
        for position_name,position_days in shift_data.items():
            for day in days:
                day_info=position_days.get('weapon',0)

                nums_with_weapon=day_info.get('weapon',0)
                nums_without_weapon=day_info.get('noweapn',0)

                for i in range(nums_with_weapon):
                    var_name=f"{hotel_name}_{day}_{position_name}_weapon_{i}"
                    variables.append(var_name)

                for i in range(nums_without_weapon):
                    var_name=f"{hotel_name}_{day}_{position_name}_noweapn_{i}"
                    variables.append(var_name)

print(variables)                    
