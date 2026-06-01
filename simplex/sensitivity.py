# ============================================================
# sensitivity.py — Análisis de sensibilidad
# ============================================================
# Calcula el análisis a partir del tablero INICIAL del solver
# (que ya contiene todas las columnas: X, holguras S, excesos E
# y artificiales A con sus signos +1/-1 correctos) y de la base
# final. Esto lo hace válido para restricciones <=, >= y =,
# y tanto para maximización como minimización.
#
# Idea matricial estándar:
#   B      = columnas de A correspondientes a la base final
#   B_inv  = inversa de B
#   Cb     = costos ORIGINALES de las variables básicas
#   xB     = B_inv · b                  (valores de las básicas)
#   y      = Cb · B_inv                 (precios sombra / dual)
#   z_j-c_j= Cb · B_inv · A_j - c_j     (costos reducidos)
#
# Se usan los costos ORIGINALES del problema (no los negados que
# app.py pasa al solver en minimización), de modo que el dual
# corresponde al problema tal como lo planteó el usuario.

import streamlit as st
import pandas as pd
import numpy as np


def compute_sensitivity(result, problem_data):
    """
    Devuelve un diccionario con los datos del análisis de
    sensibilidad, o None en cada bloque que no se pueda calcular.
    No usa Streamlit: es testeable de forma aislada.
    """

    constraints = problem_data["constraints"]
    num_constraints = len(constraints)

    objective = np.array(problem_data["objective"], dtype=float)
    num_variables = len(objective)

    variable_names = result["variable_names"]
    basic_variables = result["basic_variables"]

    # Tablero inicial: filas de restricción = matriz A aumentada, b = RHS
    initial = result["initial_tableau"]
    A_full = initial[:-1, :-1].astype(float)
    b = initial[:-1, -1].astype(float)

    total_cols = A_full.shape[1]

    # Vector de costos extendido (0 para S, E, A; costo original para X)
    c_full = np.zeros(total_cols)
    c_full[:num_variables] = objective

    # Índices de columna de cada variable básica (en el mismo orden de filas)
    try:
        basic_indices = [variable_names.index(name) for name in basic_variables]
    except ValueError:
        return {"ok": False}

    B = A_full[:, basic_indices]

    try:
        B_inv = np.linalg.inv(B)
    except np.linalg.LinAlgError:
        return {"ok": False}

    Cb = c_full[basic_indices]

    shadow_prices = Cb @ B_inv                      # dual por restricción
    xB = B_inv @ b                                  # valores de las básicas
    reduced_costs = (Cb @ B_inv @ A_full) - c_full  # costos reducidos

    return {
        "ok": True,
        "shadow_prices": shadow_prices,
        "xB": xB,
        "reduced_costs": reduced_costs,
        "variable_names": variable_names,
        "basic_variables": basic_variables,
        "num_constraints": num_constraints,
    }


def build_slack_table(result, problem_data):
    """Holgura/exceso por restricción evaluando la solución final."""
    constraints = problem_data["constraints"]
    solution = result["solution"]

    rows = []
    for i, constraint in enumerate(constraints):
        coefficients = np.array(constraint["coefficients"], dtype=float)
        rhs = float(constraint["rhs"])
        operator = constraint["operator"]

        lhs = float(np.dot(coefficients, solution))

        if operator == "<=":
            slack = rhs - lhs
            tipo = "Holgura"
        elif operator == ">=":
            slack = lhs - rhs
            tipo = "Exceso"
        else:
            slack = abs(lhs - rhs)
            tipo = "—"

        if abs(slack) < 1e-6:
            slack = 0.0
            estado = "Restricción activa (saturada)"
        else:
            estado = "Restricción no activa (recurso/sobrante)"

        rows.append({
            "Restricción": f"R{i + 1}",
            "Tipo": tipo,
            "Holgura/Exceso": round(slack, 4),
            "Estado": estado,
        })

    return pd.DataFrame(rows)


def show_sensitivity_analysis(result, problem_data):
    """Renderiza el análisis de sensibilidad en Streamlit."""

    st.subheader("Análisis de sensibilidad")

    if result.get("status") == "infactible":
        st.error(
            "El problema es infactible, por lo que el análisis de "
            "sensibilidad no aplica."
        )
        return

    # -----------------------------------------------------
    # HOLGURAS / EXCESOS
    # -----------------------------------------------------
    st.write("### Holguras y excesos de las restricciones")
    st.dataframe(
        build_slack_table(result, problem_data),
        use_container_width=True,
    )

    # -----------------------------------------------------
    # ANÁLISIS MATRICIAL
    # -----------------------------------------------------
    data = compute_sensitivity(result, problem_data)

    if not data.get("ok"):
        st.warning(
            "No fue posible calcular el análisis matricial "
            "(la base final no produjo una matriz invertible)."
        )
        return

    num_constraints = data["num_constraints"]

    # Precios sombra
    st.write("### Precios sombra (valores duales)")
    shadow_df = pd.DataFrame([
        {"Restricción": f"R{i + 1}", "Precio sombra": round(v, 4)}
        for i, v in enumerate(data["shadow_prices"])
    ])
    st.dataframe(shadow_df, use_container_width=True)

    # Costos reducidos (con nombres reales de variable)
    st.write("### Costos reducidos")
    reduced_df = pd.DataFrame([
        {"Variable": data["variable_names"][j], "Costo reducido": round(v, 4)}
        for j, v in enumerate(data["reduced_costs"])
    ])
    st.dataframe(reduced_df, use_container_width=True)

    # Valores de las variables básicas (RHS)
    st.write("### Valores de las variables básicas (lado derecho)")
    rhs_df = pd.DataFrame([
        {
            "Variable básica": data["basic_variables"][i],
            "Valor": round(data["xB"][i], 4),
            "Condición": "Debe permanecer ≥ 0",
        }
        for i in range(num_constraints)
    ])
    st.dataframe(rhs_df, use_container_width=True)

    # -----------------------------------------------------
    # INTERPRETACIÓN
    # -----------------------------------------------------
    st.write("### Interpretación económica")
    st.info(
        "Una restricción está **activa** cuando su holgura/exceso es 0: "
        "el recurso se usa por completo."
    )
    st.info(
        "El **precio sombra** indica en cuánto cambia el valor óptimo de Z "
        "por cada unidad adicional del lado derecho de esa restricción."
    )
    st.info(
        "El **costo reducido** de una variable no básica indica cuánto "
        "tendría que mejorar su coeficiente para que entre a la solución."
    )
