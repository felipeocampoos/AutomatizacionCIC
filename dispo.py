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

    # Crear la tabla con los cambios solicitados
    tabla_estudios = pd.DataFrame({
        'Acrónimo': estudios_filtrados['Acrónimo Estudio'],
        'Número del Comité': estudios_filtrados['Número IRB'],
        'Fase del Estudio': estudios_filtrados['Estado especifico del estudio'],
        'Sujetos Tamizados': estudios_filtrados['Total de tamizados'],
        'Sujetos Activos': estudios_filtrados['Total de activos'],
        'Disponibilidad de horas': estudios_filtrados.apply(
            lambda row: calcular_disponibilidad(row['Estado especifico del estudio'], coordinador_seleccionado), axis=1)
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
st.write(
    """
    <style>
    .fixed-text {
        position: fixed;
        left: 10px;
        bottom: 10px;
        font-size: 12px;
    }
    </style>
    <div class="fixed-text">
        Desarrollado por: Unidad de Inteligencia Artificial
    </div>
    """,
    unsafe_allow_html=True
)

st.title("Generador de Informes")
st.header("Centro de Investigaciones Clínicas")
st.subheader("Fundación Valle del Lili")

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

    seleccion_categoria = st.selectbox("Selecciona una categoría", categorias)

    if seleccion_categoria != "Seleccionar":
        categoria = seleccion_categoria
        coordinadores = obtener_coordinadores(df_grouped, categoria)

        if len(coordinadores) > 0:
            seleccion_persona = st.selectbox("Seleccionar Persona", coordinadores)
            
            if st.button("Generar Informe"):
                tabla_resultante = estudios_por_coordinador(df_grouped, seleccion_persona, categoria)
                generar_documento(seleccion_persona, categoria, tabla_resultante)
        else:
            st.error(f"No hay personal registrado en la categoría {seleccion_categoria}.")
    else:
        st.warning("Por favor selecciona una categoría.")


