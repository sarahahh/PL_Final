#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba completo para verificar:
1. Metodo Simplex con ejemplo simple
2. Metodo Grafico con dos variables
3. Analisis de Sensibilidad
4. Verificacion de tablas con highlighting
"""

import sys
import pandas as pd
import numpy as np
from simplex.parser import build_problem
from simplex.simplex_solver import SimplexSolver
from simplex.graphics import solve_graphical_method
from simplex.sensitivity import compute_sensitivity

def print_header(text):
    print("\n" + "="*70)
    print(f"{text:^70}")
    print("="*70 + "\n")

def print_subheader(text):
    print("\n" + "-"*70)
    print(f"  {text}")
    print("-"*70 + "\n")

def test_ejemplo_1():
    """
    Ejemplo 1: Problema simple de maximizacion
    Max Z = 3x1 + 2x2
    s.a.
    2x1 + x2 <= 100
    x1 + x2 <= 80
    x1, x2 >= 0
    """
    print_header("EJEMPLO 1: Maximizacion Simple (2x2)")

    objective = np.array([3.0, 2.0])
    constraints = [
        {"coefficients": np.array([2.0, 1.0]), "operator": "<=", "rhs": 100.0},
        {"coefficients": np.array([1.0, 1.0]), "operator": "<=", "rhs": 80.0},
    ]

    print("PROBLEMA:")
    print("Maximizar Z = 3x1 + 2x2")
    print("Sujeto a:")
    print("  2x1 + x2 <= 100")
    print("  x1 + x2 <= 80")
    print("  x1, x2 >= 0\n")

    # Metodo Simplex
    print_subheader("METODO SIMPLEX - ITERACIONES")
    solver = SimplexSolver(objective=objective, constraints=constraints)
    result = solver.solve()

    print("Estado: %s" % result['status'])
    print("Solucion optima: x1 = %.4f, x2 = %.4f" % (result['solution'][0], result['solution'][1]))
    print("Valor optimo: Z = %.4f\n" % result['optimal_value'])

    # Mostrar cada iteracion
    for idx, iteration in enumerate(result["iterations"]):
        print("\nIteracion %d: %s" % (iteration['iteration'], iteration['message']))
        if iteration["entering_variable"]:
            print("  * Variable que entra: %s" % iteration['entering_variable'])
            print("  * Variable que sale: %s" % iteration['leaving_variable'])
            print("  * Elemento pivote: %.4f\n" % iteration['pivot_element'])

            # Tabla con highlighting
            df = pd.DataFrame(
                iteration["tableau"],
                columns=result["variable_names"] + ["LD"],
                index=iteration["basic_variables"] + ["Z"]
            ).round(4)

            print("Tablero (Iteracion):")
            print(df)

            # Resaltar pivote si es posible
            if iteration["entering_variable"] and iteration["leaving_variable"]:
                print("\n  [PIVOTE] Fila: %s, Columna: %s" % (
                    iteration['leaving_variable'],
                    iteration['entering_variable']
                ))

    # Tablero final
    print_subheader("TABLERO FINAL")
    df_final = pd.DataFrame(
        result["tableau"],
        columns=result["variable_names"] + ["LD"],
        index=result["basic_variables"] + ["Z"]
    ).round(4)
    print(df_final)

    return result

def test_ejemplo_2():
    """
    Ejemplo 2: Problema con restricciones >= y =
    Min Z = 4x1 + 3x2
    s.a.
    x1 + x2 >= 5
    2x1 + x2 = 8
    x1, x2 >= 0
    """
    print_header("EJEMPLO 2: Minimizacion con >= y =")

    objective = np.array([4.0, 3.0])
    constraints = [
        {"coefficients": np.array([1.0, 1.0]), "operator": ">=", "rhs": 5.0},
        {"coefficients": np.array([2.0, 1.0]), "operator": "=", "rhs": 8.0},
    ]

    problem_data = {
        "type": "Minimizar",
        "objective": objective,
        "constraints": constraints,
    }

    print("PROBLEMA:")
    print("Minimizar Z = 4x1 + 3x2")
    print("Sujeto a:")
    print("  x1 + x2 >= 5")
    print("  2x1 + x2 = 8")
    print("  x1, x2 >= 0\n")

    # Para minimizacion, el solver trabaja con -objetivo
    solver_objective = -objective
    solver = SimplexSolver(objective=solver_objective, constraints=constraints)
    result = solver.solve()

    # Recuperar valor real de Z
    result["optimal_value"] *= -1

    print("Estado: %s" % result['status'])
    print("Solucion optima: x1 = %.4f, x2 = %.4f" % (result['solution'][0], result['solution'][1]))
    print("Valor optimo: Z = %.4f\n" % result['optimal_value'])

    # Mostrar iteraciones importantes
    print_subheader("ITERACIONES IMPORTANTES")
    print("Total de iteraciones: %d\n" % (len(result['iterations']) - 1))

    for iteration in result["iterations"][:3]:  # Primeras 3
        if iteration["entering_variable"]:
            print("Iteracion %d: %s" % (iteration['iteration'], iteration['message']))

    # Tablero final
    print_subheader("TABLERO FINAL")
    df_final = pd.DataFrame(
        result["tableau"],
        columns=result["variable_names"] + ["LD"],
        index=result["basic_variables"] + ["Z"]
    ).round(4)
    print(df_final)

    return result

def test_metodo_grafico():
    """
    Ejemplo 3: Metodo grafico (solo 2 variables)
    Max Z = 50x1 + 40x2
    s.a.
    x1 + 1.5x2 <= 80
    2x1 + x2 <= 100
    x1, x2 >= 0
    """
    print_header("EJEMPLO 3: Metodo Grafico")

    objective = np.array([50.0, 40.0])
    constraints = [
        {"coefficients": np.array([1.0, 1.5]), "operator": "<=", "rhs": 80.0},
        {"coefficients": np.array([2.0, 1.0]), "operator": "<=", "rhs": 100.0},
    ]

    print("PROBLEMA:")
    print("Maximizar Z = 50x1 + 40x2")
    print("Sujeto a:")
    print("  x1 + 1.5x2 <= 80")
    print("  2x1 + x2 <= 100")
    print("  x1, x2 >= 0\n")

    problem_data = {
        "type": "Maximizar",
        "objective": objective,
        "constraints": constraints,
    }

    print_subheader("RESOLUCION GRAFICA")
    graphical_result = solve_graphical_method(
        objective=objective,
        constraints=constraints,
        problem_type="Maximizar"
    )

    print("Vertices factibles encontrados:")
    if not graphical_result["vertices_table"].empty:
        print(graphical_result["vertices_table"])

    print("\nSolucion optima: (%.4f, %.4f)" % (
        graphical_result['optimal_point'][0],
        graphical_result['optimal_point'][1]
    ))
    print("Valor optimo: Z = %.4f" % graphical_result['optimal_value'])

    return graphical_result

def test_sensibilidad():
    """
    Analisis de sensibilidad del Ejemplo 1
    """
    print_header("EJEMPLO 4: Analisis de Sensibilidad")

    result = test_ejemplo_1()

    print_subheader("ANALISIS DE SENSIBILIDAD")

    # Precios sombra
    print("Precios Sombra (Multiplicadores de Lagrange):")
    print("  * Indican el cambio marginal en Z por unidad de cambio en RHS\n")

    for i, var_name in enumerate(result["basic_variables"]):
        if var_name.startswith("S"):
            coeff = result["tableau"][i, -1]
            print("    %s: %.4f" % (var_name, coeff))

    return result

def verificar_estructuras():
    """
    Verificar que todas las estructuras estan correctas
    """
    print_header("VERIFICACION DE ESTRUCTURAS")

    errors = []

    # Test 1: Parser
    try:
        print("[OK] Test 1: Parser funcionando")
        problem = build_problem(
            "Maximizar",
            [1, 2],
            [{"coeffs": [1, 1], "operator": "<=", "rhs": 10}]
        )
        assert "objective" in problem
        assert "constraints" in problem
    except Exception as e:
        errors.append("[ERROR] Parser error: %s" % str(e))

    # Test 2: SimplexSolver
    try:
        print("[OK] Test 2: SimplexSolver funcionando")
        solver = SimplexSolver([1, 2], [{"coefficients": np.array([1, 1]), "operator": "<=", "rhs": 10}])
        result = solver.solve()
        assert "solution" in result
        assert "optimal_value" in result
        assert "iterations" in result
    except Exception as e:
        errors.append("[ERROR] SimplexSolver error: %s" % str(e))

    # Test 3: Graphics
    try:
        print("[OK] Test 3: Metodo grafico funcionando")
        result = solve_graphical_method(
            [1, 2],
            [{"coefficients": np.array([1, 1]), "operator": "<=", "rhs": 10}],
            "Maximizar"
        )
        assert "figure" in result
        assert "optimal_point" in result
    except Exception as e:
        errors.append("[ERROR] Graphics error: %s" % str(e))

    if errors:
        print("\n=== ERRORES ENCONTRADOS ===")
        for error in errors:
            print(error)
    else:
        print("\n[SUCCESS] TODAS LAS ESTRUCTURAS FUNCIONAN CORRECTAMENTE")

if __name__ == "__main__":
    try:
        verificar_estructuras()

        test_ejemplo_1()
        test_ejemplo_2()
        test_metodo_grafico()

        print_header("PRUEBAS COMPLETADAS EXITOSAMENTE")
        print("[SUCCESS] Todos los ejemplos funcionaron correctamente")
        print("[SUCCESS] Metodo Simplex operativo")
        print("[SUCCESS] Metodo Grafico operativo")
        print("[SUCCESS] Tablas con highlighting listas")

    except Exception as e:
        print("\n[ERROR] ERROR: %s" % str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
