# ============================================================
# app.py — Interfaz principal (Streamlit)
# ============================================================
# Proyecto unificado de Programación Lineal:
#   - Método gráfico (2 variables) con explicación paso a paso.
#   - Método Simplex con Gran M: <=, >=, = y max/min.
#   - Análisis de sensibilidad (precios sombra, costos reducidos).

import streamlit as st
import pandas as pd
import numpy as np

from simplex.parser import build_problem
from simplex.simplex_solver import SimplexSolver
from simplex.graphics import solve_graphical_method
from simplex.sensitivity import show_sensitivity_analysis


st.set_page_config(page_title="Simplex Optimizer", layout="wide")

st.title("Simplex Optimizer")
st.write("Ingrese un problema de Programación Lineal")


# =========================
# FUNCIONES AUXILIARES
# =========================

def format_objective(objective, problem_type):
    """Convierte la función objetivo en notación matemática (LaTeX)."""
    terms = [f"{coefficient}x_{i + 1}" for i, coefficient in enumerate(objective)]
    return f"{problem_type} \\ Z = " + " + ".join(terms)


def format_constraint(constraint):
    """Convierte un diccionario de restricción en un string matemático."""
    terms = [
        f"{coefficient}x_{i + 1}"
        for i, coefficient in enumerate(constraint["coefficients"])
    ]
    left_side = " + ".join(terms)
    return f"{left_side} {constraint['operator']} {constraint['rhs']}"


def build_tableau_dataframe(tableau, basic_variables, variable_names):
    """
    Convierte el tablero (matriz numpy) en un DataFrame con
    nombres de columna dinámicos. Usa variable_names para soportar
    holguras (S), excesos (E) y artificiales (A), no solo X/S.
    """
    column_names = list(variable_names) + ["RHS"]
    tableau_df = pd.DataFrame(tableau, columns=column_names)
    tableau_df.index = list(basic_variables) + ["Z"]
    return tableau_df.round(4)

# ← AGREGA ESTA FUNCIÓN NUEVA JUSTO AQUÍ
def style_tableau(df, entering_variable=None, leaving_variable=None):
    """
    Colorea el tablero para destacar la columna y fila pivote.
        - Columna (variable que entra) → azul claro
        - Fila (variable que sale)     → naranja claro
        - Intersección (pivote)        → rojo, negrita
    """
    styles = pd.DataFrame("", index=df.index, columns=df.columns)

    if entering_variable and entering_variable in df.columns:
        styles[entering_variable] = "background-color: #bbdefb; color: black"

    if leaving_variable and leaving_variable in df.index:
        styles.loc[leaving_variable] = "background-color: #ffe0b2; color: black"

    if (entering_variable and leaving_variable
            and entering_variable in df.columns
            and leaving_variable in df.index):
        styles.loc[leaving_variable, entering_variable] = (
            "background-color: #ef9a9a; color: black; font-weight: bold"
        )

    return df.style.apply(lambda _: styles, axis=None)

def show_simplex_iterations(result, problem_data):
    """Muestra el proceso simplex paso a paso (tablero por tablero)."""

    num_constraints = len(problem_data["constraints"])

    st.subheader("Solución numérica paso a paso - Método Simplex (Gran M)")

    # Aviso de infactibilidad
    if result.get("status") == "infactible":
        nombres = ", ".join(
            f"{n} = {v:.4f}" for n, v in result["infeasible_artificials"]
        )
        st.error(
            "El problema NO tiene solución factible: en la base final "
            f"quedaron variables artificiales con valor positivo ({nombres}). "
            "Esto significa que las restricciones se contradicen entre sí."
        )

    # =========================
    # RESULTADO ÓPTIMO
    # =========================
    st.write("### Resultado óptimo")

    solution_data = [
        {"Variable": f"X{i + 1}", "Valor": round(value, 4)}
        for i, value in enumerate(result["solution"])
    ]
    st.dataframe(pd.DataFrame(solution_data), use_container_width=True)

    st.success(f"Valor óptimo: Z = {result['optimal_value']:.4f}")

    if problem_data["type"] == "Minimizar":
        st.caption(
            "Nota: para minimizar se resolvió el problema equivalente "
            "max(-Z); por eso la última celda del tablero muestra el valor "
            "negado. El valor de Z mostrado arriba ya está corregido."
        )

    # =========================
    # HOLGURAS EN LA BASE FINAL
    # =========================
    st.write("### Variables de holgura en la solución final")

    slack_data = []
    for i, variable_name in enumerate(result["basic_variables"]):
        if variable_name.startswith("S"):
            slack_data.append({
                "Variable de holgura": variable_name,
                "Valor": round(result["tableau"][i, -1], 4),
                "Interpretación": "Recurso no utilizado",
            })

    if slack_data:
        st.dataframe(pd.DataFrame(slack_data), use_container_width=True)
    else:
        st.info("No hay variables de holgura positivas en la base final.")

    # =========================
    # ITERACIONES
    # =========================
    st.write("### Iteraciones del método simplex")

    # Convertimos la lista a una lista indexable para poder mirar
    # el tablero ANTERIOR al pivoteo de cada iteración
    iterations = result["iterations"]

    for idx, step in enumerate(iterations):

        st.write(f"#### Iteración {step['iteration']}")
        st.info(step["message"])

        if step["entering_variable"] is not None:

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Variable que entra", step["entering_variable"])
            with col2:
                st.metric("Variable que sale", step["leaving_variable"])
            with col3:
                st.metric("Elemento pivote", round(step["pivot_element"], 4))

            ratio_data = []
            basic_before = step.get(
                "basic_variables_before", step["basic_variables"]
            )
            for i, ratio in enumerate(step["ratios"]):
                ratio_value = "-" if np.isinf(ratio) else round(ratio, 4)
                ratio_data.append({
                    "Fila": basic_before[i],
                    "Razón RHS / columna pivote": ratio_value,
                })

            st.write("##### Prueba de razón mínima")
            st.dataframe(pd.DataFrame(ratio_data), use_container_width=True)

        # ── Tablero con colores ──────────────────────────────
        # Para la iteración 0: mostramos su tablero con los colores
        # del pivote que SE VA A HACER (datos del step siguiente)
        # Para las demás: mostramos el tablero del step actual
        # con los colores del pivote que SE HIZO para llegar aquí
        # (datos del step actual)
        # Esto replica exactamente las diapositivas del profe:
        # cada tablero muestra resaltado el pivote de ESA iteración.

        if idx < len(iterations) - 1:
            # Hay una iteración siguiente → coloreamos con el pivote
            # que se va a realizar (step siguiente)
            next_step = iterations[idx + 1]
            entering = next_step.get("entering_variable")
            leaving = next_step.get("leaving_variable")
        else:
            # Último tablero → no hay pivote siguiente, sin color
            entering = None
            leaving = None

        df_step = build_tableau_dataframe(
            tableau=step["tableau"],
            basic_variables=step["basic_variables"],
            variable_names=result["variable_names"],
        )

        st.write("##### Tablero simplex")
        if entering:
            st.dataframe(
                style_tableau(df_step, entering, leaving),
                use_container_width=True,
            )
        else:
            st.dataframe(df_step, use_container_width=True)

    # =========================
    # TABLERO FINAL
    # =========================
    st.write("### Tablero simplex final")
    st.dataframe(
        build_tableau_dataframe(
            tableau=result["tableau"],
            basic_variables=result["basic_variables"],
            variable_names=result["variable_names"],
        ),
        use_container_width=True,
    )
    st.info(
        "En el tablero final, las filas indican las variables básicas y la "
        "columna RHS su valor. La última fila corresponde a la función objetivo."
    )


# =========================
# CONFIGURACIÓN GENERAL
# =========================

problem_type = st.selectbox("Tipo de problema", ["Maximizar", "Minimizar"])

num_variables = st.number_input(
    "Número de variables", min_value=2, max_value=10, value=2, step=1
)

num_constraints = st.number_input(
    "Número de restricciones", min_value=1, max_value=10, value=2, step=1
)

solution_method = st.selectbox(
    "Seleccione el método de solución",
    ["Método numérico paso a paso", "Método gráfico", "Ambos"],
)

st.divider()


# =========================
# FUNCIÓN OBJETIVO
# =========================

st.subheader("Función Objetivo")

objective_coeffs = []
cols = st.columns(num_variables)
for i in range(num_variables):
    coeff = cols[i].number_input(f"X{i + 1}", value=0.0, key=f"obj_{i}")
    objective_coeffs.append(coeff)

st.latex(
    "Z = " + " + ".join(
        [f"{objective_coeffs[i]}x_{i + 1}" for i in range(num_variables)]
    )
)

st.divider()


# =========================
# RESTRICCIONES
# =========================

st.subheader("Restricciones")

constraints = []
for r in range(num_constraints):
    st.markdown(f"### Restricción {r + 1}")
    row = st.columns(num_variables + 2)

    coeffs = []
    for c in range(num_variables):
        value = row[c].number_input(f"X{c + 1}", value=0.0, key=f"r{r}c{c}")
        coeffs.append(value)

    operator = row[num_variables].selectbox(
        "Operador", ["<=", ">=", "="], key=f"op_{r}"
    )
    rhs = row[num_variables + 1].number_input("Resultado", value=0.0, key=f"rhs_{r}")

    constraints.append({"coeffs": coeffs, "operator": operator, "rhs": rhs})

st.divider()


# =========================
# BOTÓN RESOLVER
# =========================

if st.button("Resolver Problema"):

    try:

        problem_data = build_problem(problem_type, objective_coeffs, constraints)

        st.success("Problema cargado correctamente")

        st.subheader("Resumen del Problema")
        st.write("### Tipo")
        st.write(problem_data["type"])
        st.write("### Función Objetivo")
        st.latex(format_objective(problem_data["objective"], problem_data["type"]))
        st.write("### Restricciones")
        for i, constraint in enumerate(problem_data["constraints"]):
            st.latex(f"R_{i + 1}: " + format_constraint(constraint))

        show_numeric = solution_method in ["Método numérico paso a paso", "Ambos"]
        show_graphical = solution_method in ["Método gráfico", "Ambos"]

        # =========================
        # MÉTODO GRÁFICO (paso a paso, estilo A)
        # =========================
        if show_graphical:

            if num_variables == 2:

                st.subheader("Método gráfico paso a paso")

                graphical_result = solve_graphical_method(
                    objective=problem_data["objective"],
                    constraints=problem_data["constraints"],
                    problem_type=problem_data["type"],
                )

                st.write("## Paso 1: Modelo ingresado")
                st.write("### Función objetivo")
                st.latex(format_objective(problem_data["objective"], problem_data["type"]))
                st.write("### Restricciones")
                for i, constraint in enumerate(problem_data["constraints"]):
                    st.latex(f"R_{i + 1}: " + format_constraint(constraint))

                st.write("## Paso 2: Rectas frontera")
                st.info(
                    "Cada restricción se toma como recta frontera (igualdad) "
                    "y luego se identifica el lado factible."
                )
                for i, constraint in enumerate(problem_data["constraints"]):
                    frontera = constraint.copy()
                    frontera["operator"] = "="
                    st.latex(f"R_{i + 1}: " + format_constraint(frontera))

                st.write("## Paso 3: Vértices factibles encontrados")

                if graphical_result["vertices_table"].empty:
                    st.error(
                        "No se encontraron vértices factibles. El problema "
                        "puede no tener región factible."
                    )
                else:
                    st.dataframe(
                        graphical_result["vertices_table"], use_container_width=True
                    )

                    st.write("## Paso 4: Evaluación de la función objetivo")
                    criterio = "mayor" if problem_data["type"] == "Maximizar" else "menor"
                    st.info(
                        f"La columna Z muestra el valor de la función objetivo en "
                        f"cada vértice. Como el problema es de "
                        f"{problem_data['type'].lower()}, se elige el vértice con el "
                        f"{criterio} valor de Z."
                    )

                    x1, x2 = graphical_result["optimal_point"]
                    st.write("### Vértice seleccionado")
                    st.latex(f"({x1:.2f}, {x2:.2f})")
                    st.write("### Valor de la función objetivo")
                    st.latex(f"Z = {graphical_result['optimal_value']:.2f}")

                    st.write("## Paso 5: Conclusión")
                    st.success(
                        f"La solución óptima es x1 = {x1:.2f} y x2 = {x2:.2f}, "
                        f"con Z = {graphical_result['optimal_value']:.2f}."
                    )

                    st.write("## Paso 6: Gráfica de la región factible")
                    st.pyplot(graphical_result["figure"])

            else:
                st.warning(
                    "El método gráfico solo aplica para problemas con dos variables."
                )

        # =========================
        # MÉTODO NUMÉRICO SIMPLEX + GRAN M
        # =========================
        if show_numeric:

            solver_objective = problem_data["objective"].copy()
            is_minimization = problem_data["type"] == "Minimizar"

            # min c·x  =  -max(-c·x): se niega el objetivo para el solver
            if is_minimization:
                solver_objective = -solver_objective

            solver = SimplexSolver(
                objective=solver_objective,
                constraints=problem_data["constraints"],
            )
            result = solver.solve()

            # Recuperar el valor real de Z para minimización
            if is_minimization:
                result["optimal_value"] *= -1

            show_simplex_iterations(result=result, problem_data=problem_data)

            show_sensitivity_analysis(result=result, problem_data=problem_data)

    except Exception as error:
        st.error(f"Error: {str(error)}")
