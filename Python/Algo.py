from constraint import Problem
from MongoConnection import getData , extractPositions

problem = Problem()

people,positionsTable= getData()
positions=extractPositions(positionsTable[0])

days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
shifts = ['Morning', 'Afternoon', 'Evening']
variables=[f"{day}_{shift}_{position}" for day in days for shift in shifts for position in positions]

for variable in variables:
    print(variable)