# inspeccionar.py
# Este programa revisa la base de datos medicamentos.db para saber
# que tablas y columnas tiene, antes de construir el tablero.

import sqlite3
import os

# Revisamos que el archivo exista (si no existe, sqlite crearia uno vacio)
if not os.path.exists("medicamentos.db"):
    print("ERROR: no encuentro medicamentos.db en esta carpeta.")
    print("Carpeta actual:", os.getcwd())
    exit()

# Nos conectamos a la base de datos
conexion = sqlite3.connect("medicamentos.db")
cursor = conexion.cursor()

# Buscamos el nombre de todas las tablas
cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
tablas = cursor.fetchall()

print("TABLAS ENCONTRADAS:")
for tabla in tablas:
    print("  -", tabla[0])

# Revisamos cada tabla una por una
for tabla in tablas:
    nombre_tabla = tabla[0]
    print()
    print("=" * 60)
    print("TABLA:", nombre_tabla)
    print("=" * 60)

    # Numero de filas de la tabla
    cursor.execute('SELECT COUNT(*) FROM "' + nombre_tabla + '"')
    total_filas = cursor.fetchone()[0]
    print("Número de filas:", total_filas)

    # Columnas y su tipo
    cursor.execute('PRAGMA table_info("' + nombre_tabla + '")')
    columnas = cursor.fetchall()
    print()
    print("COLUMNAS (nombre - tipo):")
    for columna in columnas:
        print("  -", columna[1], "-", columna[2])

    # 5 filas de ejemplo
    print()
    print("5 FILAS DE EJEMPLO:")
    cursor.execute('SELECT * FROM "' + nombre_tabla + '" LIMIT 5')
    filas = cursor.fetchall()
    for fila in filas:
        print("  ", fila)

    # Revisamos cada columna para encontrar PBS, grupo, fecha
    # y cualquier columna con pocos valores distintos (categorias)
    for columna in columnas:
        nombre_columna = columna[1]
        nombre_minuscula = nombre_columna.lower()

        # Cuantos valores distintos tiene la columna
        cursor.execute('SELECT COUNT(DISTINCT "' + nombre_columna + '") FROM "' + nombre_tabla + '"')
        cantidad_distintos = cursor.fetchone()[0]

        # Si parece una columna de fecha, mostramos el minimo y el maximo
        if "fecha" in nombre_minuscula or "date" in nombre_minuscula or "periodo" in nombre_minuscula:
            cursor.execute('SELECT MIN("' + nombre_columna + '"), MAX("' + nombre_columna + '"), typeof("' + nombre_columna + '") FROM "' + nombre_tabla + '"')
            resultado = cursor.fetchone()
            print()
            print("FECHA -> columna:", nombre_columna)
            print("  Mínimo:", resultado[0])
            print("  Máximo:", resultado[1])
            print("  Tipo guardado en SQLite:", resultado[2])

        # Si es PBS, grupo, o tiene pocos valores distintos, mostramos sus valores
        es_pbs_o_grupo = "pbs" in nombre_minuscula or "grupo" in nombre_minuscula
        if es_pbs_o_grupo or cantidad_distintos <= 40:
            print()
            print("VALORES DISTINTOS -> columna:", nombre_columna, "(" + str(cantidad_distintos) + " valores)")
            cursor.execute('SELECT "' + nombre_columna + '", COUNT(*) FROM "' + nombre_tabla + '" GROUP BY "' + nombre_columna + '" ORDER BY COUNT(*) DESC LIMIT 60')
            valores = cursor.fetchall()
            for valor in valores:
                print("  ", valor[0], "->", valor[1], "filas")
        else:
            print()
            print("Columna", nombre_columna, "tiene", cantidad_distintos, "valores distintos (no se listan)")

# Cerramos la conexion
conexion.close()
