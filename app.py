
import streamlit as st
import pandas as pd
import plotly.express as px
from influxdb_client import InfluxDBClient

# ==========================================
# CONFIGURACION
# ==========================================

st.set_page_config(
    page_title="Galpón IoT | Monitoreo Avícola",
    page_icon="🐔",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# IDENTIDAD VISUAL
# ==========================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');

.stApp {
    background-color: #F4EBDD;
    color: #533C2D;
    font-family: 'DM Sans', sans-serif;
}

header[data-testid="stHeader"] {
    background-color: #F4EBDD;
}

.block-container {
    max-width: 1250px;
    padding-top: 2.5rem;
    padding-bottom: 3rem;
}

h1, h2, h3, p, label {
    color: #533C2D;
}

.hero {
    background: linear-gradient(115deg, #654631, #98704F);
    padding: 30px;
    border-radius: 20px;
    color: white;
    margin-bottom: 25px;
}

.hero h1 {
    color: #FFF8EE;
    font-size: 36px;
    font-weight: 800;
    margin-bottom: 5px;
}

.hero p {
    color: #F0DCC5;
    font-size: 14px;
    margin-bottom: 0;
}

.section-title {
    font-size: 22px;
    font-weight: 800;
    color: #533C2D;
    margin: 25px 0 15px 0;
}

.metric-card {
    background: #FFFAF2;
    border: 1px solid #E8D9C5;
    border-radius: 17px;
    padding: 23px;
    min-height: 155px;
    box-shadow: 0 3px 12px rgba(83,60,45,0.05);
}

.metric-label {
    color: #94775C;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
}

.metric-value {
    color: #533C2D;
    font-size: 34px;
    font-weight: 800;
    margin-top: 12px;
}

.metric-description {
    color: #A18A72;
    font-size: 12px;
    margin-top: 5px;
}

.panel {
    background: #FFFAF2;
    border: 1px solid #E8D9C5;
    border-radius: 17px;
    padding: 20px;
    margin-bottom: 18px;
}

div.stButton > button {
    background: #A9633D;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 9px 20px;
    font-weight: 700;
}

div.stButton > button:hover {
    background: #895033;
    color: white;
    border: none;
}

div[data-testid="stDataFrame"] {
    border: 1px solid #E8D9C5;
    border-radius: 12px;
}

footer {
    visibility: hidden;
}

</style>
""", unsafe_allow_html=True)

# ==========================================
# ENCABEZADO
# ==========================================

st.markdown("""
<div class="hero">
    <h1>🐔 GALPÓN IoT</h1>
    <p>Sistema inteligente de monitoreo de condiciones ambientales</p>
    <p>TECNOLOGÍA · AUTOMATIZACIÓN · PRODUCCIÓN AVÍCOLA</p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# CONEXION INFLUXDB
# ==========================================

@st.cache_data(ttl=10)
def obtener_datos():

    url = st.secrets["INFLUX_URL"]
    token = st.secrets["INFLUX_TOKEN"]
    org = st.secrets["INFLUX_ORG"]
    bucket = st.secrets["INFLUX_BUCKET"]

    consulta = f'''
    from(bucket: "{bucket}")
      |> range(start: -24h)
      |> filter(fn: (r) => r["_measurement"] == "galpon")
      |> filter(fn: (r) =>
        r["_field"] == "temperatura" or
        r["_field"] == "amoniaco_ppm")
      |> pivot(
        rowKey: ["_time"],
        columnKey: ["_field"],
        valueColumn: "_value"
      )
      |> keep(columns: ["_time", "temperatura", "amoniaco_ppm"])
      |> sort(columns: ["_time"])
    '''

    with InfluxDBClient(
        url=url,
        token=token,
        org=org
    ) as client:

        resultado = client.query_api().query_data_frame(
            consulta,
            org=org
        )

    if isinstance(resultado, list):
        resultado = pd.concat(resultado, ignore_index=True)

    if resultado.empty:
        return resultado

    resultado = resultado.drop(
        columns=["result", "table"],
        errors="ignore"
    )

    resultado["_time"] = pd.to_datetime(
        resultado["_time"], utc=True
    ).dt.tz_convert("America/Bogota")

    return resultado.sort_values("_time")

# ==========================================
# ACTUALIZACION
# ==========================================

col_btn, col_info = st.columns([1, 3])

with col_btn:
    if st.button("↻ Actualizar monitoreo"):
        st.cache_data.clear()
        st.rerun()

with col_info:
    st.caption("Consulta de datos de las últimas 24 horas")

# ==========================================
# LECTURA DE DATOS
# ==========================================

try:

    datos = obtener_datos()

    if datos.empty:

        st.warning(
            "No hay registros disponibles en las últimas 24 horas."
        )

    else:

        ultimo = datos.iloc[-1]

        temperatura = ultimo.get("temperatura")
        amoniaco = ultimo.get("amoniaco_ppm")

        # ==================================
        # INDICADORES
        # ==================================

        st.markdown(
            '<div class="section-title">Indicadores ambientales</div>',
            unsafe_allow_html=True
        )

        c1, c2 = st.columns(2)

        with c1:

            valor_temp = (
                f"{temperatura:.1f} °C"
                if pd.notna(temperatura)
                else "Sin datos"
            )

            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🌡️ TEMPERATURA</div>
                <div class="metric-value">{valor_temp}</div>
                <div class="metric-description">Sensor ambiental DHT22</div>
            </div>
            """, unsafe_allow_html=True)

        with c2:

            valor_gas = (
                f"{amoniaco:.1f} ppm"
                if pd.notna(amoniaco)
                else "Sin datos"
            )

            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">💨 AMONIACO</div>
                <div class="metric-value">{valor_gas}</div>
                <div class="metric-description">Lectura calculada del sensor MQ-2</div>
            </div>
            """, unsafe_allow_html=True)

        fecha = ultimo["_time"].strftime("%d/%m/%Y %H:%M:%S")

        st.markdown(
            f'<p style="color:#94775C;font-size:12px;margin-top:12px;">'
            f'Último registro: {fecha} (hora Colombia)</p>',
            unsafe_allow_html=True
        )

        # ==================================
        # GRAFICAS
        # ==================================

        st.markdown(
            '<div class="section-title">Histórico de variables ambientales</div>',
            unsafe_allow_html=True
        )

        def configurar_grafico(fig, titulo, unidad):

            fig.update_layout(
                title=dict(
                    text=titulo,
                    font=dict(size=17, color="#533C2D")
                ),
                paper_bgcolor="#FFFAF2",
                plot_bgcolor="#FFFAF2",
                font=dict(
                    family="DM Sans",
                    color="#80664F"
                ),
                margin=dict(l=15, r=15, t=55, b=15),
                xaxis=dict(
                    title="Hora",
                    showgrid=False,
                    linecolor="#E8D9C5"
                ),
                yaxis=dict(
                    title=unidad,
                    gridcolor="#EDE3D5",
                    zeroline=False
                ),
                hovermode="x unified"
            )

            return fig

        if "temperatura" in datos.columns:

            temp_datos = datos.dropna(subset=["temperatura"])

            if not temp_datos.empty:

                fig_temp = px.line(
                    temp_datos,
                    x="_time",
                    y="temperatura",
                    markers=True
                )

                fig_temp.update_traces(
                    line=dict(color="#B96E40", width=3),
                    marker=dict(size=6, color="#B96E40")
                )

                fig_temp = configurar_grafico(
                    fig_temp,
                    "Evolución de la temperatura",
                    "Temperatura (°C)"
                )

                st.plotly_chart(
                    fig_temp,
                    use_container_width=True
                )

        if "amoniaco_ppm" in datos.columns:

            gas_datos = datos.dropna(subset=["amoniaco_ppm"])

            if not gas_datos.empty:

                fig_gas = px.line(
                    gas_datos,
                    x="_time",
                    y="amoniaco_ppm",
                    markers=True
                )

                fig_gas.update_traces(
                    line=dict(color="#858653", width=3),
                    marker=dict(size=6, color="#858653")
                )

                fig_gas = configurar_grafico(
                    fig_gas,
                    "Evolución del amoniaco",
                    "Amoniaco (ppm)"
                )

                st.plotly_chart(
                    fig_gas,
                    use_container_width=True
                )

        # ==================================
        # TABLA DE REGISTROS
        # ==================================

        st.markdown(
            '<div class="section-title">Últimos registros del sistema</div>',
            unsafe_allow_html=True
        )

        tabla = datos.sort_values(
            "_time",
            ascending=False
        ).head(20).copy()

        tabla["_time"] = tabla["_time"].dt.strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        tabla = tabla.rename(columns={
            "_time": "Fecha y hora",
            "temperatura": "Temperatura (°C)",
            "amoniaco_ppm": "Amoniaco (ppm)"
        })

        st.dataframe(
            tabla,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            f"Total de registros consultados: {len(datos)}"
        )

except Exception as error:

    st.error("No fue posible consultar InfluxDB.")
    st.caption(str(error))

# ==========================================
# PIE DE PAGINA
# ==========================================

st.markdown("""
<hr style="border-color:#E8D9C5;margin-top:40px;">
<div style="text-align:center;color:#94775C;padding:12px;">
    <b>GALPÓN IoT</b><br>
    Sistema de monitoreo ambiental avícola<br>
    ESP32 · ThingsBoard · InfluxDB · Grafana
</div>
""", unsafe_allow_html=True)

