"""
Dashboard Ligero en Tiempo Real & Simulador LAN - Integrante B
Práctica Calificada: Mini-Azure LUIS & Text Analytics Agroexportación Ica

Tecnología: Streamlit + Requests
Ejecución:
    streamlit run app_dashboard.py
"""

import json
import os
import time
from typing import Dict, Any, Optional
import requests
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="Dashboard Operativo NLP - AgroIca",
    page_icon="🍇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para look profesional tipo Azure Cognitive Services
st.markdown("""
<style>
    .main-title {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #4B5563;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F8FAFC;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-intent {
        background-color: #DBEAFE;
        color: #1E40AF;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        display: inline-block;
    }
    .badge-sentiment-neg {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-sentiment-pos {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-sentiment-neu {
        background-color: #F3F4F6;
        color: #374151;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-action {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-fallback {
        background-color: #FCE7F3;
        color: #9D174D;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# Cargar casos de prueba desde JSON si existe
RUTA_CASOS = os.path.join(os.path.dirname(__file__), "casos_de_prueba.json")
casos_predefinidos = []
if os.path.exists(RUTA_CASOS):
    try:
        with open(RUTA_CASOS, "r", encoding="utf-8") as f:
            data_casos = json.load(f)
            casos_predefinidos = data_casos.get("casos_sustentacion", [])
    except Exception as e:
        st.sidebar.warning(f"No se pudo cargar casos_de_prueba.json: {e}")

# ==========================================
# SIDEBAR: CONFIGURACIÓN DE RED Y CONECTIVIDAD
# ==========================================
st.sidebar.image("https://img.icons8.com/color/96/000000/grapes.png", width=64)
st.sidebar.title("Configuración LAN")
st.sidebar.caption("Rol: Integrante B (Cliente & Dashboard)")

ip_servidor = st.sidebar.text_input(
    "IP Servidor (Integrante A)",
    value="127.0.0.1",
    help="Ingresa la IP privada del servidor en la red local (ej. 192.168.1.15 o 127.0.0.1)"
)
puerto_servidor = st.sidebar.number_input("Puerto API", value=8001, step=1)
timeout_seg = st.sidebar.slider("Timeout HTTP (seg)", min_value=1, max_value=10, value=4)

BASE_URL = f"http://{ip_servidor}:{puerto_servidor}"

# Prueba de conectividad rápida
btn_ping = st.sidebar.button("🔍 Probar Conectividad LAN")
if btn_ping:
    try:
        t0 = time.time()
        resp = requests.get(f"{BASE_URL}/nlp/estadisticas", timeout=timeout_seg)
        latencia = int((time.time() - t0) * 1000)
        if resp.status_code == 200:
            st.sidebar.success(f" Conectado a {BASE_URL} ({latencia} ms)")
        else:
            st.sidebar.warning(f"⚠️ Servidor respondió con código {resp.status_code}")
    except requests.exceptions.ConnectionError:
        st.sidebar.error(f"❌ Error de conexión: No se puede alcanzar {BASE_URL}. Verifica Firewall y puerto 8001.")
    except Exception as ex:
        st.sidebar.error(f"❌ Error: {str(ex)}")

st.sidebar.divider()
st.sidebar.subheader("Acciones de Control")
if st.sidebar.button("🧹 Reiniciar Estadísticas (Demo limpia)", use_container_width=True):
    try:
        resp = requests.post(f"{BASE_URL}/nlp/estadisticas/reiniciar", timeout=timeout_seg)
        if resp.status_code == 200:
            st.sidebar.success(" Estadísticas reiniciadas en el servidor.")
            st.rerun()
        else:
            st.sidebar.error(f"Error al reiniciar: {resp.status_code}")
    except Exception as ex:
        st.sidebar.error(f"Error conectando al servidor: {ex}")

# ==========================================
# HEADER PRINCIPAL
# ==========================================
st.markdown('<div class="main-title">🍇 Mini-Azure LUIS & Text Analytics Agroexportación</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-title">Plataforma de Diagnóstico Operativo y Analítica de Comunicaciones LAN | Servidor Destino: <b>{BASE_URL}</b></div>', unsafe_allow_html=True)

# Tabs principales
tab_simulador, tab_dashboard, tab_documentacion = st.tabs([
    "🚀 Simulador de Mensajes (Individual y Lotes)",
    "📊 Tablero de Analítica en Tiempo Real",
    "📑 Casos de Sustentación & Ficha Técnica"
])

# Funciones de consulta a la API
def consultar_estadisticas() -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(f"{BASE_URL}/nlp/estadisticas", timeout=timeout_seg)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None

def enviar_comando_nlp(texto: str) -> Optional[Dict[str, Any]]:
    payload = {"texto": texto}
    try:
        resp = requests.post(
            f"{BASE_URL}/nlp/entender-comando",
            json=payload,
            timeout=timeout_seg
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"Error {resp.status_code}: {resp.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error(f"No se pudo conectar al servidor en {BASE_URL}. Asegúrate que esté corriendo.")
        return None
    except Exception as ex:
        st.error(f"Excepción en petición: {ex}")
        return None

# ==========================================
# TAB 1: SIMULADOR DE MENSAJES (Fase 3)
# ==========================================
with tab_simulador:
    st.subheader("1. Envío Individual de Mensajes Operativos")
    
    col_sel, col_btn = st.columns([3, 1])
    opciones_casos = ["-- Escribir mensaje personalizado --"] + [f"{c['id']}: {c['tipo']}" for c in casos_predefinidos]
    seleccion_caso = col_sel.selectbox("Cargar caso de prueba de sustentación:", opciones_casos)
    
    mensaje_defecto = ""
    if seleccion_caso != "-- Escribir mensaje personalizado --":
        caso_id = seleccion_caso.split(":")[0].strip()
        caso_obj = next((c for c in casos_predefinidos if c["id"] == caso_id), None)
        if caso_obj:
            mensaje_defecto = caso_obj["mensaje"]
            st.info(f"💡 **Objetivo de la prueba:** {caso_obj['justificacion_demo']} | Intención esperada: `{caso_obj['intencion_esperada']}`")

    texto_input = st.text_area(
        "Mensaje del operador (campo, empaque, logística, frío):",
        value=mensaje_defecto,
        height=90,
        placeholder="Ej: La camara de frio 2 subio a 9 grados con 120 cajas de uva red globe..."
    )

    col_btn_send, col_btn_clear = st.columns([1, 4])
    btn_analizar = col_btn_send.button("📤 Enviar Comando NLP", type="primary", use_container_width=True)

    if btn_analizar:
        if not texto_input.strip():
            st.warning("Por favor ingresa un texto para analizar.")
        else:
            with st.spinner("Procesando con LUIS y Text Analytics local..."):
                t_ini = time.time()
                res = enviar_comando_nlp(texto_input.strip())
                lat_ms = int((time.time() - t_ini) * 1000)

            if res:
                st.success(f" Respuesta procesada con éxito ({lat_ms} ms)")
                
                # Visualización estructurada de la respuesta
                st.markdown("#### Resultado del Análisis Semántico:")
                
                col_res1, col_res2, col_res3, col_res4 = st.columns(4)
                
                # Intención
                intencion_res = res.get("intencion", "DESCONOCIDO")
                conf_int = res.get("confianza_intencion", 0.0)
                
                with col_res1:
                    st.caption("INTENCIÓN PREDICHA")
                    if intencion_res == "INTENCION_NO_CLARA":
                        st.markdown(f'<span class="badge-fallback">⚠️ {intencion_res}</span>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="badge-intent">🏷️ {intencion_res}</span>', unsafe_allow_html=True)
                    st.metric("Confianza", f"{conf_int * 100:.1f}%")
                    if conf_int < 0.65:
                        st.warning("⚠️ Confianza < 65% (Fallback activado)")

                # Sentimiento
                sent_res = res.get("sentimiento", "NEUTRAL")
                with col_res2:
                    st.caption("SENTIMIENTO (POLARIDAD)")
                    if sent_res == "NEGATIVO":
                        st.markdown(f'<span class="badge-sentiment-neg">🔴 NEGATIVO</span>', unsafe_allow_html=True)
                    elif sent_res == "POSITIVO":
                        st.markdown(f'<span class="badge-sentiment-pos">🟢 POSITIVO</span>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="badge-sentiment-neu">⚪ NEUTRAL</span>', unsafe_allow_html=True)

                # Acción sugerida
                accion_res = res.get("accion_sugerida", "NINGUNA")
                with col_res3:
                    st.caption("ACCIÓN SUGERIDA")
                    st.markdown(f'<span class="badge-action">⚙️ {accion_res}</span>', unsafe_allow_html=True)

                # Entidades
                entidades_res = res.get("entidades", {})
                with col_res4:
                    st.caption("ENTIDADES DETECTADAS")
                    if entidades_res:
                        for k, v in entidades_res.items():
                            st.write(f"• **{k}**: `{v}`")
                    else:
                        st.write("*(Ninguna entidad detectada)*")

                with st.expander("Ver JSON Completo de Respuesta (Raw HTTP)"):
                    st.json(res)

    st.divider()
    st.subheader("2. Envío por Lotes (Simulación Masiva de Prueba)")
    st.write("Dispara secuencialmente la batería de casos de prueba con pausas para observar el impacto en tiempo real en las métricas.")

    col_lote1, col_lote2 = st.columns([2, 1])
    pausa_lote = col_lote1.slider("Pausa entre mensajes del lote (segundos):", 0.0, 2.0, 0.5)
    btn_lote = col_lote2.button("⚡ Ejecutar Lote de Sustentación (6 Casos)", type="secondary", use_container_width=True)

    if btn_lote:
        if not casos_predefinidos:
            st.error("No se encontraron casos de sustentación.")
        else:
            progreso_bar = st.progress(0)
            status_text = st.empty()
            resultados_lote = []

            for idx, caso in enumerate(casos_predefinidos):
                status_text.text(f"Enviando ({idx+1}/{len(casos_predefinidos)}): {caso['id']} - {caso['mensaje'][:40]}...")
                res_caso = enviar_comando_nlp(caso["mensaje"])
                if res_caso:
                    resultados_lote.append({
                        "ID": caso["id"],
                        "Tipo": caso["tipo"],
                        "Mensaje": caso["mensaje"],
                        "Intención Esperada": caso["intencion_esperada"],
                        "Intención Obtenida": res_caso.get("intencion"),
                        "Confianza": f"{res_caso.get('confianza_intencion', 0)*100:.1f}%",
                        "Sentimiento": res_caso.get("sentimiento"),
                        "Acción Sugerida": res_caso.get("accion_sugerida"),
                        "Match": "✅" if res_caso.get("intencion") == caso["intencion_esperada"] else "⚠️"
                    })
                progreso_bar.progress((idx + 1) / len(casos_predefinidos))
                if pausa_lote > 0:
                    time.sleep(pausa_lote)

            status_text.success(" ¡Lote de simulación completado exitosamente!")
            st.dataframe(resultados_lote, use_container_width=True)

# ==========================================
# TAB 2: TABLERO DE ANALÍTICA EN TIEMPO REAL
# ==========================================
with tab_dashboard:
    col_dash_title, col_dash_refresh = st.columns([3, 1])
    col_dash_title.subheader("Analítica Operativa de Comunicaciones")
    if col_dash_refresh.button("🔄 Refrescar Métricas"):
        st.rerun()

    stats = consultar_estadisticas()

    if not stats:
        st.warning(f"No se pudieron obtener estadísticas desde `{BASE_URL}/nlp/estadisticas`. Asegúrate de que el servidor esté encendido y el puerto 8001 accesible.")
    else:
        total_msg = stats.get("total_mensajes", 0)
        conf_prom = stats.get("confianza_promedio", 0.0)
        tasa_deriv = stats.get("tasa_derivacion", 0.0)
        alertas_crit = stats.get("alertas_criticas", 0)

        # KPIs Principales
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Mensajes Procesados", total_msg)
        kpi2.metric("Confianza Promedio", f"{conf_prom * 100:.1f}%")
        kpi3.metric("Tasa de Derivación a Supervisor", f"{tasa_deriv * 100:.1f}%")
        kpi4.metric("Alertas Críticas Activas", alertas_crit, delta_color="inverse")

        st.divider()

        # Distribución Visual: Gráficos
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.markdown("##### 📌 Distribución de Mensajes por Intención")
            por_int = stats.get("por_intencion", {})
            if total_msg > 0 and sum(por_int.values()) > 0:
                st.bar_chart(por_int, color="#2563EB")
            else:
                st.info("Sin datos aún para graficar intenciones.")

        with col_g2:
            st.markdown("##### 🎭 Distribución por Sentimiento")
            por_sent = stats.get("por_sentimiento", {})
            if total_msg > 0 and sum(por_sent.values()) > 0:
                st.bar_chart(por_sent, color="#10B981")
            else:
                st.info("Sin datos aún para graficar sentimiento.")

        # Entidades frecuentes
        st.markdown("##### 🏷️ Entidades Más Frecuentes Reportadas")
        entidades_frec = stats.get("entidades_frecuentes", {})
        if entidades_frec:
            st.bar_chart(entidades_frec, horizontal=True, color="#8B5CF6")
        else:
            st.caption("Aún no se han registrado entidades detectadas.")

        st.divider()

        # Bitácora Reciente
        st.markdown("##### 📋 Bitácora Reciente de Mensajes Evaluados")
        ultimos = stats.get("ultimos_mensajes", [])
        if ultimos:
            filas_bitacora = []
            for item in ultimos:
                filas_bitacora.append({
                    "Hora": item.get("timestamp", "-"),
                    "Texto Original": item.get("texto_original", ""),
                    "Intención": item.get("intencion", ""),
                    "Confianza": f"{item.get('confianza_intencion', 0)*100:.1f}%",
                    "Sentimiento": item.get("sentimiento", ""),
                    "Entidades": ", ".join([f"{k}:{v}" for k, v in item.get("entidades", {}).items()]) or "-",
                    "Acción": item.get("accion_sugerida", "")
                })
            st.dataframe(filas_bitacora, use_container_width=True)
        else:
            st.info("No hay mensajes registrados en la bitácora todavía.")

# ==========================================
# TAB 3: DOCUMENTACIÓN Y FICHA TÉCNICA
# ==========================================
with tab_documentacion:
    st.subheader("Ficha Técnica y Matriz de Sustentación (Integrante B)")
    st.markdown("""
    ### Matriz de Casos de Prueba para la Sustentación en Laboratorio:
    """)
    if casos_predefinidos:
        st.table([{
            "ID": c["id"],
            "Tipo": c["tipo"],
            "Mensaje de Prueba": c["mensaje"],
            "Intención Esperada": c["intencion_esperada"],
            "Sentimiento": c["sentimiento_esperado"],
            "Acción Esperada": c["accion_esperada"]
        } for c in casos_predefinidos])

    st.markdown("""
    ---
    ### Procedimiento de Prueba en Red LAN:
    1. **Comprobar IP del Servidor:** En la máquina del Integrante A, ejecutar `ipconfig` (Windows) o `ifconfig` (Linux) y anotar la IPv4 de la red LAN (ej: `192.168.1.15`).
    2. **Validar Conectividad con Ping:**
       ```bash
       ping <IP_DEL_SERVIDOR>
       ```
    3. **Asegurar Regla de Firewall en PC Servidor (Integrante A):**
       El puerto `8001` TCP de entrada debe estar habilitado en Windows Defender Firewall.
    4. **Conectar Dashboard:**
       Ingresar la IP en la barra lateral del Dashboard y presionar `Probar Conectividad LAN`.
    5. **Demostración de los 6 Casos:**
       - Ejecutar el Caso A (Directo con entidades).
       - Ejecutar el Caso B (Errores ortográficos de campo).
       - Ejecutar el Caso C (Ambiguo con <65% de confianza que dispara `INTENCION_NO_CLARA` y `DERIVAR_A_SUPERVISOR`).
       - Ejecutar Casos D, E y F.
       - Observar en tiempo real la actualización de las métricas en la pestaña de analítica.
    """)
