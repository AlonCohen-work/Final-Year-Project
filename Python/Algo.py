from MongoConnection import getData
#מביא את כל המידע ממונגו ע פי הID של המנהל 
def run_algo(user_id):    
    data = getData(user_id)
    
    if data is None:
        print("manager not found")
        return 
   #שומר את המשתנים שקיבלנו במשתנים נפרדים 
    hotel = data["hotel"]["schedule"]
    shift_managers = data["workers"]["shift_managers"]
    with_weapon = data["workers"]["with_weapon"]
    without_weapon = data["workers"]["without_weapon"]

    variables = {}
    #לולאה שעוברת על כל המשמרות ועל כל העמודות ויוצרת משתנים עבור כל יום וכל עמדה ועבור כל 
    #עמדה עם נשק ובלי נשק 
    for shift in hotel:
        for position in hotel[shift]:
            for day in hotel[shift][position]:
                if position == "shift supervisor":
                    var_name = f'{shift}_{position}_{day}'
                    variables[var_name] = {
                        "shift": shift,
                        "position": position,
                        "day": day,
                        "possible_workers": shift_managers
                    }
                    #במידה וה שאר העמדות ולא העמדה של המנהל משמרת 
                else:
                    requirements = hotel[shift][position][day]
                    weapon_needed = requirements.get("weapon", 0)
                    no_weapon_needed = requirements.get("noWeapon", 0)
                    #העובדים שיש להם נשק 
                    for i in range(weapon_needed):
                        var_name = f"{shift}_{position}_{day}_weapon{i}"
                        variables[var_name] = {
                            "shift": shift,
                            "position": position,
                            "day": day,
                            "required_weapon": True,
                            "possible_workers": with_weapon
                        }
                      #העובדים שאין להם נשק
                    for i in range(no_weapon_needed):
                        var_name = f"{shift}_{position}_{day}_noweapon{i}"
                        variables[var_name] = {
                            "shift": shift,
                            "position": position,
                            "day": day,
                            "required_weapon": False,
                            "possible_workers": without_weapon
                        }   
#החזרת כל המידע להמשך הבעיה כאן נוצרו רק המשתנים 
    return {
        "variables": variables,
        "workers": {
            "shift_managers": shift_managers,
            "with_weapon": with_weapon,
            "without_weapon": without_weapon
        }
    }

if __name__ == "__main__":
    manager_id = 4
    result = run_algo(manager_id)

                 




