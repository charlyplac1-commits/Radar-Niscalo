# IA del Radar del Níscalo

Esta carpeta contiene la primera tubería reproducible para convertir el escáner heurístico en un detector visual entrenado.

## Qué hace

1. Recopila automáticamente fotografías de *Lactarius deliciosus* desde iNaturalist usando únicamente fotos con licencias CC0, CC-BY o CC-BY-SA.
2. Recopila imágenes negativas de pinares/suelo forestal desde Wikimedia Commons y conserva la atribución y licencia en `manifest.csv`.
3. Entrena un clasificador ligero MobileNetV3-Small: `niscalo` frente a `no_niscalo`.
4. Exporta `models/niscalo-detector/model.onnx` para ejecutarlo en el navegador mediante ONNX Runtime Web.
5. El escáner mantiene el detector heurístico como respaldo si el modelo todavía no está disponible.

## Importante

No se descarga contenido sin licencia adecuada. iNaturalist indica que las fotos pertenecen a sus autores y que cada foto tiene su propia licencia; por eso el recolector filtra las licencias antes de descargar. Wikimedia Commons expone licencia y atribución mediante su API.

El modelo es experimental: detectar una imagen como `niscalo` no significa identificar una especie con certeza.
