# ============================================================
# parser.py — Intérprete de datos de la interfaz
# ============================================================
# Actúa como PUENTE entre la interfaz (app.py) y los módulos
# matemáticos (simplex_solver, graphics, sensitivity).

import numpy as np


def build_problem(problem_type, objective_coeffs, constraints):
    """
    Toma los datos crudos de la UI y los convierte en el
    diccionario estándar que usan todos los demás módulos.
    """

    objective = np.array(objective_coeffs, dtype=float)

    parsed_constraints = []

    for constraint in constraints:
        parsed_constraints.append({
            "coefficients": np.array(constraint["coeffs"], dtype=float),
            "operator": constraint["operator"],
            "rhs": float(constraint["rhs"]),
        })

    return {
        "type": problem_type,
        "objective": objective,
        "constraints": parsed_constraints,
    }
