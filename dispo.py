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

# Función para obtener la lista de coordinadores, MD asistenciales o investigadores
def obtener_coordinadores(df_grouped, columna):
    coordinadores = df_grouped[columna].dropna().unique()
    return coordinadores

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
def estudios_por_coordinador(df_grouped, coordinador_seleccionado, columna):
    # Filtrar estudios activos
    estudios_filtrados = df_grouped[
        (df_grouped[columna] == coordinador_seleccionado) &
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
            lambda row: calcular_disponibilidad(row['Estado especifico del estudio'], columna), axis=1)
    }).reset_index(drop=True)

    return tabla_estudios

# Función para generar el documento en Word
def generar_documento_acumulado(reporte_acumulado):
    doc = Document()
    doc.add_heading("Reporte Acumulado", 0)

    for reporte in reporte_acumulado:
        nombre_persona = reporte['nombre']
        categoria = reporte['categoria']
        tabla_estudios = reporte['tabla']

        doc.add_heading(f"Reporte para {categoria}", level=1)
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

    filename = "Reporte_Acumulado.docx"
    doc.save(filename)
    return filename

# Código para ejecutar la lógica en la interfaz Streamlit
st.title("Generador de Informes Acumulados")
st.header("Centro de Investigaciones Clínicas")
st.subheader("Fundación Valle del Lili")

# Inicializar el estado del informe acumulado en session_state
if 'reporte_acumulado' not in st.session_state:
    st.session_state.reporte_acumulado = []

# Botón para reiniciar la aplicación
if st.button("Reiniciar Aplicación"):
    st.session_state.reporte_acumulado = []
    st.experimental_rerun()

# Obtener datos desde la API
csv_data = obtener_datos_api()
if csv_data:
    df_grouped = cargar_datos(csv_data)

    categorias = [
        "Seleccionar", "Coordinador Principal", "Coordinador backup principal 1", "Coordinador backup principal 2",
        "Coordinador backup principal 3", "Coordinador backup principal 4", "Coordinador backup principal 5", 
        "MD asistencial 1", "MD asistencial 2", "MD asistencial 3", "MD asistencial 4", "MD asistencial 5", 
        "MD asistencial 6", "MD asistencial 7", "MD asistencial 8", "Investigador Principal", 
        "Co-Investigador 1", "Co-Investigador 2", "Co-Investigador 3", "Co-Investigador 4", "Co-Investigador 5",
        "Co-Investigador 6", "Co-Investigador 7"
    ]

    seleccion_categoria = st.selectbox("Selecciona una categoría", categorias, key="categoria_general")

    if seleccion_categoria != "Seleccionar":
        categoria = seleccion_categoria
        coordinadores = obtener_coordinadores(df_grouped, categoria)

        seleccion_personas = st.multiselect("Seleccionar Personas", coordinadores, key="personas_general")

        if st.button("Agregar a Informe", key="agregar_general"):
            for persona in seleccion_personas:
                tabla_resultante = estudios_por_coordinador(df_grouped, persona, categoria)
                st.session_state.reporte_acumulado.append({
                    'nombre': persona,
                    'categoria': categoria,
                    'tabla': tabla_resultante
                })
            st.success(f"Se han agregado {len(seleccion_personas)} reportes al informe acumulado.")

        if st.session_state.reporte_acumulado and st.button("Generar y Descargar Informe Acumulado", key="descargar_informe"):
            filename = generar_documento_acumulado(st.session_state.reporte_acumulado)
            with open(filename, "rb") as file:
                st.download_button(label="Descargar Informe Acumulado", data=file, file_name=filename)
    else:
        st.warning("Por favor selecciona una categoría.")


