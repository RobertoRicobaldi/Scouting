# Página de Scouting, Filtros y Comparativa integradas
import os
import sqlite3
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from fpdf import FPDF
from PIL import Image

# Inicializar la base de datos
@st.cache_data
def init_db():
    conn = sqlite3.connect("jugadoras.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS valoraciones (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT,
                        posicion TEXT,
                        club TEXT,
                        valoracion INTEGER,
                        comentario TEXT,
                        captador TEXT
                    )''')
    conn.commit()
    conn.close()

init_db()

# Cargar datos directamente desde el archivo principal
EXCEL_PATH = r"C:\\Users\\rricobaldi\\Desktop\\Atlético de Madrid\\Atlético de Madrid\\Departamento Captación\\Seguimiento Jugadoras\\Seguimiento Jugadoras TOTALES Temporada 2023-2024.xlsx"
FOTOS_PATH = r"C:\\Users\\rricobaldi\\Desktop\\Atlético de Madrid\\Atlético de Madrid\\Departamento Captación\\Seguimiento Jugadoras\\Fotos Jugadoras Temporada 2023-2024.xlsx"

@st.cache_data
def load_data(ruta):
    try:
        if not os.path.exists(ruta):
            st.error(f"No se encontró el archivo en la ruta especificada: {ruta}")
            return pd.DataFrame()
        return pd.read_excel(ruta, engine='openpyxl')
    except Exception as e:
        st.error(f"Error al cargar el archivo Excel: {e}")
        return pd.DataFrame()

df = load_data(EXCEL_PATH)
df_fotos = load_data(FOTOS_PATH)

# Unir datos con las fotos
if "NOMBRE COMPLETO / APODO" in df.columns and "NOMBRE COMPLETO / APODO" in df_fotos.columns:
    df = df.merge(df_fotos[["NOMBRE COMPLETO / APODO", "FOTO"]], on="NOMBRE COMPLETO / APODO", how="left")

def obtener_valoraciones():
    conn = sqlite3.connect("jugadoras.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM valoraciones")
    datos = cursor.fetchall()
    conn.close()
    return datos

def agregar_valoracion(captador, nombre, posicion, club, valoracion, comentario):
    conn = sqlite3.connect("jugadoras.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO valoraciones (captador, nombre, posicion, club, valoracion, comentario) VALUES (?, ?, ?, ?, ?, ?)",
                   (captador, nombre, posicion, club, valoracion, comentario))
    conn.commit()
    conn.close()

def mostrar_tabla_con_fotos(df):
    df = df.copy()
    if "FOTO" in df.columns:
        df["FOTO"] = df["FOTO"].apply(lambda url: f'<img src="{url}" width="60">' if pd.notna(url) else "")
        columnas = ["FOTO"] + [col for col in df.columns if col != "FOTO"]
        df = df[columnas]
        st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.dataframe(df)

pagina = st.sidebar.radio("Selecciona una página", ["Scouting", "Búsqueda de Jugadoras", "Filtros y Datos", "Comparativa de Jugadoras"], key="pagina_principal")

# -------------------- SCOUTING --------------------
if pagina == "Scouting":
    st.header("Scouting de Jugadoras")
    jugadoras = df["NOMBRE COMPLETO / APODO"].dropna().unique()
    seleccionada = st.selectbox("Selecciona una jugadora", ["Selecciona una jugadora"] + list(jugadoras), key="scouting_jugadora")

    if seleccionada and seleccionada != "Selecciona una jugadora":
        datos_jugadora = df[df["NOMBRE COMPLETO / APODO"] == seleccionada]
        st.write(f"### Datos de {seleccionada}")
        columnas_mostrar = ["FECHA PARTIDO", "TEMPORADA", "NOMBRE COMPLETO / APODO", "NACIONALIDAD", "POSICIÓN", "EDAD", "EQUIPO 24-25", "FOTO"]
        mostrar_tabla_con_fotos(datos_jugadora[columnas_mostrar])

        st.write("### Agregar valoración")
        captador = st.text_input("Nombre del captador")
        valoracion = st.selectbox("Valoración", [3, 5, 7, 9], key="valoracion")
        comentario = st.text_area("Comentario")

        if st.button("Guardar valoración"):
            if captador and comentario:
                if not datos_jugadora.empty:
                    posicion = datos_jugadora.iloc[0]["POSICIÓN"] if "POSICIÓN" in datos_jugadora.columns else "Sin posición"
                    club = datos_jugadora.iloc[0]["EQUIPO 24-25"] if "EQUIPO 24-25" in datos_jugadora.columns else "Sin club"
                    agregar_valoracion(captador, seleccionada, posicion, club, valoracion, comentario)
                    st.success("Valoración guardada correctamente.")
                else:
                    st.error("No se encontraron datos de la jugadora seleccionada.")
            else:
                st.error("Por favor, completa todos los campos.")

    st.subheader("Ranking de Jugadoras Mejor Valoradas")
    valoraciones = pd.DataFrame(obtener_valoraciones(), columns=["ID", "Nombre", "Posición", "Club", "Valoración", "Comentario", "Captador"])
    if not valoraciones.empty:
        top_valoradas = valoraciones.groupby("Nombre").agg(Media=("Valoración", "mean"), Cuenta=("Valoración", "count")).sort_values(by="Media", ascending=False).head(10).reset_index()
        df_fotos = df[["NOMBRE COMPLETO / APODO", "FOTO"]].drop_duplicates().rename(columns={"NOMBRE COMPLETO / APODO": "Nombre"})
        top_valoradas = pd.merge(top_valoradas, df_fotos, on="Nombre", how="left")
        mostrar_tabla_con_fotos(top_valoradas)

# -------------------- BÚSQUEDA DE JUGADORAS --------------------
elif pagina == "Búsqueda de Jugadoras":
    st.header("Búsqueda de Jugadoras")
    jugadoras = df["NOMBRE COMPLETO / APODO"].dropna().unique()
    seleccionada = st.selectbox("Buscar jugadora por nombre", ["Selecciona una jugadora"] + list(jugadoras), key="busqueda_jugadora")

    if seleccionada != "Selecciona una jugadora":
        resultado = df[df["NOMBRE COMPLETO / APODO"] == seleccionada]
        mostrar_tabla_con_fotos(resultado)

# -------------------- FILTROS Y DATOS --------------------
elif pagina == "Filtros y Datos":
    st.header("Filtros y Datos Generales")
    equipos = df["EQUIPO 24-25"].dropna().unique() if "EQUIPO 24-25" in df.columns else []
    posiciones = df["POSICIÓN"].dropna().unique() if "POSICIÓN" in df.columns else []
    edades = df["EDAD"].dropna() if "EDAD" in df.columns else pd.Series(dtype='int')
    calificaciones = df["CALIFICACIÓN"].dropna() if "CALIFICACIÓN" in df.columns else pd.Series(dtype='float')

    equipo_sel = st.selectbox("Selecciona un equipo", ["Todos"] + list(equipos))
    pos_sel = st.selectbox("Selecciona una posición", ["Todas"] + list(posiciones))

    edad_min = int(edades.min()) if not edades.empty else 10
    edad_max = int(edades.max()) if not edades.empty else 40
    edad_range = st.slider("Rango de edad", edad_min, edad_max, (edad_min, edad_max))

    cal_min = float(calificaciones.min()) if not calificaciones.empty else 0.0
    cal_max = float(calificaciones.max()) if not calificaciones.empty else 10.0
    cal_range = st.slider("Rango de calificación", cal_min, cal_max, (cal_min, cal_max))

    df_filtrado = df.copy()
    if equipo_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["EQUIPO 24-25"] == equipo_sel]
    if pos_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado["POSICIÓN"] == pos_sel]
    if "EDAD" in df_filtrado.columns:
        df_filtrado = df_filtrado[(df_filtrado["EDAD"] >= edad_range[0]) & (df_filtrado["EDAD"] <= edad_range[1])]
    if "CALIFICACIÓN" in df_filtrado.columns:
        df_filtrado = df_filtrado[(df_filtrado["CALIFICACIÓN"] >= cal_range[0]) & (df_filtrado["CALIFICACIÓN"] <= cal_range[1])]

    mostrar_tabla_con_fotos(df_filtrado)

    if st.button("Exportar a PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        for index, row in df_filtrado.iterrows():
            nombre = row.get("NOMBRE COMPLETO / APODO", "")
            pos = row.get("POSICIÓN", "")
            equipo = row.get("EQUIPO 24-25", "")
            linea = f"{nombre} - {pos} en {equipo}"
            pdf.cell(200, 10, txt=linea, ln=True)
        pdf.output("informe_jugadoras.pdf")
        st.success("Informe exportado como 'informe_jugadoras.pdf'")

# -------------------- COMPARATIVA DE JUGADORAS --------------------
elif pagina == "Comparativa de Jugadoras":
    st.header("Comparativa de Jugadoras")
    jugadoras = df["NOMBRE COMPLETO / APODO"].dropna().unique()

    jugadora_1 = st.selectbox("Selecciona la primera jugadora", ["Selecciona una jugadora"] + list(jugadoras), key="jugadora_1")
    jugadora_2 = st.selectbox("Selecciona la segunda jugadora", ["Selecciona una jugadora"] + list(jugadoras), key="jugadora_2")

    if jugadora_1 != "Selecciona una jugadora" and jugadora_2 != "Selecciona una jugadora":
        datos_1 = df[df["NOMBRE COMPLETO / APODO"] == jugadora_1]
        datos_2 = df[df["NOMBRE COMPLETO / APODO"] == jugadora_2]

        st.write("#### Estadísticas de Jugadoras")
        mostrar_tabla_con_fotos(datos_1)
        mostrar_tabla_con_fotos(datos_2)

        st.write("#### Radar Chart Comparativo")
        metricas = ["EDAD", "CALIFICACIÓN", "NÚMERO DE VECES DESTACADA"]

        valores_1 = [datos_1[met].mean() if met in datos_1.columns else 0 for met in metricas]
        valores_2 = [datos_2[met].mean() if met in datos_2.columns else 0 for met in metricas]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=valores_1, theta=metricas, fill='toself', name=jugadora_1))
        fig.add_trace(go.Scatterpolar(r=valores_2, theta=metricas, fill='toself', name=jugadora_2))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True)
        st.plotly_chart(fig)

        st.write("#### Valoraciones")
        valoraciones_df = pd.DataFrame(obtener_valoraciones(), columns=["ID", "Nombre", "Posición", "Club", "Valoración", "Comentario", "Captador"])

        for jugadora in [jugadora_1, jugadora_2]:
            valoraciones_jugadora = valoraciones_df[valoraciones_df["Nombre"] == jugadora]
            st.subheader(f"Valoraciones de {jugadora}")
            if not valoraciones_jugadora.empty:
                for _, fila in valoraciones_jugadora.iterrows():
                    st.write(f"📋 **Captador:** {fila['Captador']}")
                    st.write(f"⭐ Valoración: {'⭐' * int(fila['Valoración'])} ({fila['Valoración']})")
                    st.write(f"📜 Comentario: {fila['Comentario']}")
                    st.write("---")
            else:
                st.write("Sin valoraciones registradas para esta jugadora.")
