import pandas as pd
import streamlit as st
import requests
from docx import Document
from io import StringIO, BytesIO

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

# Función para calcular la disponibilidad
def calcular_disponibilidad(fase, categoria):
    disponibilidad = { 
        "Investigador Principal": {
            "Administrativo Pre inicio": "30 minutos",
            "Reclutamiento": "2 horas",
            "Reclutamiento on Hold": "1 hora",
            "Seguimiento": "2 horas",
            "Administrativo cierre": "30 minutos",
        },
        **{f"Co-Investigador {i}": {
            "Administrativo Pre inicio": "15 minutos",
            "Reclutamiento": "1 hora",
            "Reclutamiento on Hold": "30 minutos",
            "Seguimiento": "1 hora",
            "Administrativo cierre": "0 minutos",
        } for i in range(1, 8)},
        "Coordinador Principal": {
            "Administrativo Pre inicio": "1 hora",
            "Reclutamiento": "4 horas",
            "Reclutamiento on Hold": "2 horas",
            "Seguimiento": "2 horas",
            "Administrativo cierre": "1 hora",
        },
        **{f"Coordinador backup principal {i}": {
            "Administrativo Pre inicio": "0 minutos",
            "Reclutamiento": "0 minutos",
            "Reclutamiento on Hold": "0 minutos",
            "Seguimiento": "0 minutos",
            "Administrativo cierre": "0 minutos",
        } for i in range(1, 6)},
        "MD asistencial 1": {
            "Administrativo Pre inicio": "15 minutos",
            "Reclutamiento": "1 hora",
            "Reclutamiento on Hold": "30 minutos",
            "Seguimiento": "1 hora",
            "Administrativo cierre": "0 minutos",
        },
        **{f"MD asistencial {i}": {
            "Administrativo Pre inicio": "0 minutos",
            "Reclutamiento": "0 minutos",
            "Reclutamiento on Hold": "0 minutos",
            "Seguimiento": "0 minutos",
            "Administrativo cierre": "0 minutos",
        } for i in range(2, 9)},
        "Coordinador Supernumerario": {
            "Administrativo Pre inicio": "0 minutos",
            "Reclutamiento": "0 minutos",
            "Reclutamiento on Hold": "0 minutos",
            "Seguimiento": "0 minutos",
            "Administrativo cierre": "0 minutos",
        },
    }
    return disponibilidad.get(categoria, {}).get(fase, "N/A")

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

            for _, row in tabla_estudios.iterrows():
                row_cells = table.add_row().cells
                for i, value in enumerate(row):
                    row_cells[i].text = str(value)
        else:
            doc.add_paragraph("No hay estudios asociados.")

    filename = "Reporte_Acumulado.docx"
    doc.save(filename)
    return filename

# Botón para descargar la base de datos en formato XLSX
if csv_data:
    df = pd.read_csv(StringIO(csv_data), sep=';')
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Datos')
    output.seek(0)
    
    st.download_button(
        label="Descargar Base de Datos en XLSX",
        data=output,
        file_name="Base_de_Datos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
