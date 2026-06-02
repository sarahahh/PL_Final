# ============================================================
# sensitivity.py — Análisis de sensibilidad
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np


def compute_sensitivity(result, problem_data):

    constraints = problem_data["constraints"]
    num_constraints = len(constraints)

    objective = np.array(problem_data["objective"], dtype=float)
    num_variables = len(objective)

    variable_names = result["variable_names"]
    basic_variables = result["basic_variables"]

    initial = result["initial_tableau"]
    A_full = initial[:-1, :-1].astype(float)
    b = initial[:-1, -1].astype(float)

    total_cols = A_full.shape[1]

    c_full = np.zeros(total_cols)
    c_full[:num_variables] = objective

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

    shadow_prices = Cb @ B_inv
    xB = B_inv @ b
    reduced_costs = (Cb @ B_inv @ A_full) - c_full

    # ── Rangos de cj ─────────────────────────────────────────
    cj_ranges = []

    for j in range(num_variables):
        cj = objective[j]
        var_name = variable_names[j]

        if var_name not in basic_variables:
            # Variable NO básica:
            # rc_j >= 0  →  cj <= Cb·B_inv·aj  →  solo cota superior
            cj_max = cj + reduced_costs[j]
            cj_ranges.append({
                "Variable": var_name,
                "cj actual": round(cj, 4),
                "Límite inferior": "-∞",
                "Límite superior": round(cj_max, 4),
            })

        else:
            # Variable BÁSICA en fila k:
            # Al cambiar cj en Δ, el costo reducido de cada no básica p cambia:
            #   rc_p_nuevo = rc_p - Δ * (B_inv · ap)[k]
            # Para rc_p_nuevo >= 0 calculamos los Δ admisibles.
            # Usamos todas las no básicas con rc >= 0 (excluimos artificiales
            # y variables con costos reducidos negativos por la M grande).
            k = basic_variables.index(var_name)

            non_basic_indices = [
                i for i in range(total_cols)
                if i not in basic_indices
                and not variable_names[i].startswith("A")
                and reduced_costs[i] >= -1e-6
            ]

            deltas_pos = []
            deltas_neg = []

            for p in non_basic_indices:
                rc_p = reduced_costs[p]
                coef_k = (B_inv @ A_full[:, p])[k]

                if abs(coef_k) < 1e-10:
                    continue

                delta_limit = -rc_p / coef_k

                if coef_k > 0:
                    deltas_neg.append(delta_limit)   # cota inferior
                else:
                    deltas_pos.append(delta_limit)   # cota superior

            delta_max = min(deltas_pos) if deltas_pos else np.inf
            delta_min = max(deltas_neg) if deltas_neg else -np.inf

            cj_min = cj + delta_min
            cj_max = cj + delta_max

            cj_ranges.append({
                "Variable": var_name,
                "cj actual": round(cj, 4),
                "Límite inferior": round(cj_min, 4) if not np.isinf(cj_min) else "-∞",
                "Límite superior": round(cj_max, 4) if not np.isinf(cj_max) else "+∞",
            })

    # ── Rangos de bi ─────────────────────────────────────────
    # Al cambiar bi en Δ: xB_nuevo = xB + Δ * (col i de B_inv)
    # Para xB_nuevo >= 0 calculamos los Δ admisibles.
    bi_ranges = []

    for i in range(num_constraints):
        bi = float(constraints[i]["rhs"])
        col_i = B_inv[:, i]

        deltas_pos = []
        deltas_neg = []

        for k in range(num_constraints):
            if abs(col_i[k]) < 1e-10:
                continue
            delta_limit = -xB[k] / col_i[k]
            if col_i[k] > 0:
                deltas_neg.append(delta_limit)
            else:
                deltas_pos.append(delta_limit)

        delta_max = min(deltas_pos) if deltas_pos else np.inf
        delta_min = max(deltas_neg) if deltas_neg else -np.inf

        bi_min = bi + delta_min
        bi_max = bi + delta_max

        bi_ranges.append({
            "Restricción": f"R{i + 1}",
            "bi actual": round(bi, 4),
            "Límite inferior": round(bi_min, 4) if not np.isinf(bi_min) else "-∞",
            "Límite superior": round(bi_max, 4) if not np.isinf(bi_max) else "+∞",
        })

    return {
        "ok": True,
        "shadow_prices": shadow_prices,
        "xB": xB,
        "reduced_costs": reduced_costs,
        "variable_names": variable_names,
        "basic_variables": basic_variables,
        "num_constraints": num_constraints,
        "cj_ranges": cj_ranges,
        "bi_ranges": bi_ranges,
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
            estado = "Restricción no activa (recurso sobrante)"

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

    # ── Holguras / Excesos ───────────────────────────────────
    st.write("### Holguras y excesos de las restricciones")
    st.dataframe(
        build_slack_table(result, problem_data),
        use_container_width=True,
    )

    # ── Análisis matricial ───────────────────────────────────
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
    st.dataframe(
        pd.DataFrame([
            {"Restricción": f"R{i + 1}", "Precio sombra": round(v, 4)}
            for i, v in enumerate(data["shadow_prices"])
        ]),
        use_container_width=True,
    )

    # Costos reducidos
    st.write("### Costos reducidos")
    st.dataframe(
        pd.DataFrame([
            {"Variable": data["variable_names"][j], "Costo reducido": round(v, 4)}
            for j, v in enumerate(data["reduced_costs"])
        ]),
        use_container_width=True,
    )

    # Valores de las variables básicas
    st.write("### Valores de las variables básicas")
    st.dataframe(
        pd.DataFrame([
            {
                "Variable básica": data["basic_variables"][i],
                "Valor": round(data["xB"][i], 4),
                "Condición": "Debe permanecer ≥ 0 para mantener la factibilidad",
            }
            for i in range(num_constraints)
        ]),
        use_container_width=True,
    )

    # ── Rangos de cj ────────────────────────────────────────
    st.write("### Rangos de los coeficientes de la función objetivo (cj)")
    st.info(
        "Intervalo en el que puede variar cada coeficiente cj sin que "
        "cambie la base óptima (las variables que forman la solución)."
    )
    st.dataframe(
        pd.DataFrame(data["cj_ranges"]),
        use_container_width=True,
    )

    # ── Rangos de bi ────────────────────────────────────────
    st.write("### Rangos del lado derecho (bi)")
    st.info(
        "Intervalo en el que puede variar cada término independiente bi "
        "sin que cambie la base óptima (aunque sí cambian los valores "
        "de las variables básicas)."
    )
    st.dataframe(
        pd.DataFrame(data["bi_ranges"]),
        use_container_width=True,
    )

    # ── Interpretación económica ─────────────────────────────
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
    st.info(
        "El **rango de cj** muestra entre qué valores puede moverse el "
        "coeficiente de cada variable en Z sin cambiar la solución óptima."
    )
    st.info(
        "El **rango de bi** muestra entre qué valores puede moverse el "
        "lado derecho de cada restricción sin cambiar qué variables "
        "están en la base (aunque el valor de Z sí cambia)."
    )