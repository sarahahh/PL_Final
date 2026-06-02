# ============================================================
# graphics.py — Método gráfico de programación lineal
# ============================================================
# Solo funciona con problemas de 2 variables (x1, x2).
# No hay forma general de graficar en n dimensiones.

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def is_feasible_point(point, constraints, tolerance=1e-6):
    
    """
    Verifica si un punto (x1, x2) satisface TODAS las
    restricciones del problema, incluyendo la no negatividad.

    """

    x1, x2 = point

    if x1 < -tolerance or x2 < -tolerance:
        return False

    for constraint in constraints:
        a, b = constraint["coefficients"]
        operator = constraint["operator"]
        rhs = constraint["rhs"]

        value = a * x1 + b * x2

        if operator == "<=" and value > rhs + tolerance:
            return False

        if operator == ">=" and value < rhs - tolerance:
            return False

        if operator == "=" and abs(value - rhs) > tolerance:
            return False

    return True

def find_intersections(constraints):

    """
    Encuentra todas las intersecciones entre pares de rectas
    (restricciones y ejes coordenados).

    """

    lines = []

    for constraint in constraints:
        a, b = constraint["coefficients"]
        rhs = constraint["rhs"]
        lines.append((a, b, rhs))

    # Agregamos los ejes x1 = 0 y x2 = 0
    lines.append((1, 0, 0))
    lines.append((0, 1, 0))

    points = []

    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            a1, b1, c1 = lines[i]
            a2, b2, c2 = lines[j]

            matrix = np.array([
                [a1, b1],
                [a2, b2]
            ], dtype=float)

            vector = np.array([c1, c2], dtype=float)

            determinant = np.linalg.det(matrix)

            if abs(determinant) > 1e-9:
                solution = np.linalg.solve(matrix, vector)
                points.append(tuple(solution))

    return points

def get_feasible_vertices(constraints):

    """
    Filtra los puntos de intersección para quedarse solo
    con los que son vértices de la región factible.

    """
    candidate_points = find_intersections(constraints)
    feasible_points = []

    for point in candidate_points:
        if is_feasible_point(point, constraints):
            rounded_point = (
                round(point[0], 8),
                round(point[1], 8)
            )

            if rounded_point not in feasible_points:
                feasible_points.append(rounded_point)

    return feasible_points

def evaluate_objective(point, objective):

    """
    Calcula Z = c1*x1 + c2*x2 para un punto dado.

    """

    x1, x2 = point
    return objective[0] * x1 + objective[1] * x2


def find_optimal_vertex(vertices, objective, problem_type):
    
    """
    Evalúa Z en todos los vértices y retorna el óptimo.

    """

    if not vertices:
        return None, None

    values = []

    for point in vertices:
        z_value = evaluate_objective(point, objective)
        values.append(z_value)

    if problem_type == "Maximizar":
        best_index = int(np.argmax(values))
    else:
        best_index = int(np.argmin(values))

    return vertices[best_index], values[best_index]


def order_vertices(vertices):

    """
    Ordena los vértices en sentido antihorario para
    que matplotlib pueda sombrear el polígono correctamente.

    """

    center_x = sum(point[0] for point in vertices) / len(vertices)
    center_y = sum(point[1] for point in vertices) / len(vertices)

    def angle_from_center(point):
        return np.arctan2(point[1] - center_y, point[0] - center_x)

    return sorted(vertices, key=angle_from_center)


def plot_graphical_solution(
    objective,
    constraints,
    vertices,
    optimal_point,
    optimal_value,
    problem_type
):
    """
    Genera la gráfica completa con matplotlib.

    """
    fig, ax = plt.subplots(figsize=(8, 6))

    max_value = 10

    if vertices:
        max_x = max(point[0] for point in vertices)
        max_y = max(point[1] for point in vertices)
        max_value = max(max_x, max_y, 10) * 1.2

    x = np.linspace(0, max_value, 400)

    for index, constraint in enumerate(constraints):
        a, b = constraint["coefficients"]
        operator = constraint["operator"]
        rhs = constraint["rhs"]

        if abs(b) > 1e-9:
            y = (rhs - a * x) / b
            ax.plot(
                x,
                y,
                label=f"R{index + 1}: {a}x1 + {b}x2 {operator} {rhs}"
            )
        else:
            if abs(a) > 1e-9:
                x_line = rhs / a
                ax.axvline(
                    x=x_line,
                    label=f"R{index + 1}: {a}x1 {operator} {rhs}"
                )

    if len(vertices) >= 3:
        ordered_vertices = order_vertices(vertices)
        polygon = np.array(ordered_vertices)

        ax.fill(
            polygon[:, 0],
            polygon[:, 1],
            alpha=0.25,
            label="Región factible"
        )

    for point in vertices:
        ax.scatter(point[0], point[1])
        ax.text(
            point[0],
            point[1],
            f"({point[0]:.2f}, {point[1]:.2f})"
        )

    if optimal_point is not None:
        ax.scatter(
            optimal_point[0],
            optimal_point[1],
            s=150,
            marker="*",
            label=f"Óptimo: Z = {optimal_value:.2f}"
        )
    
    if optimal_point is not None and abs(objective[1]) > 1e-9:
        # Despejamos x2: x2 = (Z_opt - c1*x1) / c2
        y_iso = (optimal_value - objective[0] * x) / objective[1]

        ax.plot(
            x,
            y_iso,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Isobeneficio: Z = {optimal_value:.2f}"
        )

    elif optimal_point is not None and abs(objective[1]) <= 1e-9:
        # Si c2 = 0, la recta es vertical: x1 = Z_opt / c1
        if abs(objective[0]) > 1e-9:
            x_iso = optimal_value / objective[0]
            ax.axvline(
                x=x_iso,
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Isobeneficio: Z = {optimal_value:.2f}"
            )

    ax.set_xlim(0, max_value)
    ax.set_ylim(0, max_value)
    ax.set_xlabel("x1")
    ax.set_ylabel("x2")
    ax.set_title(f"Método gráfico - {problem_type}")
    ax.grid(True)
    ax.legend()

    return fig

#funcion principal 
def solve_graphical_method(objective, constraints, problem_type):
    
    """
    Función principal del módulo: orquesta todo el proceso
    gráfico y retorna un diccionario con los resultados.

    """

    vertices = get_feasible_vertices(constraints)

    optimal_point, optimal_value = find_optimal_vertex(
        vertices,
        objective,
        problem_type
    )

    table_data = []

    for point in vertices:
        z_value = evaluate_objective(point, objective)

        table_data.append({
            "x1": point[0],
            "x2": point[1],
            "Z": z_value
        })

    vertices_table = pd.DataFrame(table_data)

    if not vertices_table.empty:
        vertices_table = vertices_table.sort_values(
        by=["x1", "x2"],
        ascending=[True, True]
        ).reset_index(drop=True)

    fig = plot_graphical_solution(
        objective,
        constraints,
        vertices,
        optimal_point,
        optimal_value,
        problem_type
    )

    return {
        "vertices": vertices,
        "vertices_table": vertices_table,
        "optimal_point": optimal_point,
        "optimal_value": optimal_value,
        "figure": fig
    }