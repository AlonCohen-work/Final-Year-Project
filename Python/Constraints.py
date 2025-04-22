from ortools.sat.python import cp_model
from Algo import run_algo, available_workers
from OrTools import available_shift, variables_for_shifts


def one_shift_per_day(variables, model, workers, variable_model):
    for worker in workers:
        worker_id = worker['_id']

        for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']:
            worker_assignments = []
            for var_name, var_info in variables.items():
                if var_info['day'] == day:
                    possible_ids = [w['_id'] for w in var_info['possible_workers']]
                    if worker_id in possible_ids:
                        cp_var = variable_model[var_name]
                        assigned = model.NewBoolVar(f"{var_name}_assigned_to_{worker_id}")
                        model.Add(cp_var == worker_id).OnlyEnforceIf(assigned)
                        model.Add(cp_var != worker_id).OnlyEnforceIf(assigned.Not())
                        worker_assignments.append(assigned)
            if worker_assignments:
                model.Add(sum(worker_assignments) <= 1)


if __name__ == "__main__":
    model = cp_model.CpModel()
    manager_id = 4
    result = run_algo(manager_id)
    workers_data = result['workers']
    available_employee = available_workers(workers_data)
    variables = available_shift(result['variables'], available_employee)
    print("✅ Processed shifts")
    variable_model = variables_for_shifts(variables, model)

    # אילוץ: כל עובד יכול לעבוד מקסימום משמרת אחת ביום
    one_shift_per_day(variables, model, workers_data['shift_managers'] + workers_data['with_weapon'] + workers_data['without_weapon'], variable_model)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("\n✅ found solution!")
        for var_name, var in variable_model.items():
            print(f"{var_name}: {solver.Value(var)}")
    else:
        print("\n❌ didnt found solution")
