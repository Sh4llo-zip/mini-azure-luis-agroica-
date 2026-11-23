"""
Servidor Mock de Prueba Local - Fase 2 (Simulación Mini-Azure LUIS + Text Analytics)
Permite al Integrante B probar y calibrar el Cliente LAN y Dashboard sin depender
del servidor del Integrante A.

Uso:
    python mock_servidor_nlp.py
    (Escuchará en 0.0.0.0:8001)
"""

import re
import statistics
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(
    title="Mini-Azure LUIS Agroexportación Ica (Mock Servidor NLP)",
    description="Microservicio de simulación local de Text Analytics, LUIS y Métricas Operativas",
    version="1.0.0"
)

# Habilitar CORS para permitir peticiones desde dashboards web o clientes LAN
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Modelos de Entrada / Salida ---
class MensajeInput(BaseModel):
    texto: str

class AnalisisTextoOutput(BaseModel):
    texto_original: str
    sentimiento: str
    confianza_sentimiento: float
    terminos_clave: List[str]

class EntenderComandoOutput(BaseModel):
    texto_original: str
    intencion: str
    confianza_intencion: float
    sentimiento: str
    entidades: Dict[str, Any]
    accion_sugerida: str

# --- Almacenamiento en memoria de estadísticas y bitácora ---
historial_mensajes: List[Dict[str, Any]] = []

def extraer_entidades_heuristica(texto: str) -> Dict[str, Any]:
    entidades = {}
    t_lower = texto.lower()

    # Productos
    for prod in ["uva red globe", "uva thompson", "uva crimson", "esparrago verde", "esparragos", "esparrago", "uva"]:
        if prod in t_lower:
            entidades["PRODUCTO"] = prod
            break

    # Áreas
    areas = [
        "camara de frio 2", "camara de frio 1", "camara 1", "camara 2", "camara 3",
        "paking 1", "packing 1", "packing 2", "sala de maquinas", "tunel de enfriamiento",
        "puerto de pisco", "aeropuerto jorge chavez", "acopio central", "linea de seleccion 3"
    ]
    for area in areas:
        if area in t_lower:
            entidades["AREA"] = area
            break

    # Cantidades (ej: 120 cajas, 500 jabas, 10 pallets)
    match_cant = re.search(r"\b(\d+)\s*(cajas|jabas|pallets|kg|kilos|toneladas|grados)\b", t_lower)
    if match_cant:
        entidades["CANTIDAD"] = match_cant.group(0)

    # Códigos de Lote (ej: L-502, U-110, 004-9821)
    match_lote = re.search(r"\b([A-Z]-\d+|\d{3}-\d{4}|lote\s+[A-Za-z0-9\-]+)\b", texto, re.IGNORECASE)
    if match_lote:
        entidades["CODIGO_LOTE"] = match_lote.group(0)

    return entidades

def clasificar_sentimiento_heuristica(texto: str) -> tuple[str, float]:
    t_lower = texto.lower()
    palabras_negativas = ["peligro", "fuga", "urgnt", "urgente", "trabada", "subio", "pudricion", "paro", "detenida", "insoportable", "deshidratacion", "falla", "danada", "dano", "alerta"]
    palabras_positivas = ["excelente", "conforme", "correcto", "listo", "completado", "exito", "buen", "optimo", "ok"]

    count_neg = sum(1 for p in palabras_negativas if p in t_lower)
    count_pos = sum(1 for p in palabras_positivas if p in t_lower)

    if count_neg > 0:
        conf = min(0.95, 0.75 + (0.1 * count_neg))
        return "NEGATIVO", round(conf, 2)
    elif count_pos > 0:
        conf = min(0.95, 0.70 + (0.1 * count_pos))
        return "POSITIVO", round(conf, 2)
    else:
        return "NEUTRAL", 0.85

def clasificar_intencion_heuristica(texto: str) -> tuple[str, float]:
    t_lower = texto.lower()

    # Patrones de ambigüedad extrema o mensajes sin contexto operativo
    if any(frase in t_lower for frase in ["raro x aca", "no se que decir", "cualquier cosa me avisan", "como quedamos ayer", "paso una cosa muy rara"]):
        return "INTENCION_NO_CLARA", 0.48

    puntuaciones = {
        "REPORTE_CALIDAD": 0,
        "FALLA_EQUIPO": 0,
        "CONSULTA_INVENTARIO": 0,
        "SOLICITUD_DESPACHO": 0
    }

    # Palabras clave por intención
    kw_calidad = ["temperatura", "humedad", "grados", "pudricion", "calibre", "condicion", "empaque", "bayas", "deshidratacion", "calidad", "cajas de uva"]
    kw_falla = ["camara de frio", "faja", "transportadora", "impresora", "sensor", "compresor", "fuga", "amoniaco", "trabada", "detenida", "maquinas", "tunel"]
    kw_inventario = ["cuantos", "stock", "disponible", "pallets listos", "jabas", "insumos", "saldo", "quedan", "cosecheras"]
    kw_despacho = ["programar", "salida", "camion", "guia de remision", "embarque", "contenedor", "flete", "cisterna", "despacho", "chofer", "puerto"]

    for kw in kw_calidad:
        if kw in t_lower:
            puntuaciones["REPORTE_CALIDAD"] += 1
    for kw in kw_falla:
        if kw in t_lower:
            puntuaciones["FALLA_EQUIPO"] += 1
    for kw in kw_inventario:
        if kw in t_lower:
            puntuaciones["CONSULTA_INVENTARIO"] += 1
    for kw in kw_despacho:
        if kw in t_lower:
            puntuaciones["SOLICITUD_DESPACHO"] += 1

    mejor_intencion = max(puntuaciones, key=puntuaciones.get)
    max_pts = puntuaciones[mejor_intencion]

    if max_pts == 0:
        return "INTENCION_NO_CLARA", 0.42
    elif max_pts == 1:
        # Si tiene sólo 1 coincidencia débil
        return mejor_intencion, 0.72
    else:
        conf = min(0.97, 0.78 + (0.07 * max_pts))
        return mejor_intencion, round(conf, 2)


# --- Endpoints Fase 2 ---

@app.post("/nlp/analizar-texto", response_model=AnalisisTextoOutput)
def analizar_texto(input_data: MensajeInput):
    """
    Simulación Text Analytics:
    Devuelve sentimiento, confianza y términos/frases clave.
    """
    sentimiento, conf_sent = clasificar_sentimiento_heuristica(input_data.texto)
    palabras = [w.strip(",.?!;:()\"'") for w in input_data.texto.split() if len(w) > 4]
    terminos_clave = list(set([p for p in palabras if p.lower() not in ["desde", "hacia", "sobre", "entre", "donde", "cuando", "favor"]]))[:6]

    return AnalisisTextoOutput(
        texto_original=input_data.texto,
        sentimiento=sentimiento,
        confianza_sentimiento=conf_sent,
        terminos_clave=terminos_clave
    )

@app.post("/nlp/entender-comando", response_model=EntenderComandoOutput)
def entender_comando(input_data: MensajeInput):
    """
    Simulación LUIS + Text Analytics:
    Predice intención, confianza, sentimiento, entidades y acción sugerida.
    Aplica regla de fallback (<0.65 -> INTENCION_NO_CLARA y DERIVAR_A_SUPERVISOR).
    Registra evento para estadísticas.
    """
    texto = input_data.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="El campo texto no puede estar vacío.")

    intencion_raw, confianza = clasificar_intencion_heuristica(texto)
    sentimiento, conf_sent = clasificar_sentimiento_heuristica(texto)
    entidades = extraer_entidades_heuristica(texto)

    # Regla de incertidumbre (< 0.65)
    if confianza < 0.65 or intencion_raw == "INTENCION_NO_CLARA":
        intencion = "INTENCION_NO_CLARA"
        accion_sugerida = "DERIVAR_A_SUPERVISOR"
    else:
        intencion = intencion_raw
        if intencion == "REPORTE_CALIDAD":
            accion_sugerida = "ALERTA_CRITICA_CALIDAD" if sentimiento == "NEGATIVO" else "VERIFICAR_LOTE_CALIDAD"
        elif intencion == "FALLA_EQUIPO":
            accion_sugerida = "EMERGENCIA_PARADA_PLANTA" if "peligro" in texto.lower() or "amoniaco" in texto.lower() else "NOTIFICAR_MANTENIMIENTO"
        elif intencion == "CONSULTA_INVENTARIO":
            accion_sugerida = "CONSULTAR_SISTEMA_WMS"
        elif intencion == "SOLICITUD_DESPACHO":
            accion_sugerida = "GENERAR_ORDEN_DESPACHO"
        else:
            accion_sugerida = "REGISTRAR_REPORTE"

    resultado = {
        "texto_original": texto,
        "intencion": intencion,
        "confianza_intencion": confianza,
        "sentimiento": sentimiento,
        "entidades": entidades,
        "accion_sugerida": accion_sugerida,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }

    historial_mensajes.append(resultado)

    return EntenderComandoOutput(
        texto_original=resultado["texto_original"],
        intencion=resultado["intencion"],
        confianza_intencion=resultado["confianza_intencion"],
        sentimiento=resultado["sentimiento"],
        entidades=resultado["entidades"],
        accion_sugerida=resultado["accion_sugerida"]
    )

@app.get("/nlp/estadisticas")
def obtener_estadisticas():
    """
    Devuelve analítica acumulada de comunicaciones.
    """
    total = len(historial_mensajes)
    if total == 0:
        return {
            "total_mensajes": 0,
            "por_intencion": {
                "REPORTE_CALIDAD": 0,
                "FALLA_EQUIPO": 0,
                "CONSULTA_INVENTARIO": 0,
                "SOLICITUD_DESPACHO": 0,
                "INTENCION_NO_CLARA": 0
            },
            "por_sentimiento": {
                "POSITIVO": 0,
                "NEUTRAL": 0,
                "NEGATIVO": 0
            },
            "confianza_promedio": 0.0,
            "tasa_derivacion": 0.0,
            "entidades_frecuentes": {},
            "alertas_criticas": 0,
            "ultimos_mensajes": []
        }

    por_intencion = {
        "REPORTE_CALIDAD": 0,
        "FALLA_EQUIPO": 0,
        "CONSULTA_INVENTARIO": 0,
        "SOLICITUD_DESPACHO": 0,
        "INTENCION_NO_CLARA": 0
    }
    por_sentimiento = {
        "POSITIVO": 0,
        "NEUTRAL": 0,
        "NEGATIVO": 0
    }
    conteo_entidades: Dict[str, int] = {}
    alertas_criticas = 0

    confianzas = []
    derivados = 0

    for item in historial_mensajes:
        it = item["intencion"]
        por_intencion[it] = por_intencion.get(it, 0) + 1

        st = item["sentimiento"]
        por_sentimiento[st] = por_sentimiento.get(st, 0) + 1

        confianzas.append(item["confianza_intencion"])

        if item["accion_sugerida"] == "DERIVAR_A_SUPERVISOR":
            derivados += 1
        if "CRITICA" in item["accion_sugerida"] or "EMERGENCIA" in item["accion_sugerida"]:
            alertas_criticas += 1

        for k, v in item.get("entidades", {}).items():
            key_repr = f"{k}: {v}"
            conteo_entidades[key_repr] = conteo_entidades.get(key_repr, 0) + 1

    conf_prom = round(statistics.mean(confianzas), 3) if confianzas else 0.0
    tasa_deriv = round(derivados / total, 3)

    # Entidades ordenadas
    entidades_ord = dict(sorted(conteo_entidades.items(), key=lambda x: x[1], reverse=True)[:10])

    return {
        "total_mensajes": total,
        "por_intencion": por_intencion,
        "por_sentimiento": por_sentimiento,
        "confianza_promedio": conf_prom,
        "tasa_derivacion": tasa_deriv,
        "entidades_frecuentes": entidades_ord,
        "alertas_criticas": alertas_criticas,
        "ultimos_mensajes": historial_mensajes[-15:][::-1] # más recientes primero
    }

@app.post("/nlp/estadisticas/reiniciar")
def reiniciar_estadisticas():
    """
    Control de sesión: Reinicia historial para demostración limpia.
    """
    historial_mensajes.clear()
    return {"status": "success", "mensaje": "Historial de estadísticas reiniciado correctamente."}

if __name__ == "__main__":
    print("Iniciando Mock Servidor NLP en 0.0.0.0:8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
