import cv2
import numpy as np
from utils import draw_text_with_outline

def detect_fish_orientation(head_coords, body_coords, fins_coords):
    """
    Detecta la orientación del pez basándose en la posición de los segmentos.
    
    Returns:
        str: 'left' si el hocico está a la izquierda, 'right' si está a la derecha
    """
    if head_coords.size == 0 or body_coords.size == 0:
        return 'left'  # Orientación por defecto
    
    # IMPORTANTE: las coordenadas están en formato (fila, columna) = (y, x)
    # Para orientación necesitamos comparar las posiciones X (columna)
    head_center_x = np.mean(head_coords[:, 1])  # Columna X (posición horizontal)
    body_center_x = np.mean(body_coords[:, 1])  # Columna X (posición horizontal)
    
    print(f"DEBUG: Centro X de cabeza: {head_center_x:.1f}")
    print(f"DEBUG: Centro X de cuerpo: {body_center_x:.1f}")
    
    # CORREGIDO: Si la cabeza está a la izquierda del cuerpo (menor X), el pez mira hacia la IZQUIERDA
    if head_center_x < body_center_x:
        print("DEBUG: Cabeza está a la IZQUIERDA del cuerpo -> Pez mira hacia la IZQUIERDA")
        return 'left'   # Cabeza a la izquierda, mira hacia la izquierda
    else:
        print("DEBUG: Cabeza está a la DERECHA del cuerpo -> Pez mira hacia la DERECHA")
        return 'right'  # Cabeza a la derecha, mira hacia la derecha

def get_fish_extremes(fish_coords, head_coords, body_coords, fins_coords, orientation):
    """
    Encuentra los puntos extremos del pez según su orientación.
    NOTA: Las coordenadas están en formato (fila, columna) = (y, x)
    Pero devolvemos en formato (x, y) para dibujo
    """
    
    print(f"DEBUG: Buscando extremos para orientación '{orientation}'")
    
    if orientation == 'left':
        # Pez mirando hacia la IZQUIERDA: hocico en lado izquierdo (X mínima)
        hocico_idx = np.argmin(fish_coords[:, 1])  # Menor X (más a la izquierda)
        punto_hocico = (fish_coords[hocico_idx, 1], fish_coords[hocico_idx, 0])  # Convertir a (x,y)
        
        # Cola en lado derecho (X máxima)
        if fins_coords.size > 0:
            cola_idx = np.argmax(fins_coords[:, 1])  # Mayor X en aletas
            fin_aleta_caudal = (fins_coords[cola_idx, 1], fins_coords[cola_idx, 0])
        else:
            cola_idx = np.argmax(fish_coords[:, 1])  # Mayor X en pez completo
            fin_aleta_caudal = (fish_coords[cola_idx, 1], fish_coords[cola_idx, 0])
            
        # Fin del cuerpo (lado derecho)
        if body_coords.size > 0:
            fin_cuerpo_idx = np.argmax(body_coords[:, 1])
            fin_cuerpo = (body_coords[fin_cuerpo_idx, 1], body_coords[fin_cuerpo_idx, 0])
        else:
            fin_cuerpo = fin_aleta_caudal
            
        # Fin de cabeza (lado derecho de la cabeza)
        if head_coords.size > 0:
            fin_cabeza_idx = np.argmax(head_coords[:, 1])
            fin_cabeza = (head_coords[fin_cabeza_idx, 1], head_coords[fin_cabeza_idx, 0])
        else:
            fin_cabeza = punto_hocico
            
    else:  # orientation == 'right'
        # Pez mirando hacia la DERECHA: hocico en lado derecho (X máxima)
        hocico_idx = np.argmax(fish_coords[:, 1])  # Mayor X (más a la derecha)
        punto_hocico = (fish_coords[hocico_idx, 1], fish_coords[hocico_idx, 0])  # Convertir a (x,y)
        
        # Cola en lado izquierdo (X mínima)
        if fins_coords.size > 0:
            cola_idx = np.argmin(fins_coords[:, 1])  # Menor X en aletas
            fin_aleta_caudal = (fins_coords[cola_idx, 1], fins_coords[cola_idx, 0])
        else:
            cola_idx = np.argmin(fish_coords[:, 1])  # Menor X en pez completo
            fin_aleta_caudal = (fish_coords[cola_idx, 1], fish_coords[cola_idx, 0])
            
        # Fin del cuerpo (lado izquierdo)
        if body_coords.size > 0:
            fin_cuerpo_idx = np.argmin(body_coords[:, 1])
            fin_cuerpo = (body_coords[fin_cuerpo_idx, 1], body_coords[fin_cuerpo_idx, 0])
        else:
            fin_cuerpo = fin_aleta_caudal
            
        # Fin de cabeza (lado izquierdo de la cabeza)
        if head_coords.size > 0:
            fin_cabeza_idx = np.argmin(head_coords[:, 1])
            fin_cabeza = (head_coords[fin_cabeza_idx, 1], head_coords[fin_cabeza_idx, 0])
        else:
            fin_cabeza = punto_hocico
    
    print(f"DEBUG: Hocico en: {punto_hocico}")
    print(f"DEBUG: Cola en: {fin_aleta_caudal}")
    print(f"DEBUG: Fin cuerpo en: {fin_cuerpo}")
    print(f"DEBUG: Fin cabeza en: {fin_cabeza}")
    
    return punto_hocico, fin_aleta_caudal, fin_cuerpo, fin_cabeza

def measure_morphology_with_overlay(
    image_path,
    original_image_path=None,
    cm_per_pixel=1.0,
    show_visualization=True,
    annotated_output_path="mediciones_pez.png",
    overlay_output_path="mediciones_pez_overlay.png",
):
    """
    Carga una imagen de pez segmentado y calcula sus medidas morfológicas.
    Genera las mediciones tanto sobre la máscara como, opcionalmente, sobre
    la imagen original usada durante la segmentación.
    """
    print(f"DEBUG: Analizando imagen: {image_path}")

    cm_per_pixel = float(cm_per_pixel)
    if not np.isfinite(cm_per_pixel) or cm_per_pixel <= 0:
        raise ValueError("cm_per_pixel debe ser un número finito mayor que cero")
    
    # Cargar la imagen
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: No se pudo cargar la imagen desde {image_path}")
        return None, None, None

    print(f"DEBUG: Imagen cargada, dimensiones: {img.shape}")

    # --- 1. Crear máscaras para cada color ---
    # Definir los colores para cada segmento (BGR)
    red_color = np.array([0, 0, 255])      # Cabeza (rojo)
    green_color = np.array([0, 255, 0])    # Cuerpo (verde)
    blue_color = np.array([255, 0, 0])     # Aletas (azul)

    head_mask = cv2.inRange(img, red_color, red_color)
    body_mask = cv2.inRange(img, green_color, green_color)
    fins_mask = cv2.inRange(img, blue_color, blue_color)
    
    # Combinar todas las máscaras para tener la silueta completa del pez
    full_fish_mask = head_mask + body_mask + fins_mask

    # Debug: mostrar píxeles encontrados
    head_pixels = cv2.countNonZero(head_mask)
    body_pixels = cv2.countNonZero(body_mask)
    fins_pixels = cv2.countNonZero(fins_mask)
    total_pixels = cv2.countNonZero(full_fish_mask)
    
    print(f"DEBUG: Píxeles encontrados - Cabeza: {head_pixels}, Cuerpo: {body_pixels}, Aletas: {fins_pixels}, Total: {total_pixels}")

    # --- 2. Verificar que hay píxeles segmentados ---
    if total_pixels == 0:
        print("Error: No se encontraron píxeles segmentados en la imagen.")
        print("Asegúrate de que la imagen tenga segmentación con colores RGB(255,0,0), RGB(0,255,0), RGB(0,0,255)")
        return None, None, None

    # Encontrar coordenadas de cada segmento
    fish_coords = np.column_stack(np.where(full_fish_mask > 0))
    head_coords = np.column_stack(np.where(head_mask > 0))
    body_coords = np.column_stack(np.where(body_mask > 0))
    fins_coords = np.column_stack(np.where(fins_mask > 0))
    
    print(f"DEBUG: Coordenadas - Pez: {len(fish_coords)}, Cabeza: {len(head_coords)}, Cuerpo: {len(body_coords)}, Aletas: {len(fins_coords)}")

    # --- 3. Fallbacks para segmentos faltantes ---
    if head_coords.size == 0:
        print("Advertencia: No se encontraron píxeles de cabeza (rojos)")
        # Usar primer tercio del pez como cabeza
        head_coords = fish_coords[:len(fish_coords)//3]
    
    if body_coords.size == 0:
        print("Advertencia: No se encontraron píxeles de cuerpo (verdes)")
        # Usar tercio medio del pez como cuerpo
        body_coords = fish_coords[len(fish_coords)//3:2*len(fish_coords)//3]
    
    if fins_coords.size == 0:
        print("Advertencia: No se encontraron píxeles de aletas (azules)")
        # Usar último tercio del pez como aletas
        fins_coords = fish_coords[2*len(fish_coords)//3:]

    # --- 4. Detectar orientación del pez ---
    orientation = detect_fish_orientation(head_coords, body_coords, fins_coords)
    print(f"DEBUG: Orientación detectada: Pez mirando hacia la {'izquierda' if orientation == 'left' else 'derecha'}")
    
    try:
        punto_hocico, fin_aleta_caudal, fin_cuerpo, fin_cabeza = get_fish_extremes(
            fish_coords, head_coords, body_coords, fins_coords, orientation
        )
    except (IndexError, ValueError) as e:
        print(f"Error al encontrar puntos clave: {e}")
        return None, None, None

    # --- 5. Calcular las mediciones ---
    try:
        # Todas las coordenadas ya están en formato (x, y)
        longitud_total = abs(fin_aleta_caudal[0] - punto_hocico[0])
        longitud_estandar = abs(fin_cuerpo[0] - punto_hocico[0])
        longitud_cefalica = abs(fin_cabeza[0] - punto_hocico[0])
        
        print(f"DEBUG: Longitudes calculadas - Total: {longitud_total:.1f}, Estándar: {longitud_estandar:.1f}, Cefálica: {longitud_cefalica:.1f}")
        
        # Para la profundidad corporal, encontramos la máxima distancia vertical en el cuerpo
        profundidad_corporal = 0
        profundidad_x_pos = 0
        punto_dorsal = punto_hocico
        punto_ventral = punto_hocico
        
        if body_coords.size > 0:
            # Buscar en cada columna X del cuerpo la máxima distancia vertical
            unique_x_body = np.unique(body_coords[:, 1])  # Columnas X únicas
            
            for x_col in unique_x_body:
                # Encontrar todas las filas Y en esta columna X
                ys_in_col = body_coords[body_coords[:, 1] == x_col][:, 0]
                if len(ys_in_col) > 1:  # Necesitamos al menos 2 puntos
                    current_depth = np.max(ys_in_col) - np.min(ys_in_col)
                    if current_depth > profundidad_corporal:
                        profundidad_corporal = current_depth
                        profundidad_x_pos = x_col
                        # Puntos en formato (x, y) para dibujo
                        punto_dorsal = (x_col, np.min(ys_in_col))
                        punto_ventral = (x_col, np.max(ys_in_col))
        
        print(f"DEBUG: Profundidad corporal: {profundidad_corporal:.1f} en X={profundidad_x_pos}")

    except Exception as e:
        print(f"Error al calcular mediciones: {e}")
        return None, None, None

    # Guardar resultados en un diccionario
    mediciones = {
        "Longitud Total": longitud_total,
        "Longitud Estándar": longitud_estandar,
        "Longitud Cefálica": longitud_cefalica,
        "Profundidad Corporal": profundidad_corporal
    }

    # --- 6. Visualizar los resultados ---
    try:
        annotation_data = {
            "punto_hocico": punto_hocico,
            "fin_aleta_caudal": fin_aleta_caudal,
            "fin_cuerpo": fin_cuerpo,
            "fin_cabeza": fin_cabeza,
            "punto_dorsal": punto_dorsal,
            "punto_ventral": punto_ventral,
            "orientation": orientation,
        }
        img_visual = draw_morphology_annotations(
            img,
            mediciones,
            annotation_data,
            cm_per_pixel,
        )


        # Mostrar la imagen (si se especifica)
        if show_visualization:
            cv2.imshow('Mediciones Morfologicas', img_visual)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
        # Guardar la vista sobre la máscara.
        if annotated_output_path and not cv2.imwrite(str(annotated_output_path), img_visual):
            raise OSError(f"No se pudo guardar {annotated_output_path}")

        # El overlay es opcional para mantener disponibles las mediciones aun
        # cuando la imagen base haya sido movida o eliminada.
        overlay_visual = None
        if original_image_path:
            try:
                original_img = cv2.imread(str(original_image_path))
                if original_img is None:
                    raise ValueError(
                        f"No se pudo cargar la imagen original desde {original_image_path}"
                    )

                if original_img.shape[:2] != img.shape[:2]:
                    original_img = cv2.resize(
                        original_img,
                        (img.shape[1], img.shape[0]),
                        interpolation=cv2.INTER_AREA,
                    )

                overlay_visual = draw_morphology_annotations(
                    original_img,
                    mediciones,
                    annotation_data,
                    cm_per_pixel,
                )
                if overlay_output_path and not cv2.imwrite(str(overlay_output_path), overlay_visual):
                    raise OSError(f"No se pudo guardar {overlay_output_path}")
            except (OSError, ValueError, cv2.error) as overlay_error:
                print(f"No se pudo generar el overlay morfométrico: {overlay_error}")
                overlay_visual = None

        print(f"Mediciones calculadas exitosamente (orientación: {orientation}):")
        for nombre, valor in mediciones.items():
            print(f"  {nombre}: {valor * cm_per_pixel:.2f} cm ({valor:.1f} píxeles)")

        return mediciones, img_visual, overlay_visual
        
    except Exception as e:
        print(f"Error durante la visualización: {e}")
        return mediciones, None, None


def draw_morphology_annotations(base_image, measurements, annotation_data, cm_per_pixel):
    """Dibuja las guías morfométricas y etiqueta sus valores en centímetros."""
    img_visual = base_image.copy()
    punto_hocico = tuple(map(int, annotation_data["punto_hocico"]))
    fin_aleta_caudal = tuple(map(int, annotation_data["fin_aleta_caudal"]))
    fin_cuerpo = tuple(map(int, annotation_data["fin_cuerpo"]))
    fin_cabeza = tuple(map(int, annotation_data["fin_cabeza"]))
    punto_dorsal = tuple(map(int, annotation_data["punto_dorsal"]))
    punto_ventral = tuple(map(int, annotation_data["punto_ventral"]))
    orientation = annotation_data["orientation"]

    color_linea = (0, 255, 255)
    color_punto = (255, 0, 255)
    color_texto = (0, 255, 255)
    color_contorno = (0, 0, 0)
    grosor_linea = 3
    radio_punto = 6
    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = 0.7
    grosor_texto = 2
    grosor_contorno = 5

    def label(name, short_name):
        return f"{short_name}: {measurements[name] * cm_per_pixel:.2f} cm"

    # Longitud total
    y_pos = max(10, punto_hocico[1] - 80)
    cv2.line(img_visual, (punto_hocico[0], y_pos), (fin_aleta_caudal[0], y_pos), color_linea, grosor_linea)
    cv2.circle(img_visual, punto_hocico, radio_punto, color_punto, -1)
    cv2.circle(img_visual, fin_aleta_caudal, radio_punto, color_punto, -1)
    text_pos = (min(punto_hocico[0], fin_aleta_caudal[0]), max(25, y_pos - 15))
    draw_text_with_outline(
        img_visual, label("Longitud Total", "Total"), text_pos, font, font_scale,
        color_texto, color_contorno, grosor_texto, grosor_contorno,
    )

    # Longitud estándar
    y_pos = max(50, punto_hocico[1] - 40)
    cv2.line(img_visual, (punto_hocico[0], y_pos), (fin_cuerpo[0], y_pos), color_linea, grosor_linea)
    cv2.circle(img_visual, fin_cuerpo, radio_punto, color_punto, -1)
    text_pos = (min(punto_hocico[0], fin_cuerpo[0]), max(65, y_pos - 15))
    draw_text_with_outline(
        img_visual, label("Longitud Estándar", "Estandar"), text_pos, font, font_scale,
        color_texto, color_contorno, grosor_texto, grosor_contorno,
    )

    # Longitud cefálica
    y_pos = min(img_visual.shape[0] - 60, fin_cabeza[1] + 60)
    cv2.line(img_visual, (punto_hocico[0], y_pos), (fin_cabeza[0], y_pos), color_linea, grosor_linea)
    cv2.circle(img_visual, fin_cabeza, radio_punto, color_punto, -1)
    text_pos = (min(punto_hocico[0], fin_cabeza[0]), min(img_visual.shape[0] - 5, y_pos + 25))
    draw_text_with_outline(
        img_visual, label("Longitud Cefálica", "Cefalica"), text_pos, font, font_scale,
        color_texto, color_contorno, grosor_texto, grosor_contorno,
    )

    # Profundidad corporal
    if measurements["Profundidad Corporal"] > 0:
        cv2.line(img_visual, punto_dorsal, punto_ventral, color_linea, grosor_linea)
        cv2.circle(img_visual, punto_dorsal, radio_punto, color_punto, -1)
        cv2.circle(img_visual, punto_ventral, radio_punto, color_punto, -1)
        text_pos = (punto_dorsal[0] + 15, punto_dorsal[1] + 60)
        draw_text_with_outline(
            img_visual, label("Profundidad Corporal", "Profundidad"), text_pos, font, font_scale,
            color_texto, color_contorno, grosor_texto, grosor_contorno,
        )

    orientation_text = f'Orientacion: {"Izquierda" if orientation == "left" else "Derecha"}'
    draw_text_with_outline(
        img_visual, orientation_text, (10, 30), font, 0.6,
        (255, 255, 0), (0, 0, 0), 2, 4,
    )
    return img_visual


def measure_morphology(
    image_path,
    show_visualization=True,
    cm_per_pixel=1.0,
    annotated_output_path="mediciones_pez.png",
):
    """API compatible para generar la vista anotada sobre la máscara."""
    measurements, annotated_image, _ = measure_morphology_with_overlay(
        image_path,
        cm_per_pixel=cm_per_pixel,
        show_visualization=show_visualization,
        annotated_output_path=annotated_output_path,
    )
    return measurements, annotated_image
