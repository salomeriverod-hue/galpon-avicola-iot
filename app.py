
import streamlit as st
import pandas as pd
import plotly.express as px
from influxdb_client import InfluxDBClient

st.set_page_config(
    page_title="Galpón Avícola IoT",
    page_icon="🐔",
    layout="wide"
)

st.title("🐔 Sistema IoT para Galpón Avícola")
st.caption("Monitoreo de condiciones ambientales en tiempo real")

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

    with InfluxDBClient(url=url, token=token, org=org) as client:
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

    resultado["_time"] = pd.to_datetime(resultado["_time"])

    return resultado

if st.button("🔄 Actualizar datos"):
    st.cache_data.clear()

try:
    datos = obtener_datos()

    if datos.empty:
        st.warning("Todavía no hay registros disponibles en InfluxDB.")
    else:
        ultimo = datos.iloc[-1]

        temperatura = ultimo.get("temperatura")
        amoniaco = ultimo.get("amoniaco_ppm")

        st.subheader("Indicadores actuales")

        col1, col2 = st.columns(2)

        with col1:
            if pd.notna(temperatura):
                st.metric(
                    "🌡️ Temperatura",
                    f"{temperatura:.1f} °C"
                )
            else:
                st.metric("🌡️ Temperatura", "Sin datos")

        with col2:
            if pd.notna(amoniaco):
                st.metric(
                    "💨 Amoniaco",
                    f"{amoniaco:.1f} ppm"
                )
            else:
                st.metric("💨 Amoniaco", "Sin datos")

        st.caption(
            "Último registro: "
            + ultimo["_time"].strftime("%d/%m/%Y %H:%M:%S UTC")
        )

        st.divider()
        st.subheader("Histórico de variables ambientales")

        if "temperatura" in datos.columns:
            grafico_temp = px.line(
                datos,
                x="_time",
                y="temperatura",
                title="Evolución de la temperatura",
                labels={
                    "_time": "Hora",
                    "temperatura": "Temperatura (°C)"
                },
                markers=True
            )
            st.plotly_chart(grafico_temp, use_container_width=True)

        if "amoniaco_ppm" in datos.columns:
            grafico_gas = px.line(
                datos,
                x="_time",
                y="amoniaco_ppm",
                title="Evolución del amoniaco",
                labels={
                    "_time": "Hora",
                    "amoniaco_ppm": "Amoniaco (ppm)"
                },
                markers=True
            )
            st.plotly_chart(grafico_gas, use_container_width=True)

        st.divider()
        st.subheader("Registros del sistema")

        st.dataframe(
            datos.sort_values("_time", ascending=False),
            use_container_width=True,
            hide_index=True
        )

except Exception as error:
    st.error("No fue posible consultar InfluxDB.")
    st.caption(str(error))
