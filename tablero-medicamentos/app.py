# ============================================================
# TABLERO DE DISPENSACION DE MEDICAMENTOS (EPS 2020 - 2021)
# Materia: Toma de Decisiones Basadas en Datos
# ============================================================


# ------------------------------------------------------------
# 1) IMPORTAR LIBRERIAS
# Las librerias son herramientas que ya existen y que usamos en el programa.
# ------------------------------------------------------------
import os                                         # para buscar el archivo de la base de datos
import sqlite3                                    # para abrir la base de datos
import pandas as pd                               # para guardar el resultado de cada consulta en una tabla
import plotly.express as px                       # para hacer los graficos
from dash import Dash, html, dcc, Input, Output   # para hacer la pagina web del tablero


# ------------------------------------------------------------
# 2) CONECTARSE A LA BASE DE DATOS
# ------------------------------------------------------------
# La base de datos es el archivo medicamentos.db.
# Le decimos a Python que lo busque en la misma carpeta donde esta este archivo app.py.
ruta_base_datos = os.path.join(os.path.dirname(__file__), "medicamentos.db")

# Si el archivo no esta, mostramos un mensaje y cerramos el programa
if not os.path.exists(ruta_base_datos):
    print("ERROR: no encuentro el archivo medicamentos.db")
    print("Debe estar en la misma carpeta que app.py")
    exit()


# Esta funcion hace 3 cosas:
#   1. abre la base de datos
#   2. ejecuta la consulta SQL que le damos
#   3. cierra la base y nos devuelve el resultado como una tabla
# "filtros" son las opciones que el usuario eligio en el tablero.
def consultar(sql, filtros=None):
    conexion = sqlite3.connect(ruta_base_datos)
    tabla = pd.read_sql_query(sql, conexion, params=filtros)
    conexion.close()
    return tabla


# ------------------------------------------------------------
# 3) CONSULTAS SQL
# Aqui estan todas las preguntas que le hacemos a la base de datos.
# Todos los calculos (contar, sumar, promediar, ordenar) los hace SQL.
# La tabla de la base se llama "dispensacion".
# ------------------------------------------------------------

# ---------- 3.1 Opciones de los filtros (puntos 9, 10 y 11) ----------

# Buscamos los grupos farmacologicos que hay en la base, sin repetir (DISTINCT).
# Quitamos los que vienen vacios ('').
sql_opciones_grupo = """
    SELECT DISTINCT grupo_fco_economico AS grupo
    FROM dispensacion
    WHERE grupo_fco_economico <> ''
    ORDER BY grupo_fco_economico
"""
tabla_opciones_grupo = consultar(sql_opciones_grupo)
# La lista del filtro empieza con "Todos" y despues van los grupos
opciones_grupo = ["Todos"] + list(tabla_opciones_grupo["grupo"])

# Lo mismo con las regionales. Quitamos el '0', que significa "no se registro".
sql_opciones_regional = """
    SELECT DISTINCT regional_caf AS regional
    FROM dispensacion
    WHERE regional_caf <> '0'
    ORDER BY regional_caf
"""
tabla_opciones_regional = consultar(sql_opciones_regional)
opciones_regional = ["Todos"] + list(tabla_opciones_regional["regional"])

# Los anios y los meses los escribimos a mano porque son pocos.
# En los meses, a la izquierda va el numero del mes (como aparece en la fecha)
# y a la derecha el nombre que ve el usuario.
opciones_anio = ["Todos", "2020", "2021"]
opciones_mes = {
    "Todos": "Todos",
    "01": "Enero",
    "02": "Febrero",
    "03": "Marzo",
    "04": "Abril",
    "05": "Mayo",
    "06": "Junio",
    "07": "Julio",
    "08": "Agosto",
    "09": "Septiembre",
    "10": "Octubre",
    "11": "Noviembre",
    "12": "Diciembre",
}


# ---------- 3.2 Consultas de los puntos 1 al 8 ----------
# Estas consultas dependen de los filtros. Por eso aqui solo las escribimos,
# y se ejecutan en la parte 6, cada vez que el usuario cambia un filtro.
#
# Todas tienen el mismo WHERE para aplicar los 4 filtros:
#   - :grupo, :anio, :mes y :regional se cambian por lo que eligio el usuario.
#   - Si el usuario deja "Todos", esa condicion siempre se cumple y no filtra nada.
#   - substr(fecha_entrega, 1, 4) saca el anio de la fecha:  '2020-03-15' -> '2020'
#   - substr(fecha_entrega, 6, 2) saca el mes de la fecha:   '2020-03-15' -> '03'
#   - El grupo lo buscamos por el nombre del medicamento (descripcion), porque en 2020
#     la columna del grupo viene vacia. Asi no se pierden los datos de 2020.

# --- PUNTO 1: numero de personas con dispensaciones ---
# Contamos las personas (id) sin repetir, porque una persona aparece en muchas filas.
sql_personas = """
    SELECT COUNT(DISTINCT id) AS total_personas
    FROM dispensacion
    WHERE (:grupo = 'Todos' OR descripcion IN (
              SELECT descripcion FROM dispensacion WHERE grupo_fco_economico = :grupo))
      AND (:anio = 'Todos' OR substr(fecha_entrega, 1, 4) = :anio)
      AND (:mes = 'Todos' OR substr(fecha_entrega, 6, 2) = :mes)
      AND (:regional = 'Todos' OR regional_caf = :regional)
"""

# --- PUNTO 2: numero de formulas distintas ---
# Contamos las formulas sin repetir, porque una formula tiene una fila por cada medicamento.
sql_formulas = """
    SELECT COUNT(DISTINCT formula) AS total_formulas
    FROM dispensacion
    WHERE (:grupo = 'Todos' OR descripcion IN (
              SELECT descripcion FROM dispensacion WHERE grupo_fco_economico = :grupo))
      AND (:anio = 'Todos' OR substr(fecha_entrega, 1, 4) = :anio)
      AND (:mes = 'Todos' OR substr(fecha_entrega, 6, 2) = :mes)
      AND (:regional = 'Todos' OR regional_caf = :regional)
"""

# --- PUNTO 3: costo promedio de una formula ---
# Una formula puede tener varios medicamentos, por eso lo hacemos en 2 pasos:
#   Paso 1 (consulta de adentro): sumamos el costo de cada formula (GROUP BY formula).
#   Paso 2 (consulta de afuera): sacamos el promedio de esas sumas (AVG).
# COALESCE(..., 0) pone un 0 cuando con los filtros elegidos no hay datos.
sql_costo_promedio_formula = """
    SELECT COALESCE(AVG(costo_formula), 0) AS costo_promedio_formula
    FROM (
        SELECT formula, SUM(costo_total) AS costo_formula
        FROM dispensacion
        WHERE (:grupo = 'Todos' OR descripcion IN (
                  SELECT descripcion FROM dispensacion WHERE grupo_fco_economico = :grupo))
          AND (:anio = 'Todos' OR substr(fecha_entrega, 1, 4) = :anio)
          AND (:mes = 'Todos' OR substr(fecha_entrega, 6, 2) = :mes)
          AND (:regional = 'Todos' OR regional_caf = :regional)
        GROUP BY formula
    )
"""

# --- PUNTO 4: dispensacion en el tiempo (por mes) ---
# substr(fecha_entrega, 1, 7) deja el anio y el mes: '2020-03-15' -> '2020-03'.
# Agrupamos por mes para sumar el costo y contar las formulas de cada mes.
sql_por_mes = """
    SELECT
        substr(fecha_entrega, 1, 7) AS mes,
        SUM(costo_total) AS costo_total,
        COUNT(DISTINCT formula) AS numero_formulas
    FROM dispensacion
    WHERE (:grupo = 'Todos' OR descripcion IN (
              SELECT descripcion FROM dispensacion WHERE grupo_fco_economico = :grupo))
      AND (:anio = 'Todos' OR substr(fecha_entrega, 1, 4) = :anio)
      AND (:mes = 'Todos' OR substr(fecha_entrega, 6, 2) = :mes)
      AND (:regional = 'Todos' OR regional_caf = :regional)
    GROUP BY mes
    ORDER BY mes
"""

# --- PUNTO 5: top 10 de medicamentos con mayor costo ---
# Sumamos el costo de cada medicamento, ordenamos de mayor a menor (DESC)
# y dejamos solo los 10 primeros (LIMIT 10).
# Algunos nombres son muy largos, asi que mostramos solo las primeras 60 letras.
sql_top_medicamentos = """
    SELECT
        substr(descripcion, 1, 60) AS medicamento,
        SUM(costo_total) AS costo_total
    FROM dispensacion
    WHERE (:grupo = 'Todos' OR descripcion IN (
              SELECT descripcion FROM dispensacion WHERE grupo_fco_economico = :grupo))
      AND (:anio = 'Todos' OR substr(fecha_entrega, 1, 4) = :anio)
      AND (:mes = 'Todos' OR substr(fecha_entrega, 6, 2) = :mes)
      AND (:regional = 'Todos' OR regional_caf = :regional)
    GROUP BY descripcion
    ORDER BY costo_total DESC
    LIMIT 10
"""

# --- PUNTO 6: costo segun plan de beneficios (PBS / NO PBS) ---
# En la base la columna pbs dice 'SI' o 'NO'.
# Con CASE WHEN lo cambiamos por 'PBS' y 'NO PBS' para que se entienda mejor.
sql_pbs = """
    SELECT
        CASE WHEN pbs = 'SI' THEN 'PBS' ELSE 'NO PBS' END AS plan_beneficios,
        SUM(costo_total) AS costo_total
    FROM dispensacion
    WHERE (:grupo = 'Todos' OR descripcion IN (
              SELECT descripcion FROM dispensacion WHERE grupo_fco_economico = :grupo))
      AND (:anio = 'Todos' OR substr(fecha_entrega, 1, 4) = :anio)
      AND (:mes = 'Todos' OR substr(fecha_entrega, 6, 2) = :mes)
      AND (:regional = 'Todos' OR regional_caf = :regional)
    GROUP BY plan_beneficios
    ORDER BY costo_total DESC
"""

# --- PUNTO 7: costo por municipio ---
# Cuando no se registro el municipio, la base tiene un '0'. Lo mostramos como 'SIN DATO'.
sql_municipios = """
    SELECT
        CASE WHEN municipio_caf = '0' THEN 'SIN DATO' ELSE municipio_caf END AS municipio,
        SUM(costo_total) AS costo_total
    FROM dispensacion
    WHERE (:grupo = 'Todos' OR descripcion IN (
              SELECT descripcion FROM dispensacion WHERE grupo_fco_economico = :grupo))
      AND (:anio = 'Todos' OR substr(fecha_entrega, 1, 4) = :anio)
      AND (:mes = 'Todos' OR substr(fecha_entrega, 6, 2) = :mes)
      AND (:regional = 'Todos' OR regional_caf = :regional)
    GROUP BY municipio
    ORDER BY costo_total DESC
"""

# --- PUNTO 8: costo segun tipo de entrega ---
# Cuando el tipo de entrega viene vacio lo mostramos como 'SIN DATO'.
sql_tipo_entrega = """
    SELECT
        CASE WHEN tipo_entrega = '' THEN 'SIN DATO' ELSE tipo_entrega END AS entrega,
        SUM(costo_total) AS costo_total
    FROM dispensacion
    WHERE (:grupo = 'Todos' OR descripcion IN (
              SELECT descripcion FROM dispensacion WHERE grupo_fco_economico = :grupo))
      AND (:anio = 'Todos' OR substr(fecha_entrega, 1, 4) = :anio)
      AND (:mes = 'Todos' OR substr(fecha_entrega, 6, 2) = :mes)
      AND (:regional = 'Todos' OR regional_caf = :regional)
    GROUP BY entrega
    ORDER BY costo_total DESC
"""


# ---------- 3.3 Consultas del grupo ANTIDIABETICOS ----------
# Esta seccion no usa los filtros: siempre muestra todo el periodo.
# Como en 2020 el grupo viene vacio, buscamos los antidiabeticos por su nombre:
# primero sacamos los nombres de los medicamentos del grupo 'ANTIDIABETICOS'
# y despues buscamos esos nombres en toda la base (2020 y 2021).

# --- a) Su costo ha aumentado? ---
# Consulta de adentro: suma el costo de 2020 y el de 2021 por separado.
#   CASE WHEN mira el anio de cada fila: si es el anio que buscamos suma su costo,
#   y si no, suma 0.
# Consulta de afuera: calcula el porcentaje de cambio entre los dos anios.
sql_antidiabeticos_por_anio = """
    SELECT
        costo_2020,
        costo_2021,
        ROUND((costo_2021 - costo_2020) * 100.0 / costo_2020, 1) AS porcentaje_cambio
    FROM (
        SELECT
            SUM(CASE WHEN substr(fecha_entrega, 1, 4) = '2020' THEN costo_total ELSE 0 END) AS costo_2020,
            SUM(CASE WHEN substr(fecha_entrega, 1, 4) = '2021' THEN costo_total ELSE 0 END) AS costo_2021
        FROM dispensacion
        WHERE descripcion IN (
            SELECT descripcion FROM dispensacion WHERE grupo_fco_economico = 'ANTIDIABETICOS')
    )
"""
tabla_antidiabeticos_por_anio = consultar(sql_antidiabeticos_por_anio)
# El resultado tiene una sola fila (la fila 0)
costo_antidiabeticos_2020 = tabla_antidiabeticos_por_anio["costo_2020"][0]
costo_antidiabeticos_2021 = tabla_antidiabeticos_por_anio["costo_2021"][0]
porcentaje_cambio = tabla_antidiabeticos_por_anio["porcentaje_cambio"][0]

# Costo de cada mes, para ver en un grafico de linea si sube o baja
sql_antidiabeticos_por_mes = """
    SELECT
        substr(fecha_entrega, 1, 7) AS mes,
        SUM(costo_total) AS costo_total
    FROM dispensacion
    WHERE descripcion IN (
        SELECT descripcion FROM dispensacion WHERE grupo_fco_economico = 'ANTIDIABETICOS')
    GROUP BY mes
    ORDER BY mes
"""
tabla_antidiabeticos_por_mes = consultar(sql_antidiabeticos_por_mes)

# --- b) Cual es el medicamento mas costoso del grupo? ---
# Sumamos el costo de cada antidiabetico y los ordenamos de mayor a menor.
# El primero de la lista (fila 0) es el mas costoso.
sql_antidiabeticos_medicamentos = """
    SELECT
        descripcion AS nombre_completo,
        substr(descripcion, 1, 60) AS medicamento,
        SUM(costo_total) AS costo_total
    FROM dispensacion
    WHERE descripcion IN (
        SELECT descripcion FROM dispensacion WHERE grupo_fco_economico = 'ANTIDIABETICOS')
    GROUP BY descripcion
    ORDER BY costo_total DESC
"""
tabla_antidiabeticos_medicamentos = consultar(sql_antidiabeticos_medicamentos)
medicamento_mas_costoso = tabla_antidiabeticos_medicamentos["nombre_completo"][0]
costo_medicamento_mas_costoso = tabla_antidiabeticos_medicamentos["costo_total"][0]

# --- c) Cuanto cuesta una formula promedio del grupo? ---
# Igual que el punto 3: primero sumamos por formula y luego sacamos el promedio,
# pero solo con los antidiabeticos.
sql_antidiabeticos_costo_formula = """
    SELECT AVG(costo_formula) AS costo_promedio_formula
    FROM (
        SELECT formula, SUM(costo_total) AS costo_formula
        FROM dispensacion
        WHERE descripcion IN (
            SELECT descripcion FROM dispensacion WHERE grupo_fco_economico = 'ANTIDIABETICOS')
        GROUP BY formula
    )
"""
tabla_antidiabeticos_costo_formula = consultar(sql_antidiabeticos_costo_formula)
costo_formula_antidiabeticos = tabla_antidiabeticos_costo_formula["costo_promedio_formula"][0]


# ------------------------------------------------------------
# 4) TEXTOS Y GRAFICOS DE LA SECCION DE ANTIDIABETICOS
# (los graficos de los puntos 4 al 8 se hacen en la parte 6,
#  porque cambian cada vez que el usuario mueve un filtro)
# ------------------------------------------------------------

# Ponemos los numeros bonitos para las tarjetas:
#   "{:,.0f}".format(numero)  -> quita los decimales y pone comas en los miles: 86,450
#   .replace(",", ".")         -> cambia las comas por puntos: 86.450
#   "$" +                      -> le pone el signo de pesos adelante: $86.450
texto_costo_2020 = "$" + "{:,.0f}".format(costo_antidiabeticos_2020).replace(",", ".")
texto_costo_2021 = "$" + "{:,.0f}".format(costo_antidiabeticos_2021).replace(",", ".")
texto_costo_mas_costoso = "$" + "{:,.0f}".format(costo_medicamento_mas_costoso).replace(",", ".")
texto_costo_formula_antidiabeticos = "$" + "{:,.0f}".format(costo_formula_antidiabeticos).replace(",", ".")

# El porcentaje lo escribimos con coma decimal: 14.6 -> 14,6 %
texto_porcentaje = str(porcentaje_cambio).replace(".", ",") + " %"

# Si el porcentaje es positivo el costo aumento, si no, disminuyo
if porcentaje_cambio > 0:
    palabra_cambio = "aumentó"
else:
    palabra_cambio = "disminuyó"

# Texto de la conclusion. Unimos varias frases con el signo +
texto_conclusion = (
    "El gasto en antidiabéticos " + palabra_cambio
    + " un " + texto_porcentaje + " entre 2020 y 2021, al pasar de "
    + texto_costo_2020 + " a " + texto_costo_2021 + ". "
    + "Hay que tener en cuenta que en 2021 la base casi no tiene registros después de agosto, "
    + "así que ese valor corresponde a menos meses que 2020. "
    + "El medicamento que más dinero representa en el grupo es " + medicamento_mas_costoso
    + ", con un costo total de " + texto_costo_mas_costoso + ". "
    + "En promedio, una fórmula con antidiabéticos cuesta " + texto_costo_formula_antidiabeticos + "."
)

# Colores de todos los graficos: azul #1f5f8b (y gris #9aa5ad para NO PBS).
# En update_layout le ponemos nombre a los ejes y formato a los numeros:
#   xaxis_type="category"    -> muestra los meses tal cual: 2020-01, 2020-02...
#   yaxis_tickformat=",.0f"  -> muestra el numero completo en el eje, sin abreviar
#   separators=",."          -> usa punto para los miles: 1.000.000

# Grafico de linea: costo de cada mes
grafico_antidiabeticos_por_mes = px.line(
    tabla_antidiabeticos_por_mes,
    x="mes",
    y="costo_total",
    title="Costo mensual de los antidiabéticos",
    markers=True,
    template="plotly_white",
    color_discrete_sequence=["#1f5f8b"],
)
grafico_antidiabeticos_por_mes.update_layout(
    xaxis_title="Mes",
    yaxis_title="Costo total (COP)",
    xaxis_type="category",
    yaxis_tickformat=",.0f",
    separators=",.",
)

# Grafico de barras acostadas: antidiabeticos del mas costoso al menos costoso
grafico_antidiabeticos_medicamentos = px.bar(
    tabla_antidiabeticos_medicamentos,
    x="costo_total",
    y="medicamento",
    orientation="h",
    title="Antidiabéticos ordenados por costo total",
    template="plotly_white",
    color_discrete_sequence=["#1f5f8b"],
    height=800,
)
grafico_antidiabeticos_medicamentos.update_layout(
    xaxis_title="Costo total (COP)",
    yaxis_title="Medicamento",
    xaxis_tickformat=",.0f",
    separators=",.",
)
# Volteamos el eje para que el mas costoso quede arriba
grafico_antidiabeticos_medicamentos.update_yaxes(autorange="reversed")


# ------------------------------------------------------------
# 5) ARMAR LA PAGINA
# html.Div es una caja donde metemos cosas.
# className es el estilo de la caja (esta en assets/estilos.css).
# id es el nombre de un elemento, para poder cambiarlo cuando se usa un filtro.
# ------------------------------------------------------------
app = Dash(__name__)
app.title = "Dispensación de medicamentos"

# Esta linea es necesaria para publicar el tablero en internet (Render)
server = app.server

app.layout = html.Div(className="pagina", children=[

    # Titulo y subtitulo
    html.Div(className="encabezado", children=[
        html.H1("Dispensación de medicamentos"),
        html.P("Datos de la EPS entre 2020 y 2021"),
    ]),

    # Filtros (puntos 9, 10 y 11). dcc.Dropdown es una lista desplegable.
    # value="Todos" es la opcion que aparece elegida al abrir el tablero.
    html.Div(className="fila-filtros", children=[
        html.Div(className="filtro", children=[
            html.Label("Grupo farmacológico"),
            dcc.Dropdown(id="filtro_grupo", options=opciones_grupo, value="Todos", clearable=False),
        ]),
        html.Div(className="filtro", children=[
            html.Label("Año"),
            dcc.Dropdown(id="filtro_anio", options=opciones_anio, value="Todos", clearable=False),
        ]),
        html.Div(className="filtro", children=[
            html.Label("Mes"),
            dcc.Dropdown(id="filtro_mes", options=opciones_mes, value="Todos", clearable=False),
        ]),
        html.Div(className="filtro", children=[
            html.Label("Regional CAF"),
            dcc.Dropdown(id="filtro_regional", options=opciones_regional, value="Todos", clearable=False),
        ]),
    ]),

    # Las 3 tarjetas de los puntos 1, 2 y 3 (el numero lo pone la parte 6)
    html.Div(className="fila-tarjetas", children=[
        html.Div(className="tarjeta", children=[
            html.P("Personas con dispensaciones", className="tarjeta-titulo"),
            html.P(id="tarjeta_personas", className="tarjeta-numero"),
        ]),
        html.Div(className="tarjeta", children=[
            html.P("Fórmulas distintas dispensadas", className="tarjeta-titulo"),
            html.P(id="tarjeta_formulas", className="tarjeta-numero"),
        ]),
        html.Div(className="tarjeta", children=[
            html.P("Costo promedio de una fórmula", className="tarjeta-titulo"),
            html.P(id="tarjeta_costo_promedio", className="tarjeta-numero"),
        ]),
    ]),

    # Graficos de los puntos 4 al 8 (el grafico lo pone la parte 6)
    html.Div(className="recuadro", children=[dcc.Graph(id="grafico_costo_por_mes")]),
    html.Div(className="recuadro", children=[dcc.Graph(id="grafico_formulas_por_mes")]),
    html.P("Nota: diciembre de 2020 y septiembre a noviembre de 2021 tienen muy pocos registros en la base.", className="nota"),
    html.Div(className="recuadro", children=[dcc.Graph(id="grafico_top_medicamentos")]),
    html.Div(className="recuadro", children=[dcc.Graph(id="grafico_pbs")]),
    html.Div(className="recuadro", children=[dcc.Graph(id="grafico_municipios")]),
    html.Div(className="recuadro", children=[dcc.Graph(id="grafico_tipo_entrega")]),

    # Seccion de antidiabeticos
    html.H2("Análisis del grupo ANTIDIABETICOS", className="titulo-seccion"),
    html.P("Esta sección no cambia con los filtros: analiza todo el periodo. Como en 2020 la base no "
           "trae el grupo farmacológico, los antidiabéticos se identificaron por el nombre del medicamento.",
           className="nota"),

    # Tarjetas de la pregunta a) Su costo ha aumentado?
    html.Div(className="fila-tarjetas", children=[
        html.Div(className="tarjeta", children=[
            html.P("Costo total 2020", className="tarjeta-titulo"),
            html.P(texto_costo_2020, className="tarjeta-numero"),
        ]),
        html.Div(className="tarjeta", children=[
            html.P("Costo total 2021", className="tarjeta-titulo"),
            html.P(texto_costo_2021, className="tarjeta-numero"),
        ]),
        html.Div(className="tarjeta", children=[
            html.P("Cambio entre 2020 y 2021", className="tarjeta-titulo"),
            html.P(texto_porcentaje, className="tarjeta-numero"),
        ]),
    ]),

    # Tarjetas de las preguntas b) y c)
    html.Div(className="fila-tarjetas", children=[
        html.Div(className="tarjeta", children=[
            html.P("Medicamento más costoso", className="tarjeta-titulo"),
            html.P(medicamento_mas_costoso, className="tarjeta-numero tarjeta-texto"),
        ]),
        html.Div(className="tarjeta", children=[
            html.P("Costo total del más costoso", className="tarjeta-titulo"),
            html.P(texto_costo_mas_costoso, className="tarjeta-numero"),
        ]),
        html.Div(className="tarjeta", children=[
            html.P("Costo de una fórmula promedio", className="tarjeta-titulo"),
            html.P(texto_costo_formula_antidiabeticos, className="tarjeta-numero"),
        ]),
    ]),

    # Graficos de antidiabeticos
    html.Div(className="recuadro", children=[dcc.Graph(figure=grafico_antidiabeticos_por_mes)]),
    html.Div(className="recuadro", children=[dcc.Graph(figure=grafico_antidiabeticos_medicamentos)]),

    # Conclusion
    html.Div(className="recuadro conclusion", children=[
        html.H3("Conclusión"),
        html.P(texto_conclusion),
    ]),
])


# ------------------------------------------------------------
# 6) HACER FUNCIONAR LOS FILTROS
# @app.callback le dice a Dash dos cosas:
#   - Input:  que este pendiente de los 4 filtros.
#   - Output: que cambie las 3 tarjetas y los 6 graficos.
# Cada vez que el usuario cambia un filtro (y tambien al abrir la pagina),
# Dash ejecuta la funcion actualizar_tablero con lo que el usuario eligio
# y muestra en la pagina lo que la funcion devuelve.
# ------------------------------------------------------------
@app.callback(
    Output("tarjeta_personas", "children"),
    Output("tarjeta_formulas", "children"),
    Output("tarjeta_costo_promedio", "children"),
    Output("grafico_costo_por_mes", "figure"),
    Output("grafico_formulas_por_mes", "figure"),
    Output("grafico_top_medicamentos", "figure"),
    Output("grafico_pbs", "figure"),
    Output("grafico_municipios", "figure"),
    Output("grafico_tipo_entrega", "figure"),
    Input("filtro_grupo", "value"),
    Input("filtro_anio", "value"),
    Input("filtro_mes", "value"),
    Input("filtro_regional", "value"),
)
def actualizar_tablero(grupo, anio, mes, regional):

    # Guardamos lo que eligio el usuario. Estos nombres son los mismos
    # que usamos en las consultas SQL (:grupo, :anio, :mes y :regional).
    filtros = {"grupo": grupo, "anio": anio, "mes": mes, "regional": regional}

    # Hacemos las consultas de los puntos 1 al 8 con los filtros
    tabla_personas = consultar(sql_personas, filtros)
    tabla_formulas = consultar(sql_formulas, filtros)
    tabla_costo_promedio_formula = consultar(sql_costo_promedio_formula, filtros)
    tabla_por_mes = consultar(sql_por_mes, filtros)
    tabla_top_medicamentos = consultar(sql_top_medicamentos, filtros)
    tabla_pbs = consultar(sql_pbs, filtros)
    tabla_municipios = consultar(sql_municipios, filtros)
    tabla_tipo_entrega = consultar(sql_tipo_entrega, filtros)

    # Sacamos el numero de cada tarjeta (esta en la fila 0 de su tabla)
    total_personas = tabla_personas["total_personas"][0]
    total_formulas = tabla_formulas["total_formulas"][0]
    costo_promedio_formula = tabla_costo_promedio_formula["costo_promedio_formula"][0]

    # Ponemos los numeros bonitos (punto en los miles y signo $), igual que en la parte 4
    texto_personas = "{:,.0f}".format(total_personas).replace(",", ".")
    texto_formulas = "{:,.0f}".format(total_formulas).replace(",", ".")
    texto_costo_promedio = "$" + "{:,.0f}".format(costo_promedio_formula).replace(",", ".")

    # PUNTO 4: grafico de linea del costo de cada mes
    grafico_costo_por_mes = px.line(
        tabla_por_mes,
        x="mes",
        y="costo_total",
        title="Costo total de medicamentos por mes",
        markers=True,
        template="plotly_white",
        color_discrete_sequence=["#1f5f8b"],
    )
    grafico_costo_por_mes.update_layout(
        xaxis_title="Mes",
        yaxis_title="Costo total (COP)",
        xaxis_type="category",
        yaxis_tickformat=",.0f",
        separators=",.",
    )

    # PUNTO 4: grafico de linea del numero de formulas de cada mes
    grafico_formulas_por_mes = px.line(
        tabla_por_mes,
        x="mes",
        y="numero_formulas",
        title="Número de fórmulas dispensadas por mes",
        markers=True,
        template="plotly_white",
        color_discrete_sequence=["#1f5f8b"],
    )
    grafico_formulas_por_mes.update_layout(
        xaxis_title="Mes",
        yaxis_title="Número de fórmulas",
        xaxis_type="category",
        separators=",.",
    )

    # PUNTO 5: grafico de barras acostadas con el top 10
    grafico_top_medicamentos = px.bar(
        tabla_top_medicamentos,
        x="costo_total",
        y="medicamento",
        orientation="h",
        title="Top 10 de medicamentos con mayor costo total",
        template="plotly_white",
        color_discrete_sequence=["#1f5f8b"],
        height=500,
    )
    grafico_top_medicamentos.update_layout(
        xaxis_title="Costo total (COP)",
        yaxis_title="Medicamento",
        xaxis_tickformat=",.0f",
        separators=",.",
    )
    # Volteamos el eje para que el mas costoso quede arriba
    grafico_top_medicamentos.update_yaxes(autorange="reversed")

    # PUNTO 6: grafico de barras PBS (azul) y NO PBS (gris)
    grafico_pbs = px.bar(
        tabla_pbs,
        x="plan_beneficios",
        y="costo_total",
        color="plan_beneficios",
        title="Costo de medicamentos según plan de beneficios (PBS / NO PBS)",
        template="plotly_white",
        color_discrete_map={"PBS": "#1f5f8b", "NO PBS": "#9aa5ad"},
    )
    grafico_pbs.update_layout(
        xaxis_title="Plan de beneficios",
        yaxis_title="Costo total (COP)",
        yaxis_tickformat=",.0f",
        separators=",.",
        showlegend=False,
    )

    # PUNTO 7: grafico de barras por municipio
    grafico_municipios = px.bar(
        tabla_municipios,
        x="municipio",
        y="costo_total",
        title="Costo de medicamentos por municipio de dispensación",
        template="plotly_white",
        color_discrete_sequence=["#1f5f8b"],
        height=550,
    )
    grafico_municipios.update_layout(
        xaxis_title="Municipio",
        yaxis_title="Costo total (COP)",
        yaxis_tickformat=",.0f",
        separators=",.",
        xaxis_tickangle=-45,
    )

    # PUNTO 8: grafico de barras por tipo de entrega
    grafico_tipo_entrega = px.bar(
        tabla_tipo_entrega,
        x="entrega",
        y="costo_total",
        title="Costo de medicamentos según tipo de entrega",
        template="plotly_white",
        color_discrete_sequence=["#1f5f8b"],
    )
    grafico_tipo_entrega.update_layout(
        xaxis_title="Tipo de entrega",
        yaxis_title="Costo total (COP)",
        yaxis_tickformat=",.0f",
        separators=",.",
    )

    # Devolvemos todo en el mismo orden de los Output de arriba
    return (
        texto_personas,
        texto_formulas,
        texto_costo_promedio,
        grafico_costo_por_mes,
        grafico_formulas_por_mes,
        grafico_top_medicamentos,
        grafico_pbs,
        grafico_municipios,
        grafico_tipo_entrega,
    )


# ------------------------------------------------------------
# 7) EJECUTAR LA APP
# Esto solo corre cuando escribimos "python app.py" en nuestro PC.
# En Render la app la ejecuta gunicorn usando la variable server.
# ------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
