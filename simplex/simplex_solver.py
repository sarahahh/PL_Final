# ============================================================
# simplex_solver.py — Método Simplex con Gran M (Big M)
# ============================================================
# Implementa el método Simplex en formato de tabla para:
#   - Maximización y minimización (la minimización se maneja
#     en app.py negando el objetivo: min c·x = -max(-c·x)).
#   - Restricciones <=, >= y =.
#
# Variables que agrega automáticamente:
#   <=  -> 1 variable de HOLGURA  (S)
#   >=  -> 1 variable de EXCESO (E) + 1 ARTIFICIAL (A)
#   =   -> 1 variable ARTIFICIAL (A)
#
# Convenio de la fila objetivo (fila Z):
#   Se almacena -c para las variables de decisión. La solución
#   es óptima cuando NO hay coeficientes negativos en la fila Z.
#   Entra la variable con el coeficiente MÁS negativo.
#
# Penalización Gran M:
#   En este convenio, la columna de cada variable artificial
#   vale +M en la fila Z, y se vuelve canónica (0 en su columna
#   básica) RESTANDO M * fila_de_la_artificial a la fila Z.
#   Esto deja las columnas estructurales en -c_j - M*a_ij, de modo
#   que el algoritmo prefiere meter variables reales y expulsa las
#   artificiales.  <-- Aquí estaba el bug del proyecto original:
#   usaba -M y suma, lo que invertía el incentivo y dejaba las
#   artificiales atrapadas en la base.

import numpy as np


class SimplexSolver:

    def __init__(self, objective, constraints, big_m=1e4):

        self.objective = np.array(objective, dtype=float)
        self.constraints = constraints

        self.num_variables = len(objective)

        # Valor de la "M grande". 1e4 es suficiente para los
        # problemas académicos de coeficientes pequeños y mantiene
        # el tablero numéricamente estable.
        self.M = big_m

        self.variable_names = []
        self.basic_variables = []
        self.artificial_names = []   # para detectar infactibilidad al final

        self.tableau = None

    # ==================================================
    # CONSTRUIR TABLERO INICIAL CON GRAN M
    # ==================================================

    def create_tableau(self):

        num_constraints = len(self.constraints)

        artificial_rows = []

        # ------------------------------------------------
        # CONTAR COLUMNAS EXTRA SEGÚN EL OPERADOR
        # ------------------------------------------------

        extra_variables = 0

        for constraint in self.constraints:

            operator = constraint["operator"]

            if operator == "<=":
                extra_variables += 1            # holgura
            elif operator == ">=":
                extra_variables += 2            # exceso + artificial
            elif operator == "=":
                extra_variables += 1            # artificial

        total_columns = self.num_variables + extra_variables + 1

        rows = num_constraints + 1

        tableau = np.zeros((rows, total_columns))

        # ------------------------------------------------
        # VARIABLES DE DECISIÓN (X1..Xn)
        # ------------------------------------------------

        for i in range(self.num_variables):
            self.variable_names.append(f"X{i + 1}")

        current_col = self.num_variables

        slack_count = 0
        excess_count = 0
        artificial_count = 0

        # ------------------------------------------------
        # FILAS DE RESTRICCIONES
        # ------------------------------------------------

        for row_index, constraint in enumerate(self.constraints):

            coeffs = constraint["coefficients"]
            operator = constraint["operator"]
            rhs = float(constraint["rhs"])

            # Normalizamos el RHS a no negativo. Si rhs < 0 se
            # multiplica la restricción por -1 y se invierte el operador.
            if rhs < 0:
                coeffs = -np.array(coeffs, dtype=float)
                rhs = -rhs
                if operator == "<=":
                    operator = ">="
                elif operator == ">=":
                    operator = "<="

            tableau[row_index, :self.num_variables] = coeffs
            tableau[row_index, -1] = rhs

            if operator == "<=":

                # Holgura: + S, entra a la base inicial
                tableau[row_index, current_col] = 1
                slack_count += 1
                slack_name = f"S{slack_count}"
                self.variable_names.append(slack_name)
                self.basic_variables.append(slack_name)
                current_col += 1

            elif operator == ">=":

                # Exceso: - E (no entra a la base inicial)
                tableau[row_index, current_col] = -1
                excess_count += 1
                excess_name = f"E{excess_count}"
                self.variable_names.append(excess_name)
                current_col += 1

                # Artificial: + A (entra a la base inicial)
                tableau[row_index, current_col] = 1
                artificial_count += 1
                artificial_name = f"A{artificial_count}"
                self.variable_names.append(artificial_name)
                self.artificial_names.append(artificial_name)
                self.basic_variables.append(artificial_name)
                artificial_rows.append(row_index)
                current_col += 1

            elif operator == "=":

                # Artificial: + A (entra a la base inicial)
                tableau[row_index, current_col] = 1
                artificial_count += 1
                artificial_name = f"A{artificial_count}"
                self.variable_names.append(artificial_name)
                self.artificial_names.append(artificial_name)
                self.basic_variables.append(artificial_name)
                artificial_rows.append(row_index)
                current_col += 1

        # ------------------------------------------------
        # FILA OBJETIVO (fila Z)
        # ------------------------------------------------

        # Variables de decisión: -c
        tableau[-1, :self.num_variables] = -self.objective

        # Penalización M en las columnas artificiales: +M
        # (CORRECCIÓN: el proyecto original usaba -M)
        for col_index, variable_name in enumerate(self.variable_names):
            if variable_name.startswith("A"):
                tableau[-1, col_index] = self.M

        # Volver canónica la fila Z respecto de las artificiales básicas:
        # se RESTA M * fila_artificial para anular su columna.
        # (CORRECCIÓN: el proyecto original sumaba)
        for row_index in artificial_rows:
            tableau[-1] = tableau[-1] - self.M * tableau[row_index]

        self.tableau = tableau

    # ==================================================
    # UTILIDADES
    # ==================================================

    def get_variable_name(self, column_index):
        return self.variable_names[column_index]

    def is_optimal(self):
        last_row = self.tableau[-1, :-1]
        return np.all(last_row >= -1e-9)

    def get_pivot_column(self):
        last_row = self.tableau[-1, :-1]
        return int(np.argmin(last_row))

    def get_ratios(self, pivot_col):
        """Razones RHS / columna pivote (solo para elementos > 0)."""
        ratios = []
        for i in range(len(self.constraints)):
            element = self.tableau[i, pivot_col]
            if element > 1e-12:
                ratios.append(self.tableau[i, -1] / element)
            else:
                ratios.append(np.inf)
        return ratios

    def get_pivot_row(self, pivot_col):
        ratios = self.get_ratios(pivot_col)
        pivot_row = int(np.argmin(ratios))
        if np.isinf(ratios[pivot_row]):
            raise Exception(
                "El problema es no acotado: la columna pivote no tiene "
                "ninguna razón finita positiva."
            )
        return pivot_row

    def pivot(self, pivot_row, pivot_col):
        pivot_element = self.tableau[pivot_row, pivot_col]
        self.tableau[pivot_row] = self.tableau[pivot_row] / pivot_element
        for i in range(len(self.tableau)):
            if i != pivot_row:
                factor = self.tableau[i, pivot_col]
                self.tableau[i] = (
                    self.tableau[i] - factor * self.tableau[pivot_row]
                )

    # ==================================================
    # RESOLVER
    # ==================================================

    def solve(self):

        self.create_tableau()

        iterations = []

        iterations.append({
            "iteration": 0,
            "tableau": self.tableau.copy(),
            "basic_variables": self.basic_variables.copy(),
            "basic_variables_before": self.basic_variables.copy(),
            "entering_variable": None,
            "leaving_variable": None,
            "pivot_element": None,
            "ratios": None,
            "message": (
                "Tablero inicial en forma aumentada (con holguras, "
                "excesos y artificiales). Se buscan coeficientes negativos "
                "en la fila Z."
            )
        })

        max_iterations = 200
        iteration_count = 0

        while not self.is_optimal():

            iteration_count += 1
            if iteration_count > max_iterations:
                raise Exception(
                    "Se superó el número máximo de iteraciones. "
                    "Posible ciclado o problema mal planteado."
                )

            pivot_col = self.get_pivot_column()
            pivot_row = self.get_pivot_row(pivot_col)
            ratios = self.get_ratios(pivot_col)

            entering_variable = self.get_variable_name(pivot_col)
            leaving_variable = self.basic_variables[pivot_row]
            pivot_element = self.tableau[pivot_row, pivot_col]

            basic_variables_before = self.basic_variables.copy()
            self.basic_variables[pivot_row] = entering_variable

            self.pivot(pivot_row, pivot_col)

            iterations.append({
                "iteration": iteration_count,
                "tableau": self.tableau.copy(),
                "basic_variables": self.basic_variables.copy(),
                "basic_variables_before": basic_variables_before,
                "entering_variable": entering_variable,
                "leaving_variable": leaving_variable,
                "pivot_element": pivot_element,
                "ratios": ratios,
                "message": (
                    f"Entra {entering_variable}, sale {leaving_variable}. "
                    f"Elemento pivote = {pivot_element:.4f}."
                )
            })

        # ------------------------------------------------
        # EXTRAER SOLUCIÓN
        # ------------------------------------------------

        solution = np.zeros(self.num_variables)
        for row_index, variable_name in enumerate(self.basic_variables):
            if variable_name.startswith("X"):
                variable_index = int(variable_name[1:]) - 1
                if variable_index < self.num_variables:
                    solution[variable_index] = self.tableau[row_index, -1]

        optimal_value = self.tableau[-1, -1]

        # ------------------------------------------------
        # DETECCIÓN DE INFACTIBILIDAD
        # ------------------------------------------------
        # Si alguna variable artificial sigue en la base con valor > 0,
        # el problema original NO tiene solución factible.
        status = "optimo"
        infeasible_artificials = []
        for row_index, variable_name in enumerate(self.basic_variables):
            if variable_name.startswith("A"):
                value = self.tableau[row_index, -1]
                if value > 1e-6:
                    status = "infactible"
                    infeasible_artificials.append((variable_name, value))

        return {
            "solution": solution,
            "optimal_value": optimal_value,
            "tableau": self.tableau,
            "iterations": iterations,
            "basic_variables": self.basic_variables,
            "variable_names": self.variable_names,
            "artificial_names": self.artificial_names,
            "status": status,
            "infeasible_artificials": infeasible_artificials,
            "initial_tableau": iterations[0]["tableau"],
        }
