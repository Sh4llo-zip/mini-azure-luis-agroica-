"""
Extractor de Entidades para el Dominio Agroexportador de Ica
Detecta entidades como PRODUCTO, AREA, CODIGO_LOTE y CANTIDAD mediante
expresiones regulares, diccionarios normalizados y patrones fonéticos/jerga de campo.
"""

import re
from typing import Dict, Any

# Diccionario normalizado de productos agroexportadores y sus variantes de campo
PRODUCTOS_MAPA = {
    "uva red globe": ["uva red globe", "red globe", "uva red glob", "red glob", "uva glob"],
    "uva thompson": ["uva thompson", "thompson", "uva tomson", "uva thompsn", "tompson"],
    "uva crimson": ["uva crimson", "crimson", "uva crimsn", "crimsn"],
    "uva de mesa": ["uva de mesa", "uva fresca", "uva blanca", "uva negra", "uva"],
    "esparrago verde": ["esparrago verde", "esparago verde", "esparago vrd", "esparragos verdes"],
    "esparrago fresco": ["esparrago fresco", "esparrago", "esparago", "esparragos"]
}

# Áreas clave de la planta de empaque, frío y logística
AREAS_MAPA = {
    "camara de frio 1": ["camara de frio 1", "camara 1", "cam 1", "camara uno", "frio 1"],
    "camara de frio 2": ["camara de frio 2", "camara 2", "cam 2", "camara dos", "frio 2"],
    "camara de frio 3": ["camara de frio 3", "camara 3", "cam 3", "camara tres", "frio 3"],
    "camara de frio 4": ["camara de frio 4", "camara 4", "cam 4", "camara cuatro"],
    "packing 1": ["packing 1", "paking 1", "empaque 1", "linea 1"],
    "packing 2": ["packing 2", "paking 2", "empaque 2", "linea 2"],
    "linea de seleccion 3": ["linea de seleccion 3", "seleccion 3", "linea 3"],
    "sala de maquinas": ["sala de maquinas", "sala maquinas", "sala de compresores"],
    "tunel de enfriamiento": ["tunel de enfriamiento", "tunel de frio", "pre-frio", "prefrio"],
    "acopio central": ["acopio central", "patio de acopio", "acopio"],
    "puerto de Pisco": ["puerto de pisco", "puerto pisco", "paracas", "terminal pisco"],
    "puerto del Callao": ["puerto del callao", "puerto callao", "callao", "apm terminals", "dp world"],
    "aeropuerto Jorge Chavez": ["aeropuerto jorge chavez", "aereopuerto jorge chavez", "aeropuerto", "jorge chavez"]
}

def extraer_entidades(texto: str) -> Dict[str, Any]:
    entidades = {}
    texto_norm = texto.lower()

    # 1. Extracción de PRODUCTO
    for prod_normalizado, sinonimos in PRODUCTOS_MAPA.items():
        if any(re.search(r"\b" + re.escape(sin) + r"\b", texto_norm) for sin in sinonimos):
            entidades["PRODUCTO"] = prod_normalizado
            break

    # 2. Extracción de AREA
    for area_normalizada, sinonimos in AREAS_MAPA.items():
        if any(re.search(r"\b" + re.escape(sin) + r"\b", texto_norm) for sin in sinonimos):
            entidades["AREA"] = area_normalizada
            break

    # 3. Extracción de CANTIDAD (ej: 120 cajas, 20 pallets, 500 jabas, 8.2 kilos, 9 grados, 15 por ciento)
    patron_cantidad = re.search(
        r"\b(\d+([.,]\d+)?)\s*(cajas|jabas|javas|pallets|palets|kilos|kg|grados|gds|toneladas|por ciento|%|brix)\b",
        texto_norm
    )
    if patron_cantidad:
        entidades["CANTIDAD"] = patron_cantidad.group(0)

    # 4. Extracción de CODIGO_LOTE o GUÍA (ej: L-502, U-110, E-204, 004-9821, HLXU-402, lote r99)
    patron_lote = re.search(
        r"\b([A-Z]{1,4}-\d{2,5}|\d{3}-\d{4}|lote\s+[A-Za-z0-9\-]+|[A-Z]\d{2,4})\b",
        texto,
        re.IGNORECASE
    )
    if patron_lote:
        entidades["CODIGO_LOTE"] = patron_lote.group(0)

    return entidades

if __name__ == "__main__":
    pruebas = [
        "La camara de frio 2 subio a 9 grados con 120 cajas de uva red globe",
        "urgnt la faja d empaq del paking 1 sta trabada botando javas d esparago vrd",
        "Cuantos pallets listos de esparrago fresco quedan en el lote L-502 de camara 1?",
        "Favor de programar salida de camion con guia de remision 004-9821 para contenedor de uva thompson al puerto de Pisco"
    ]
    for p in pruebas:
        print("Texto:", p)
        print("Entidades:", extraer_entidades(p))
        print("-" * 50)
