# Evaluación con Elliot

Este directorio contiene la configuración para evaluar las predicciones del
recomendador con [Elliot](https://github.com/sisinflab/elliot), un framework
de evaluación reproducible de sistemas recomendadores.

## Qué se evalúa

`experiment_config.yml` usa el modelo `ProxyRecommender`: Elliot no entrena
nada, sino que carga las predicciones ya generadas por el pipeline
user-user del proyecto y las evalúa contra el conjunto de test.

- **Entrada de predicciones:**
  `datasets/training/predictions/predictions_cf_100_35.tsv`
  (100 vecinos, 35 libros por usuario; formato `user_id  book_id  prediction`).
- **Datos:** `datasets/training/train_reduced.tsv` (entrenamiento) y
  `test_reduced.tsv` (test).
- **Métricas:** nDCG, Precision, Recall, HR, MAP, MAR, MRR, ItemCoverage,
  EFD, EPC y Gini, con cutoffs 50/25/10/5.

## Instalación

Elliot no está publicado en PyPI y su `setup.py` fija dependencias obsoletas
(tensorflow 2.3, numpy 1.18, ...). Por eso se instala **sin** sus
dependencias y se fijan aquí las de runtime (ver `requirements.txt`):

```bash
# En un entorno virtual dedicado (las versiones de numpy/pandas son
# compatibles con las del proyecto principal).
pip install --no-deps -e "git+https://github.com/sisinflab/elliot.git@fc27efedaddf4a57294db14b4bcaa5553a0015d2#egg=elliot"
pip install -r elliot/requirements.txt
```

## Generar las predicciones

```bash
python scripts/build_predictions.py            # n=100 vecinos, k=35 libros
```

Requiere `models/user_profiles.pkl` (ver `scripts/build_user_profiles.py`
y `docs/DATA.md`).

## Ejecutar el experimento

```bash
cd elliot
python experiment.py
```

Los resultados se escriben en `elliot/results/` (métricas por cutoff en
`results/knn/user-user/`, recomendaciones en `results/rec_res`, etc.).
Los resultados incluidos en el repositorio corresponden a la última
ejecución del experimento con las predicciones `cf_100_35`.
