import pandas as pd
import streamlit as st
import requests
from docx import Document
from io import StringIO

# Función para obtener los datos desde la API
def obtener_datos_api():
    data = {
        'token': '5A253AD70186A4E6CB1C22620A7BF6A5',
        'content': 'report',
        'format': 'csv',
        'report_id': '376',
        'csvDelimiter': ';',
        'rawOrLabel': 'label',
        'rawOrLabelHeaders': 'label',
        'exportCheckboxLabel': 'false',
        'returnFormat': 'json'
    }
    r = requests.post('https://centrodeinvestigacionesclinicas.fvl.org.co/apps/redcap/api/', data=data)
    if r.status_code == 200:
        return r.text
    else:
        st.error(f"Error al obtener los datos: {r.status_code}")
        return None

# Función para cargar y agrupar el archivo CSV
def cargar_datos(csv_data):
    df = pd.read_csv(StringIO(csv_data), sep=';')
    df_grouped = df.groupby('ID').first()
    return df_grouped

# Función para obtener las categorías asociadas a una persona
def obtener_categorias(df_grouped, persona):
    categorias = df_grouped.columns[df_grouped.isin([persona]).any()].tolist()
    return categorias

# Función para calcular la disponibilidad de horas
def calcular_disponibilidad(fase, categoria):
    if categoria == "Investigador Principal":
        if fase == "Administrativo Pre inicio":
            return "30 minutos"
        elif fase == "Reclutamiento":
            return "2 horas"
        elif fase == "Seguimiento":
            return "2 horas"
        elif fase == "Administrativo cierre":
            return "30 minutos"
    elif categoria in [
        "Co-Investigador 1", "Co-Investigador 2", "Co-Investigador 3", "Co-Investigador 4",
        "Co-Investigador 5", "Co-Investigador 6", "Co-Investigador 7"
    ]:
        if fase == "Administrativo Pre inicio":
            return "15 minutos"
        elif fase == "Reclutamiento":
            return "1 hora"
        elif fase == "Seguimiento":
            return "30 minutos"
        elif fase == "Administrativo cierre":
            return "0 minutos"
    elif categoria in [
        "Coordinador Principal", "Coordinador backup principal 1", "Coordinador backup principal 2",
        "Coordinador backup principal 3", "Coordinador backup principal 4", "Coordinador backup principal 5"
    ]:
        if fase == "Administrativo Pre inicio":
            return "1 hora"
        elif fase == "Reclutamiento":
            return "4 horas"
        elif fase == "Seguimiento":
            return "2 horas"
        elif fase == "Administrativo cierre":
            return "1 hora"
    return "N/A"

# Función para filtrar estudios por el coordinador, MD asistencial o investigador
def estudios_por_coordinador(df_grouped, persona, categoria):
    # Filtrar estudios activos
    estudios_filtrados = df_grouped[
        (df_grouped[categoria] == persona) &
        (df_grouped['Estado general del estudio'].str.contains('1. Activo', na=False))
    ]

    # Eliminar números iniciales de la columna "Estado especifico del estudio"
    estudios_filtrados['Estado especifico del estudio'] = estudios_filtrados['Estado especifico del estudio'].str.replace(
        r'^\d+\.\s', '', regex=True)

    # Crear la tabla con los cambios solicitados
    tabla_estudios = pd.DataFrame({
        'Acrónimo': estudios_filtrados['Acrónimo Estudio'],
        'Número del Comité': estudios_filtrados['Número IRB'],
        'Fase del Estudio': estudios_filtrados['Estado especifico del estudio'],
        'Sujetos Tamizados': estudios_filtrados['Total de tamizados'],
        'Sujetos Activos': estudios_filtrados['Total de activos'],
        'Disponibilidad de horas': estudios_filtrados.apply(
            lambda row: calcular_disponibilidad(row['Estado especifico del estudio'], categoria), axis=1)
    }).reset_index(drop=True)

    return tabla_estudios

# Función para generar el documento en Word
def generar_documento(nombre_persona, categoria, tabla_estudios):
    doc = Document()
    doc.add_heading(f"Reporte para {categoria}", 0)
    doc.add_paragraph(f"Nombre: {nombre_persona}")

    if not tabla_estudios.empty:
        doc.add_paragraph("Tabla de estudios asociados:")
        table = doc.add_table(rows=1, cols=len(tabla_estudios.columns))
        hdr_cells = table.rows[0].cells
        for i, col_name in enumerate(tabla_estudios.columns):
            hdr_cells[i].text = col_name

        for index, row in tabla_estudios.iterrows():
            row_cells = table.add_row().cells
            for i, value in enumerate(row):
                row_cells[i].text = str(value)
    else:
        doc.add_paragraph("No hay estudios asociados.")

    filename = f"Reporte_{nombre_persona.replace(' ', '_')}.docx"
    doc.save(filename)
    st.success(f"Documento guardado como {filename}")
    with open(filename, "rb") as file:
        st.download_button(label="Descargar reporte", data=file, file_name=filename)

# Código para ejecutar la lógica en la interfaz Streamlit
st.title("Generador de Informes")
st.header("Centro de Investigaciones Clínicas")
st.subheader("Fundación Valle del Lili")

# Obtener datos desde la API
csv_data = obtener_datos_api()
if csv_data:
    df_grouped = cargar_datos(csv_data)

    personas = df_grouped.stack().dropna().unique()
    seleccion_persona = st.selectbox("Seleccionar Persona", personas)

    if seleccion_persona:
        categorias = obtener_categorias(df_grouped, seleccion_persona)
        seleccion_categoria = st.selectbox("Seleccionar Categoría", categorias)

        if seleccion_categoria:
            if st.button("Generar Informe"):
                tabla_resultante = estudios_por_coordinador(df_grouped, seleccion_persona, seleccion_categoria)
                generar_documento(seleccion_persona, seleccion_categoria, tabla_resultante)

