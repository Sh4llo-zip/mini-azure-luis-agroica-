"""
Servidor API REST Cloud - Mini-Azure LUIS v2 (Integrante A)
Microservicio de Procesamiento de Lenguaje Natural con Autenticación RBAC y Analítica Operativa
Empresa Agroexportadora de Ica

Endpoints de Autenticación:
  • POST /auth/login              -> Inicia sesión y emite token Bearer (OPERADOR / SUPERVISOR)
  • GET  /auth/me                 -> Devuelve el perfil y rol del usuario autenticado

Endpoints de NLP (Protegidos):
  • POST /nlp/analizar-texto       -> Permitido para OPERADOR y SUPERVISOR (401 si no hay token)
  • POST /nlp/entender-comando    -> Permitido para OPERADOR y SUPERVISOR (401 si no hay token)
  • GET  /nlp/estadisticas        -> EXCLUSIVO para SUPERVISOR (403 para OPERADOR, 401 sin token)
  • POST /nlp/estadisticas/reiniciar -> EXCLUSIVO para SUPERVISOR (403 para OPERADOR, 401 sin token)

Rutas Públicas:
  • GET  /                        -> Dashboard Web interactivo con Login y RBAC integrado
  • GET  /health                  -> Chequeo de salud del servicio (Cloud Health Check)
"""

import os
import json
import statistics
from datetime import datetime
from typing import Dict, Any, List, Optional
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from extractor_entidades import extraer_entidades
from seguridad_auth import (
    USUARIOS_DB,
    crear_token_acceso,
    obtener_usuario_autenticado,
    requerir_roles
)

# Rutas de artefactos entrenados
DIR_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_MODELO_INT = os.path.join(DIR_ACTUAL, "modelos_entrenados", "modelo_intenciones.joblib")
RUTA_MODELO_SENT = os.path.join(DIR_ACTUAL, "modelos_entrenados", "modelo_sentimientos.joblib")
RUTA_HISTORIAL_JSON = os.path.join(DIR_ACTUAL, "historial_comunicaciones.json")

print("[*] Cargando modelos NLP entrenados desde disco...")
if not os.path.exists(RUTA_MODELO_INT) or not os.path.exists(RUTA_MODELO_SENT):
    raise FileNotFoundError("No se encontraron los modelos entrenados. Ejecute 'python entrenar_modelo.py' primero.")

modelo_intencion = joblib.load(RUTA_MODELO_INT)
modelo_sentimiento = joblib.load(RUTA_MODELO_SENT)
print("[+] Modelos de Intención y Sentimiento cargados en memoria exitosamente.")

app = FastAPI(
    title="Mini-Azure LUIS v2 - AgroIca Cloud API",
    description="Microservicio NLP en la nube con Autenticación RBAC (Operador / Supervisor), Simulación LUIS y Text Analytics.",
    version="2.0.0"
)

# CORS abierto para permitir llamadas remotas desde cualquier origen web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Modelos Pydantic ---
class LoginInput(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str
    nombre_completo: str

class MensajeInput(BaseModel):
    texto: str

class AnalizarTextoResponse(BaseModel):
    texto_original: str
    sentimiento: str
    confianza_sentimiento: float
    terminos_clave: List[str]

class EntenderComandoResponse(BaseModel):
    texto_original: str
    intencion: str
    confianza_intencion: float
    sentimiento: str
    entidades: Dict[str, Any]
    accion_sugerida: str
    usuario_emisor: str

# Almacenamiento en memoria con persistencia en JSON
historial_mensajes: List[Dict[str, Any]] = []

def guardar_historial_disco():
    try:
        with open(RUTA_HISTORIAL_JSON, "w", encoding="utf-8") as f:
            json.dump(historial_mensajes, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Advertencia guardando historial: {e}")

def cargar_historial_disco():
    global historial_mensajes
    if os.path.exists(RUTA_HISTORIAL_JSON):
        try:
            with open(RUTA_HISTORIAL_JSON, "r", encoding="utf-8") as f:
                historial_mensajes = json.load(f)
            print(f"[+] Historial previo restaurado ({len(historial_mensajes)} mensajes).")
        except Exception:
            historial_mensajes = []

cargar_historial_disco()

def normalizar_texto(t: str) -> str:
    t = str(t).lower()
    for orig, dest in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")]:
        t = t.replace(orig, dest)
    return t

def extraer_terminos_clave(texto: str) -> List[str]:
    stop_words = {
        "para", "como", "este", "esta", "estos", "estas", "aqui", "alli", "alla",
        "desde", "hacia", "sobre", "entre", "donde", "cuando", "favor", "queria",
        "avisar", "tengo", "tenemos", "estan", "estoy", "puede", "pueden", "bueno",
        "buenas", "tardes", "dias", "hola", "compa", "amigo", "hermano"
    }
    palabras = [w.strip(",.?!;:()\"'") for w in texto.lower().split() if len(w) > 3]
    filtradas = [w for w in palabras if w not in stop_words]
    unicas = []
    for w in filtradas:
        if w not in unicas:
            unicas.append(w)
    return unicas[:6]

def determinar_accion_sugerida(intencion: str, sentimiento: str, texto: str) -> str:
    texto_l = texto.lower()
    if intencion == "INTENCION_NO_CLARA":
        return "DERIVAR_A_SUPERVISOR"
    elif intencion == "REPORTE_CALIDAD":
        return "ALERTA_CRITICA_CALIDAD" if sentimiento == "NEGATIVO" else "VERIFICAR_LOTE_CALIDAD"
    elif intencion == "FALLA_EQUIPO":
        if any(w in texto_l for w in ["peligro", "fuga", "amoniaco", "humo", "chispas", "evacuacion"]):
            return "EMERGENCIA_PARADA_PLANTA"
        return "NOTIFICAR_MANTENIMIENTO"
    elif intencion == "CONSULTA_INVENTARIO":
        return "CONSULTAR_SISTEMA_WMS"
    elif intencion == "SOLICITUD_DESPACHO":
        return "GENERAR_ORDEN_DESPACHO"
    return "REGISTRAR_REPORTE"

# =============================================================================
# RUTAS PÚBLICAS Y DE SALUD
# =============================================================================

@app.get("/health")
@app.get("/status")
def health_check():
    return {
        "status": "online",
        "servicio": "Mini-Azure LUIS v2 Cloud",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }

# =============================================================================
# ENDPOINTS DE AUTENTICACIÓN (LOGIN & PERFIL)
# =============================================================================

@app.post("/auth/login", response_model=LoginResponse)
def login(credenciales: LoginInput):
    """
    Inicio de sesión por usuario y contraseña.
    Emite un token Bearer firmado con el rol correspondiente.
    """
    user_info = USUARIOS_DB.get(credenciales.username)
    if not user_info or user_info["password"] != credenciales.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas. Verifique usuario y contraseña.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = crear_token_acceso(credenciales.username, user_info["role"])

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        username=credenciales.username,
        role=user_info["role"],
        nombre_completo=user_info["nombre_completo"]
    )

@app.get("/auth/me")
def obtener_perfil_actual(usuario: Dict[str, Any] = Depends(obtener_usuario_autenticado)):
    """Devuelve los datos del usuario actualmente autenticado según su token."""
    info = USUARIOS_DB.get(usuario.get("sub"), {})
    return {
        "username": usuario.get("sub"),
        "role": usuario.get("role"),
        "nombre_completo": info.get("nombre_completo", "Usuario Cloud"),
        "expira_en_segundos": max(0, int(usuario.get("exp", 0) - datetime.now().timestamp()))
    }

# =============================================================================
# ENDPOINTS DE NLP PROTEGIDOS POR ROL
# =============================================================================

@app.post("/nlp/analizar-texto", response_model=AnalizarTextoResponse)
def analizar_texto_endpoint(
    payload: MensajeInput,
    usuario: Dict[str, Any] = Depends(requerir_roles(["OPERADOR", "SUPERVISOR"]))
):
    """
    Simulación Text Analytics:
    Permitido para OPERADOR y SUPERVISOR. (Rechaza con 401 si no hay token).
    """
    texto = payload.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Texto no puede estar vacío.")

    t_proc = normalizar_texto(texto)
    probas_sent = modelo_sentimiento.predict_proba([t_proc])[0]
    idx_sent = int(np.argmax(probas_sent))
    sentimiento = str(modelo_sentimiento.classes_[idx_sent])
    conf_sent = float(round(probas_sent[idx_sent], 2))

    terminos = extraer_terminos_clave(texto)

    return AnalizarTextoResponse(
        texto_original=texto,
        sentimiento=sentimiento,
        confianza_sentimiento=conf_sent,
        terminos_clave=terminos
    )

@app.post("/nlp/entender-comando", response_model=EntenderComandoResponse)
def entender_comando_endpoint(
    payload: MensajeInput,
    usuario: Dict[str, Any] = Depends(requerir_roles(["OPERADOR", "SUPERVISOR"]))
):
    """
    Simulación LUIS:
    Permitido para OPERADOR y SUPERVISOR. (Rechaza con 401 si no hay token).
    Aplica regla de fallback (<0.65 -> INTENCION_NO_CLARA y DERIVAR_A_SUPERVISOR).
    """
    texto = payload.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Texto no puede estar vacío.")

    t_proc = normalizar_texto(texto)

    # 1. Predicción de Intención con Scikit-Learn
    probas_int = modelo_intencion.predict_proba([t_proc])[0]
    idx_int = int(np.argmax(probas_int))
    intencion_predicha = str(modelo_intencion.classes_[idx_int])
    confianza_raw = float(probas_int[idx_int])

    # 2. Predicción de Sentimiento
    probas_sent = modelo_sentimiento.predict_proba([t_proc])[0]
    idx_sent = int(np.argmax(probas_sent))
    sentimiento = str(modelo_sentimiento.classes_[idx_sent])

    # 3. Extracción de Entidades
    entidades = extraer_entidades(texto)

    # 4. Regla de Incertidumbre / Fallback (< 0.65)
    UMBRAL_MINIMO = 0.65
    if confianza_raw < UMBRAL_MINIMO or intencion_predicha == "INTENCION_NO_CLARA":
        intencion_final = "INTENCION_NO_CLARA"
        confianza_final = float(round(confianza_raw, 2))
        accion_sugerida = "DERIVAR_A_SUPERVISOR"
    else:
        intencion_final = intencion_predicha
        confianza_final = float(round(confianza_raw, 2))
        accion_sugerida = determinar_accion_sugerida(intencion_final, sentimiento, texto)

    # 5. Registro para Estadísticas Acumuladas
    registro = {
        "texto_original": texto,
        "intencion": intencion_final,
        "confianza_intencion": confianza_final,
        "sentimiento": sentimiento,
        "entidades": entidades,
        "accion_sugerida": accion_sugerida,
        "usuario_emisor": usuario.get("sub", "desconocido"),
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    historial_mensajes.append(registro)
    guardar_historial_disco()

    return EntenderComandoResponse(
        texto_original=registro["texto_original"],
        intencion=registro["intencion"],
        confianza_intencion=registro["confianza_intencion"],
        sentimiento=registro["sentimiento"],
        entidades=registro["entidades"],
        accion_sugerida=registro["accion_sugerida"],
        usuario_emisor=registro["usuario_emisor"]
    )

@app.get("/nlp/estadisticas")
def obtener_estadisticas_endpoint(
    usuario: Dict[str, Any] = Depends(requerir_roles(["SUPERVISOR"]))
):
    """
    Analítica de Comunicaciones:
    RESTRINGIDO EXCLUSIVAMENTE AL ROL 'SUPERVISOR'.
    Si un 'OPERADOR' intenta acceder, FastAPI responderá con 403 Forbidden.
    Si no hay token, responderá con 401 Unauthorized.
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

    por_int = {
        "REPORTE_CALIDAD": 0,
        "FALLA_EQUIPO": 0,
        "CONSULTA_INVENTARIO": 0,
        "SOLICITUD_DESPACHO": 0,
        "INTENCION_NO_CLARA": 0
    }
    por_sent = {
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
        por_int[it] = por_int.get(it, 0) + 1

        st = item["sentimiento"]
        por_sent[st] = por_sent.get(st, 0) + 1

        confianzas.append(item["confianza_intencion"])

        if item["accion_sugerida"] == "DERIVAR_A_SUPERVISOR":
            derivados += 1

        if any(alert in item["accion_sugerida"] for alert in ["CRITICA", "EMERGENCIA"]):
            alertas_criticas += 1

        for k, v in item.get("entidades", {}).items():
            k_repr = f"{k}: {v}"
            conteo_entidades[k_repr] = conteo_entidades.get(k_repr, 0) + 1

    conf_prom = round(float(statistics.mean(confianzas)), 3) if confianzas else 0.0
    tasa_deriv = round(float(derivados / total), 3)
    entidades_ord = dict(sorted(conteo_entidades.items(), key=lambda x: x[1], reverse=True)[:10])

    return {
        "total_mensajes": total,
        "por_intencion": por_int,
        "por_sentimiento": por_sent,
        "confianza_promedio": conf_prom,
        "tasa_derivacion": tasa_deriv,
        "entidades_frecuentes": entidades_ord,
        "alertas_criticas": alertas_criticas,
        "ultimos_mensajes": historial_mensajes[-20:][::-1]
    }

@app.post("/nlp/estadisticas/reiniciar")
def reiniciar_estadisticas_endpoint(
    usuario: Dict[str, Any] = Depends(requerir_roles(["SUPERVISOR"]))
):
    """
    Control de sesión: Limpia el historial para una nueva demostración limpia.
    RESTRINGIDO EXCLUSIVAMENTE AL ROL 'SUPERVISOR'. (403 para OPERADOR).
    """
    global historial_mensajes
    historial_mensajes = []
    guardar_historial_disco()
    return {"status": "success", "mensaje": "Historial y métricas acumuladas reiniciadas con éxito."}

# =============================================================================
# FRONTEND WEB INCORPORADO (INTERFAZ SPA CON LOGIN Y CONTROL DE ROLES)
# =============================================================================

@app.get("/", response_class=HTMLResponse)
def index_web():
    """Sirve la aplicación web SPA directamente desde la raíz para acceso público en la nube."""
    ruta_html = os.path.join(DIR_ACTUAL, "index.html")
    if os.path.exists(ruta_html):
        with open(ruta_html, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h2>Servicio Mini-Azure LUIS v2 activo en la nube.</h2>")

if __name__ == "__main__":
    puerto = int(os.getenv("PORT", 8001))
    print(f"[*] Iniciando Servidor API REST Cloud en 0.0.0.0:{puerto}...")
    uvicorn.run(app, host="0.0.0.0", port=puerto)
