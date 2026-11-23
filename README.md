# Práctica Calificada: Mini-Azure LUIS & Text Analytics Local (AgroIca)
## Proyecto Completo: Integrante A (Motor NLP & API Servidor) + Integrante B (Cliente LAN & Dashboard)

Este proyecto implementa un microservicio On-Premise completo de Procesamiento del Lenguaje Natural (NLP) y analítica de comunicaciones para una empresa agroexportadora de Ica (uva de mesa y espárragos), reemplazando servicios en la nube como Azure LUIS y Azure Text Analytics.

---

## 📂 Arquitectura y Estructura de Archivos

```text
proyecto_nlp_cliente/
├── dataset_agro_ica.csv          # Corpus en español con 177 ejemplos operativos reales
├── generar_dataset.py            # Generador del dataset con 4 intenciones + casos ambiguos
├── extractor_entidades.py        # Módulo extractor de entidades (PRODUCTO, AREA, CANTIDAD, CODIGO_LOTE)
├── entrenar_modelo.py            # Pipeline TF-IDF + Scikit-Learn calibrado y persistencia en disco
├── modelos_entrenados/           # Artefactos .joblib serializados del modelo entrenado
│   ├── modelo_intenciones.joblib
│   └── modelo_sentimientos.joblib
├── servidor_api_nlp.py           # API REST de producción (FastAPI en 0.0.0.0:8001) [INTEGRANTE A]
├── app_dashboard.py              # Dashboard interactivo en tiempo real (Streamlit) [INTEGRANTE B]
├── index.html                    # Dashboard alternativo en HTML5 + Tailwind + Chart.js [INTEGRANTE B]
├── cliente_lan.py                # Cliente CLI de consola interactivo y por lotes [INTEGRANTE B]
├── casos_de_prueba.json          # Batería oficial de los 6 casos de prueba de sustentación
├── FICHA_TECNICA_ARQUITECTURA.md # Ficha técnica oficial, topología y cuadro comparativo Azure vs Local
└── README.md                     # Este manual de instrucciones
```

---

## ⚡ Guía de Ejecución Rápida (Todo en tu PC)

Para demostrar todo el sistema tú solo ante el profesor, sigue estos 2 sencillos pasos:

### 1. Iniciar el Servidor API NLP (Terminal 1)
Abre una terminal de PowerShell y corre:
```powershell
cd C:\Users\Alumno\.gemini\antigravity\scratch\proyecto_nlp_cliente
python servidor_api_nlp.py
```
> El servidor cargará los modelos `.joblib` y quedará escuchando en `http://0.0.0.0:8001`.

### 2. Iniciar el Dashboard en Tiempo Real (Terminal 2)
Abre otra ventana de PowerShell (sin cerrar la primera) y corre:
```powershell
cd C:\Users\Alumno\.gemini\antigravity\scratch\proyecto_nlp_cliente
streamlit run app_dashboard.py
```
> Se abrirá automáticamente tu navegador en `http://localhost:8501`.

*(Alternativa sin terminal: También puedes simplemente hacer doble clic en el archivo `index.html` para abrir el Dashboard Web en Chrome/Edge).*

---

## 🎯 Demostración en Vivo para la Sustentación (Paso a Paso)

1. **Verificar Conexión:**
   En la barra lateral izquierda del Dashboard, haz clic en **"🔍 Probar Conectividad LAN"** (mostrará status verde y latencia de ~2 ms).
2. **Limpiar el Tablero:**
   Haz clic en **"🧹 Reiniciar Estadísticas"** para que los contadores arranquen en cero.
3. **Disparar la Batería Oficial de Pruebas:**
   Haz clic en el botón **"⚡ Ejecutar Lote de Sustentación (6 Casos)"**:
   * **Caso A (Calidad con entidades):** `"La camara de frio 2 subio a 9 grados con 120 cajas de uva red globe"` $\rightarrow$ `REPORTE_CALIDAD` (`ALERTA_CRITICA_CALIDAD`).
   * **Caso B (Errores ortográficos de campo):** `"urgnt la faja d empaq del paking 1 sta trabada botando javas d esparago vrd"` $\rightarrow$ `FALLA_EQUIPO`.
   * **Caso C (Ambiguo - Regla de Incertidumbre):** `"hola compa queria avisar que paso una cosa muy rara x aca y no se que decir"` $\rightarrow$ Activa el fallback: `INTENCION_NO_CLARA` y `DERIVAR_A_SUPERVISOR` (< 65% confianza).
   * **Caso D (Inventario):** `"Cuantos pallets listos de esparrago fresco quedan en el lote L-502 de camara 1?"` $\rightarrow$ `CONSULTA_INVENTARIO`.
   * **Caso E (Despacho):** `"Favor de programar salida de camion con guia de remision 004-9821 para contenedor de uva thompson al puerto de Pisco"` $\rightarrow$ `SOLICITUD_DESPACHO`.
   * **Caso F (Negativo crítico):** `"PELIGRO fuga de gas amoniaco en el compresor central de sala de maquinas..."` $\rightarrow$ Sentimiento `NEGATIVO`, `EMERGENCIA_PARADA_PLANTA`.
4. **Explicar la Analítica Operativa:**
   Ve a la pestaña **"📊 Tablero de Analítica en Tiempo Real"** y muestra los gráficos de intención, de sentimiento, las entidades detectadas y la bitácora reciente.

---

## 🔄 ¿Cómo reentrenar el modelo si quieres agregar más frases?
Si deseas modificar o ampliar el dataset:
1. Edita `dataset_agro_ica.csv` o `generar_dataset.py`.
2. Ejecuta:
   ```powershell
   python entrenar_modelo.py
   ```
3. Los nuevos modelos se guardarán automáticamente en `modelos_entrenados/` listos para ser consumidos por el servidor.
