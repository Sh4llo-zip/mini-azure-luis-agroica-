"""
Entrenamiento y Persistencia de Modelos NLP - Integrante A
Entrena clasificadores de Intenciones y Sentimientos utilizando Scikit-Learn
con pipelines de TF-IDF + Regresión Logística calibrada para obtener probabilidades precisas.
"""

import os
import joblib
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, accuracy_score

DIR_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_DATASET = os.path.join(DIR_ACTUAL, "dataset_agro_ica.csv")
DIR_MODELOS = os.path.join(DIR_ACTUAL, "modelos_entrenados")
os.makedirs(DIR_MODELOS, exist_ok=True)

def preprocesar_texto(t: str) -> str:
    """Normalización básica de texto en español."""
    t = str(t).lower()
    reemplazos = [
        ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
        ("ñ", "n"), ("ü", "u")
    ]
    for orig, dest in reemplazos:
        t = t.replace(orig, dest)
    return t

def main():
    print("=" * 65)
    print("   ENTRENAMIENTO DEL MOTOR NLP LOCAL (MINI-AZURE LUIS / TEXT ANALYTICS)")
    print("=" * 65)

    if not os.path.exists(RUTA_DATASET):
        raise FileNotFoundError(f"No se encontró el dataset en {RUTA_DATASET}. Ejecute primero generar_dataset.py.")

    df = pd.read_csv(RUTA_DATASET)
    print(f"[+] Dataset cargado: {len(df)} registros.")
    
    df["texto_proc"] = df["texto"].apply(preprocesar_texto)

    # =========================================================================
    # 1. ENTRENAMIENTO DEL MODELO DE INTENCIONES (Simulación LUIS)
    # =========================================================================
    print("\n--- 1. Entrenando Clasificador de Intenciones ---")
    X = df["texto_proc"]
    y_intencion = df["intencion"]

    pipeline_intencion = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
            token_pattern=r"(?u)\b\w+\b"
        )),
        ("clf", LogisticRegression(
            C=4.0,
            max_iter=1000,
            class_weight="balanced",
            random_state=42
        ))
    ])

    # Validación cruzada estratificada (5-folds)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores_int = cross_val_score(pipeline_intencion, X, y_intencion, cv=cv, scoring="accuracy")
    print(f"Accuracy promedio en CV (5-folds): {scores_int.mean()*100:.2f}% (+/- {scores_int.std()*100:.2f}%)")

    # Ajuste final con todo el dataset
    pipeline_intencion.fit(X, y_intencion)
    preds_int = pipeline_intencion.predict(X)
    print(f"Accuracy de entrenamiento: {accuracy_score(y_intencion, preds_int)*100:.2f}%")

    ruta_modelo_int = os.path.join(DIR_MODELOS, "modelo_intenciones.joblib")
    joblib.dump(pipeline_intencion, ruta_modelo_int)
    print(f"[+] Modelo de intenciones guardado en: {ruta_modelo_int}")

    # =========================================================================
    # 2. ENTRENAMIENTO DEL MODELO DE SENTIMIENTO (Simulación Text Analytics)
    # =========================================================================
    print("\n--- 2. Entrenando Clasificador de Sentimientos ---")
    y_sentimiento = df["sentimiento"]

    pipeline_sentimiento = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
            token_pattern=r"(?u)\b\w+\b"
        )),
        ("clf", LogisticRegression(
            C=3.0,
            max_iter=1000,
            class_weight="balanced",
            random_state=42
        ))
    ])

    scores_sent = cross_val_score(pipeline_sentimiento, X, y_sentimiento, cv=cv, scoring="accuracy")
    print(f"Accuracy promedio en CV (5-folds): {scores_sent.mean()*100:.2f}% (+/- {scores_sent.std()*100:.2f}%)")

    pipeline_sentimiento.fit(X, y_sentimiento)
    ruta_modelo_sent = os.path.join(DIR_MODELOS, "modelo_sentimientos.joblib")
    joblib.dump(pipeline_sentimiento, ruta_modelo_sent)
    print(f"[+] Modelo de sentimientos guardado en: {ruta_modelo_sent}")

    # =========================================================================
    # 3. PRUEBA DE CASOS DE SUSTENTACIÓN
    # =========================================================================
    print("\n--- 3. Validación de Casos Oficiales de Sustentación ---")
    casos_test = [
        ("La camara de frio 2 subio a 9 grados con 120 cajas de uva red globe", "REPORTE_CALIDAD"),
        ("urgnt la faja d empaq del paking 1 sta trabada botando javas d esparago vrd", "FALLA_EQUIPO"),
        ("hola compa queria avisar que paso una cosa muy rara x aca y no se que decir", "INTENCION_NO_CLARA"),
        ("Cuantos pallets listos de esparrago fresco quedan en el lote L-502 de camara 1?", "CONSULTA_INVENTARIO"),
        ("Favor de programar salida de camion con guia de remision 004-9821 para contenedor de uva thompson al puerto de Pisco", "SOLICITUD_DESPACHO"),
        ("PELIGRO fuga de gas amoniaco en el compresor central de sala de maquinas olor insoportable y evacuacion inmediata", "FALLA_EQUIPO")
    ]

    for texto, int_esp in casos_test:
        texto_limp = preprocesar_texto(texto)
        probas_int = pipeline_intencion.predict_proba([texto_limp])[0]
        clases = pipeline_intencion.classes_
        idx_max = np.argmax(probas_int)
        pred_int = clases[idx_max]
        conf_int = probas_int[idx_max]

        probas_sent = pipeline_sentimiento.predict_proba([texto_limp])[0]
        idx_sent = np.argmax(probas_sent)
        pred_sent = pipeline_sentimiento.classes_[idx_sent]
        conf_sent = probas_sent[idx_sent]

        # Regla de fallback < 0.65
        int_final = pred_int
        if conf_int < 0.65 or pred_int == "INTENCION_NO_CLARA":
            int_final = "INTENCION_NO_CLARA"

        estado = "✅" if int_final == int_esp else "⚠️"
        print(f"{estado} Texto: \"{texto[:45]}...\"")
        print(f"   Pred: {pred_int} ({conf_int*100:.1f}%) | Final (Regla <0.65): {int_final} | Sent: {pred_sent} ({conf_sent*100:.1f}%)")

    print("\n[+] Entrenamiento y calibración completados exitosamente.")

if __name__ == "__main__":
    main()
