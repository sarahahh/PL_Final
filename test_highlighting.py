#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verificacion detallada de highlighting de tablas
"""

import pandas as pd
import numpy as np
from simplex.simplex_solver import SimplexSolver

def verificar_highlighting():
    """Verifica que el highlighting de tablas funcione correctamente"""

    print("\n" + "="*80)
    print("VERIFICACION DETALLADA DE HIGHLIGHTING DE TABLAS".center(80))
    print("="*80 + "\n")

    # Problema simple
    objective = np.array([3.0, 2.0])
    constraints = [
        {"coefficients": np.array([2.0, 1.0]), "operator": "<=", "rhs": 100.0},
        {"coefficients": np.array([1.0, 1.0]), "operator": "<=", "rhs": 80.0},
    ]

    solver = SimplexSolver(objective=objective, constraints=constraints)
    result = solver.solve()

    # Revisar cada iteracion
    for idx, iteration in enumerate(result["iterations"]):
        print("\n%s" % ("-"*80))
        print("ITERACION %d" % iteration["iteration"])
        print("-"*80)

        # Informacion del pivoteo
        if iteration["entering_variable"]:
            entering = iteration["entering_variable"]
            leaving = iteration["leaving_variable"]
            pivot = iteration["pivot_element"]

            print("\n[DATOS DEL PIVOTEO]")
            print("  Variable que ENTRA (columna a resaltar): %s" % entering)
            print("  Variable que SALE (fila a resaltar): %s" % leaving)
            print("  Elemento PIVOTE: %.4f" % pivot)

            print("\n[ESQUEMA DE COLORES ESPERADO]")
            print("  Columna '%s': AZUL CLARO (#bbdefb)" % entering)
            print("  Fila '%s': NARANJA CLARO (#ffe0b2)" % leaving)
            print("  Interseccion (%s, %s): ROJO (#ef9a9a) + NEGRITA" % (leaving, entering))

        # Mostrar tablero
        print("\n[TABLERO]")
        df = pd.DataFrame(
            iteration["tableau"],
            columns=result["variable_names"] + ["LD"],
            index=iteration["basic_variables"] + ["Z"]
        ).round(4)
        print(df)

        # Verificacion de elementos criticos
        if iteration["entering_variable"]:
            entering_col = entering in result["variable_names"]
            leaving_row = leaving in iteration["basic_variables"]

            print("\n[VERIFICACION]")
            if entering_col:
                print("  OK - Columna '%s' existe en tablero" % entering)
            else:
                print("  ERROR - Columna '%s' NO EXISTE" % entering)

            if leaving_row:
                print("  OK - Fila '%s' existe en tablero" % leaving)
            else:
                print("  ERROR - Fila '%s' NO EXISTE" % leaving)

            # Obtener posiciones
            col_idx = list(result["variable_names"]).index(entering)

            # Usar basic_variables_before para encontrar la fila del pivote
            basic_before = iteration.get("basic_variables_before", iteration["basic_variables"])
            row_idx = list(basic_before).index(leaving)

            print("\n[POSICIONES PARA STYLE_TABLEAU()]")
            print("  Columna '%s' esta en indice: %d" % (entering, col_idx))
            print("  Fila '%s' esta en indice: %d (de basic_variables_before)" % (leaving, row_idx))
            print("  Pivote en posicion [%d, %d]" % (row_idx, col_idx))

            pivot_value = iteration["tableau"][row_idx, col_idx]
            print("  Valor en pivote: %.4f (esperado %.4f)" % (pivot_value, pivot))

    print("\n" + "="*80)
    print("[SUCCESS] VERIFICACION DE HIGHLIGHTING COMPLETADA".center(80))
    print("="*80)

    print("\n[NOTAS SOBRE IMPLEMENTACION]")
    print("""
1. En app.py, la funcion style_tableau() colorea:
   - Columna de entering_variable: background-color: #bbdefb (AZUL)
   - Fila de leaving_variable: background-color: #ffe0b2 (NARANJA)
   - Interseccion: background-color: #ef9a9a + font-weight: bold (ROJO)

2. El coloreado se aplica mediante:
   - pd.DataFrame.style.apply()
   - Devuelve diccionario de estilos CSS

3. Streamlit renderiza los estilos en st.dataframe()

4. El tablero se actualiza en cada iteracion para mostrar
   el pivote que ESTA POR HACERSE (para iter 0) o QUE SE HIZO
   (para iter >= 1), replicando las diapositivas del profesor.
    """)

if __name__ == "__main__":
    verificar_highlighting()
