# 🐟 FishMetrics

Aplicación de escritorio en **Tkinter** para segmentar peces en imágenes, detectar marcadores **ArUco** y obtener mediciones morfológicas (**longitud total, estándar, cefálica y profundidad corporal**).  
Incluye utilidades de **corrección de distorsión** y **escalado manual/automático**.

---

## 📦 Requisitos

- **Python 3.9+** (recomendado)
- Paquetes principales:
  - `opencv-contrib-python`
  - `Pillow`
  - `numpy`
  - `PyYAML`
  - `tkinter` (generalmente incluido)
  - `torch`
  - `segmentation_models_pytorch`
- Checkpoint de segmentación:  
  - `best_miou_V5.pth` (**debe existir**)
- Script de inferencia:
  - `infer2_seg.py`

### Ejemplo de instalación (CPU)

```bash
pip install opencv-contrib-python Pillow numpy PyYAML segmentation-models-pytorch torch
```

> Si usarás **CUDA**, instala la variante de `torch` compatible con tu GPU.

---

## 📁 Estructura breve

- `main.py`: punto de entrada de la GUI  
- `gui.py` y `src/helpers/…`: lógica de interfaz, segmentación, ArUco, escala, resultados y distorsión  
- `morphology.py`: cálculo de medidas a partir de la máscara segmentada  
- `utils.py`: ArUco, segmentación por CLI y utilidades varias  
- `infer2_seg.py`: script de segmentación (**DeepLabV3+**)  
- `preds/`: carpeta de salida de segmentación (se crea al correr)

---

## ▶️ Ejecutar la aplicación

Desde la raíz del repositorio:

```bash
python src/main.py
```

Al iniciar por primera vez se crea `config.ini` en la raíz del proyecto. Las
preferencias personales, como el tema claro u oscuro y la última carpeta usada
para abrir una imagen, se guardan allí y se restauran automáticamente en la
siguiente ejecución.

---

## 🖥️ Uso de la GUI

### Cargar imagen
- Botón **“Seleccionar Imagen”**
- El selector vuelve a abrir la última carpeta utilizada

### Corrección de distorsión (opcional)
- Habilitar la casilla de corrección
- Ajustar **alpha**
- Cargar calibración **YAML/JSON** si aplica
- Vista previa disponible

### Escala

**Automática**
- Medir el lado exterior del marcador cuadrado
- Ingresar esa medida y seleccionar **mm** o **cm**
- Usar **Detectar ArUco** (no se asume ninguna dimensión)
- Botón **“Ver Detección”** para previsualizar

**Manual**
- Ingresar píxeles y cm
- Presionar **“Aplicar Escala Manual”**

### Segmentación
- Elegir dispositivo (**cpu / cuda**)
- Presionar **“Generar Segmentación”**
- Visualización de máscara, overlay e IDs

### Análisis morfométrico
- Botón **“Analizar morfometría”**
- Usa la máscara coloreada
- Calcula longitudes y profundidad corporal
- Muestra resultados en tabla e imagen anotada, con los rótulos expresados en cm
- Permite alternar las mediciones entre la máscara y un overlay sobre la imagen original
- Después del primer cálculo, usar **“Reanalizar morfometría”** para reemplazar las mediciones con un nuevo análisis
- Si el nuevo análisis falla, se conservan las últimas mediciones válidas

### Guardar resultados
- Botón **“Exportar YAML”**
- Exporta **YAML** con:
  - Cada medida en m, cm, mm y píxeles
  - Metadatos de escala y corrección

---

## ⌨️ Segmentación por línea de comandos

```bash
python seg/infer2_seg.py   --ckpt seg/best_miou_V5.pth   --input ruta/a/imagen.jpg   --out preds   --device cpu
```

> Usa `--device cuda` si tienes GPU y `torch` con CUDA.

### Archivos generados

- `*_mask.png`: máscara coloreada (fondo negro)
- `*_overlay.png`: mezcla con la imagen original
- `*_mask_ids.png`: IDs de clases (`uint16`)
- `*_mask_index_vis.png`: IDs visibles en escala de grises

---

## 📏 Medidas disponibles

- **Longitud Total** (hocico a aleta caudal)
- **Longitud Estándar** (hocico a fin de cuerpo)
- **Longitud Cefálica**
- **Profundidad Corporal**  
  (máxima distancia dorsal–ventral en el cuerpo)

La tabla muestra una sola unidad a la vez, seleccionable entre **m, cm, mm y
píxeles** (cm por defecto). En las imágenes anotadas, los rótulos se muestran
en **cm** según la escala actual.

---

## 🎯 Notas de calibración y ArUco

- ArUco esperado: diccionario **4x4_50**
- La longitud real de un lado es obligatoria y se ingresa en la interfaz
- Medir el cuadrado de borde exterior a borde exterior; no se asume un tamaño predeterminado
- Modelos de calibración admitidos vía YAML:
  - `SIMPLE_PINHOLE`: parámetros `[f, cx, cy]`
  - `RADIAL`: parámetros `[f, cx, cy, k1, k2]`
  - `width` y `height` son obligatorios; los intrínsecos se escalan si la
    imagen procesada tiene otra resolución
- Los YAML submarinos pueden incluir `non_svp_model: FLATPORT` y sus ocho
  `non_svp_parameters`. FishMetrics conserva y exporta esos datos, pero la
  rectificación 2D aplica solamente `k1` y `k2`: la refracción de un puerto
  plano no tiene una corrección exacta única sin conocer la profundidad de la
  escena.
- JSON de calibración por defecto: `data.json`
  - Puede cargarse otro archivo

---

## 🛠️ Solución de problemas

- **Segmentación deshabilitada**:
  - Verifica que existan `infer2_seg.py` y `best_miou_V5.pth`
- **CUDA no disponible**:
  - Verifica:
    ```python
    torch.cuda.is_available()
    ```
- **No se detecta ArUco**:
  - Buena iluminación y contraste
  - Tamaño mínimo recomendado: **20–30 px**
  - Si persiste, usar **escala manual**
- **Imágenes no visibles en GUI**:
  - Revisar permisos de lectura
  - Verificar formatos compatibles

---

## ⚡ Comandos rápidos

```bash
# Lanzar GUI
python src/main.py

# Segmentar una imagen (CPU)
python seg/infer2_seg.py --ckpt seg/best_miou_V5.pth --input sample.jpg --out preds --device cpu
```

---
