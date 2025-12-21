# 🐟 Medición de Peces

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

---

## 🖥️ Uso de la GUI

### Cargar imagen
- Botón **“Seleccionar Imagen”**

### Corrección de distorsión (opcional)
- Habilitar la casilla de corrección
- Ajustar **alpha**
- Cargar calibración **YAML/JSON** si aplica
- Vista previa disponible

### Escala

**Automática**
- Usar **Detectar ArUco** (marcador 4x4 de **100 mm** por defecto)
- Botón **“Ver Detección”** para previsualizar

**Manual**
- Ingresar píxeles y cm
- Presionar **“Aplicar Escala Manual”**

### Segmentación
- Elegir dispositivo (**cpu / cuda**)
- Presionar **“Generar Segmentación”**
- Visualización de máscara, overlay e IDs

### Análisis morfológico
- Botón **“Analizar Morfología”**
- Usa la máscara coloreada
- Calcula longitudes y profundidad corporal
- Muestra resultados en tabla e imagen anotada

### Guardar resultados
- Botón **“Guardar Resultados”**
- Exporta **TXT** con:
  - Medidas (px y cm)
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

Las mediciones se muestran en **píxeles** y se convierten a **cm** según la escala actual.

---

## 🎯 Notas de calibración y ArUco

- ArUco esperado: **4x4 – 100 mm**
- Ajustar tamaño en `utils.detect_aruco_marker` si se usa otro
- Para **SIMPLE_PINHOLE vía YAML**:
  - `model: SIMPLE_PINHOLE`
  - Parámetros: `[f, cx, cy]`
  - Tamaño de imagen requerido
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

## 📄 Licencia

Define aquí la licencia del proyecto (**MIT**, **Apache-2.0**, etc.).  
Añade el texto completo si aplica.
