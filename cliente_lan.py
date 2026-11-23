"""
Cliente LAN de Consola y Simulador de Pruebas - Integrante B
Práctica Calificada: Mini-Azure LUIS & Text Analytics Agroexportación Ica

Permite enviar mensajes individuales, ejecutar lotes de simulación y consultar estadísticas
directamente desde la terminal hacia la IP del servidor.

Uso:
    python cliente_lan.py --ip 192.168.1.15 --puerto 8001
    (O modo interactivo por defecto: python cliente_lan.py)
"""

import argparse
import json
import os
import sys
import time
import requests

DEFAULT_SERVER_IP = "127.0.0.1"
DEFAULT_PORT = 8001

COLOR_CYAN = "\033[96m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_MAGENTA = "\033[95m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"

RUTA_CASOS = os.path.join(os.path.dirname(__file__), "casos_de_prueba.json")

def banner():
    print(f"{COLOR_CYAN}{COLOR_BOLD}")
    print("=" * 70)
    print("   CLIENTE LAN & SIMULADOR DE PRUEBAS - AGROEXPORTACIÓN ICA (NLP)")
    print("        Microservicio Mini-Azure LUIS & Text Analytics")
    print("=" * 70)
    print(f"{COLOR_RESET}")

def test_conectividad(base_url: str) -> bool:
    print(f"[*] Comprobando conectividad HTTP con {base_url}...")
    try:
        t0 = time.time()
        resp = requests.get(f"{base_url}/nlp/estadisticas", timeout=3)
        ms = int((time.time() - t0) * 1000)
        if resp.status_code == 200:
            print(f"{COLOR_GREEN}[+] Conectividad exitosa con el Servidor ({ms} ms). Status 200 OK.{COLOR_RESET}\n")
            return True
        else:
            print(f"{COLOR_YELLOW}[!] Servidor respondió con código inesperado: {resp.status_code}{COLOR_RESET}\n")
            return False
    except requests.exceptions.ConnectionError:
        print(f"{COLOR_RED}[-] ERROR DE CONEXIÓN: No se pudo conectar a {base_url}.")
        print("    Verifique que:")
        print("    1. La IP del servidor sea correcta.")
        print("    2. El servidor esté corriendo escuchando en 0.0.0.0:8001.")
        print(f"    3. El Firewall en la PC Servidor permita conexiones TCP en el puerto 8001.{COLOR_RESET}\n")
        return False
    except Exception as ex:
        print(f"{COLOR_RED}[-] Error inesperado: {ex}{COLOR_RESET}\n")
        return False

def enviar_comando_individual(base_url: str, texto: str):
    print(f"\n{COLOR_CYAN}--> Enviando mensaje al servidor:{COLOR_RESET} \"{texto}\"")
    try:
        t0 = time.time()
        resp = requests.post(f"{base_url}/nlp/entender-comando", json={"texto": texto}, timeout=5)
        lat = int((time.time() - t0) * 1000)
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"{COLOR_GREEN}<-- Respuesta recibida ({lat} ms):{COLOR_RESET}")
            print("-" * 65)
            
            intencion = data.get("intencion", "DESCONOCIDO")
            conf = data.get("confianza_intencion", 0.0)
            sentimiento = data.get("sentimiento", "NEUTRAL")
            accion = data.get("accion_sugerida", "NINGUNA")
            entidades = data.get("entidades", {})
            
            # Formato de colores
            color_conf = COLOR_GREEN if conf >= 0.65 else COLOR_RED
            color_sent = COLOR_RED if sentimiento == "NEGATIVO" else (COLOR_GREEN if sentimiento == "POSITIVO" else COLOR_YELLOW)
            
            print(f"  • {COLOR_BOLD}Texto Evaluado:{COLOR_RESET}     {data.get('texto_original')}")
            print(f"  • {COLOR_BOLD}Intención:{COLOR_RESET}          {COLOR_CYAN}{intencion}{COLOR_RESET}")
            print(f"  • {COLOR_BOLD}Confianza:{COLOR_RESET}          {color_conf}{conf * 100:.2f}%{COLOR_RESET}")
            print(f"  • {COLOR_BOLD}Sentimiento:{COLOR_RESET}        {color_sent}{sentimiento}{COLOR_RESET}")
            print(f"  • {COLOR_BOLD}Acción Sugerida:{COLOR_RESET}    {COLOR_MAGENTA}{accion}{COLOR_RESET}")
            print(f"  • {COLOR_BOLD}Entidades Extraídas:{COLOR_RESET}")
            if entidades:
                for k, v in entidades.items():
                    print(f"      - {k}: {COLOR_YELLOW}{v}{COLOR_RESET}")
            else:
                print("      - (Ninguna entidad detectada)")
            print("-" * 65)
            
            if conf < 0.65 or intencion == "INTENCION_NO_CLARA":
                print(f"{COLOR_RED}{COLOR_BOLD}[FALLBACK ACTIVADO]{COLOR_RESET} Confianza menor al 65%. Mensaje derivado a supervisor humano.")
            return data
        else:
            print(f"{COLOR_RED}Error {resp.status_code}: {resp.text}{COLOR_RESET}")
            return None
    except Exception as ex:
        print(f"{COLOR_RED}Excepción durante el envío: {ex}{COLOR_RESET}")
        return None

def ejecutar_lote_sustentacion(base_url: str):
    if not os.path.exists(RUTA_CASOS):
        print(f"{COLOR_RED}No se encontró el archivo {RUTA_CASOS}{COLOR_RESET}")
        return

    with open(RUTA_CASOS, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    casos = data.get("casos_sustentacion", [])
    print(f"\n{COLOR_CYAN}{COLOR_BOLD}=== EJECUTANDO LOTE OFICIAL DE SUSTENTACIÓN ({len(casos)} CASOS) ==={COLOR_RESET}\n")

    for i, c in enumerate(casos, 1):
        print(f"\n{COLOR_YELLOW}[CASO {i}/{len(casos)}] {c['id']}: {c['tipo']}{COLOR_RESET}")
        print(f"Objetivo: {c['justificacion_demo']}")
        print(f"Esperado: Intención = {c['intencion_esperada']} | Sentimiento = {c['sentimiento_esperado']}")
        
        res = enviar_comando_individual(base_url, c["mensaje"])
        time.sleep(0.5)

    print(f"\n{COLOR_GREEN}{COLOR_BOLD}[+] Lote de prueba completado. Consultando estadísticas consolidadas...{COLOR_RESET}\n")
    consultar_estadisticas_resumen(base_url)

def consultar_estadisticas_resumen(base_url: str):
    try:
        resp = requests.get(f"{base_url}/nlp/estadisticas", timeout=3)
        if resp.status_code == 200:
            stats = resp.json()
            print(f"{COLOR_CYAN}{COLOR_BOLD}---------------- REPORTE ACUMULADO DE ESTADÍSTICAS ----------------{COLOR_RESET}")
            print(f"• Total Mensajes Procesados:      {COLOR_BOLD}{stats.get('total_mensajes')}{COLOR_RESET}")
            print(f"• Confianza Promedio:             {stats.get('confianza_promedio', 0)*100:.1f}%")
            print(f"• Tasa de Derivación Supervisor:  {stats.get('tasa_derivacion', 0)*100:.1f}%")
            print(f"• Alertas Críticas Activas:       {stats.get('alertas_criticas')}")
            print(f"\n• Desglose por Intención:")
            for it, cnt in stats.get("por_intencion", {}).items():
                print(f"    - {it:<22}: {cnt}")
            print(f"\n• Desglose por Sentimiento:")
            for st, cnt in stats.get("por_sentimiento", {}).items():
                print(f"    - {st:<22}: {cnt}")
            print(f"\n• Entidades Frecuentes Reportadas:")
            for ent, cnt in stats.get("entidades_frecuentes", {}).items():
                print(f"    - {ent:<30}: {cnt}")
            print(f"{COLOR_CYAN}--------------------------------------------------------------------{COLOR_RESET}\n")
        else:
            print(f"{COLOR_RED}Error consultando estadísticas: {resp.status_code}{COLOR_RESET}")
    except Exception as ex:
        print(f"{COLOR_RED}Error al conectar: {ex}{COLOR_RESET}")

def reiniciar_estadisticas(base_url: str):
    try:
        resp = requests.post(f"{base_url}/nlp/estadisticas/reiniciar", timeout=3)
        if resp.status_code == 200:
            print(f"{COLOR_GREEN}[+] Estadísticas reiniciadas en el servidor correctamente.{COLOR_RESET}\n")
        else:
            print(f"{COLOR_RED}Error al reiniciar: {resp.status_code}{COLOR_RESET}\n")
    except Exception as ex:
        print(f"{COLOR_RED}Error: {ex}{COLOR_RESET}\n")

def menu_interactivo(base_url: str):
    while True:
        banner()
        print(f"Servidor destino: {COLOR_BOLD}{base_url}{COLOR_RESET}\n")
        print("1. Enviar mensaje individual (escribir texto)")
        print("2. Ejecutar lote oficial de 6 casos de sustentación")
        print("3. Consultar estadísticas acumuladas (/nlp/estadisticas)")
        print("4. Reiniciar estadísticas (/nlp/estadisticas/reiniciar)")
        print("5. Probar conectividad con el servidor (Ping HTTP)")
        print("6. Cambiar IP / Puerto del Servidor")
        print("7. Salir")
        
        opc = input(f"\n{COLOR_YELLOW}Seleccione una opción (1-7): {COLOR_RESET}").strip()
        
        if opc == "1":
            txt = input(f"\nIngrese el mensaje operativo a clasificar:\n> ").strip()
            if txt:
                enviar_comando_individual(base_url, txt)
            else:
                print("Texto vacío.")
            input("\nPresione Enter para continuar...")
        elif opc == "2":
            ejecutar_lote_sustentacion(base_url)
            input("\nPresione Enter para continuar...")
        elif opc == "3":
            consultar_estadisticas_resumen(base_url)
            input("\nPresione Enter para continuar...")
        elif opc == "4":
            reiniciar_estadisticas(base_url)
            input("\nPresione Enter para continuar...")
        elif opc == "5":
            test_conectividad(base_url)
            input("\nPresione Enter para continuar...")
        elif opc == "6":
            nueva_ip = input("Nueva IP del Servidor: ").strip() or "127.0.0.1"
            nuevo_puerto = input("Nuevo Puerto (ej. 8001): ").strip() or "8001"
            base_url = f"http://{nueva_ip}:{nuevo_puerto}"
            print(f"Servidor actualizado a: {base_url}")
            time.sleep(1)
        elif opc == "7":
            print("Saliendo del cliente LAN.")
            break
        else:
            print("Opción inválida.")
            time.sleep(1)

def main():
    parser = argparse.ArgumentParser(description="Cliente LAN Mini-Azure LUIS AgroIca")
    parser.add_argument("--ip", default=DEFAULT_SERVER_IP, help="IP privada del Servidor (Integrante A)")
    parser.add_argument("--puerto", type=int, default=DEFAULT_PORT, help="Puerto del Servidor (defecto: 8001)")
    parser.add_argument("--lote", action="store_true", help="Ejecutar directamente el lote de sustentación")
    parser.add_argument("--stats", action="store_true", help="Consultar directamente estadísticas y salir")
    parser.add_argument("--msg", type=str, help="Enviar un mensaje directo y salir")
    
    args = parser.parse_args()
    base_url = f"http://{args.ip}:{args.puerto}"

    if args.lote:
        ejecutar_lote_sustentacion(base_url)
    elif args.stats:
        consultar_estadisticas_resumen(base_url)
    elif args.msg:
        enviar_comando_individual(base_url, args.msg)
    else:
        test_conectividad(base_url)
        menu_interactivo(base_url)

if __name__ == "__main__":
    main()
