import cv2
import os
import sys
import subprocess
import numpy as np
import json
from pathlib import Path

def draw_text_with_outline(img, text, position, font, font_scale,
                           text_color, outline_color,
                           thickness=2, outline_thickness=4):
    """
    Dibuja texto con un contorno para mejor legibilidad.
    """
    x, y = position
    cv2.putText(img, text, (x, y), font, font_scale,
                outline_color, outline_thickness, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), font, font_scale,
                text_color, thickness, cv2.LINE_AA)

def create_default_calibration_file(filename="camera_calibration.json"):
    """
    Crea un archivo de calibración por defecto.
    """
    default_calib = {
        "camera_matrix": [
            [1193.93, 0.0, 800.0],
            [0.0, 1194.89, 600.0],
            [0.0, 0.0, 1.0]
        ],
        "dist_coeffs": [0.1, -0.2, 0.0, 0.0, 0.1],
        "description": "Parámetros de calibración por defecto - Ajustar según la cámara específica",
        "notes": [
            "camera_matrix: Matriz intrínseca 3x3 [fx, 0, cx; 0, fy, cy; 0, 0, 1]",
            "dist_coeffs: Coeficientes de distorsión [k1, k2, p1, p2, k3]",
            "fx, fy: Distancias focales en píxeles",
            "cx, cy: Coordenadas del punto principal",
            "k1, k2, k3: Coeficientes de distorsión radial",
            "p1, p2: Coeficientes de distorsión tangencial"
        ]
    }
    
    with open(filename, 'w') as f:
        json.dump(default_calib, f, indent=2)
    
    print(f"Archivo de calibración por defecto creado: {filename}")
    return filename

def detect_aruco_marker(image_path, marker_size_mm=25):
    print(f"MMarker size mm: {marker_size_mm}")
    """
    Detecta marcadores ArUco 4x4_50 en la imagen y calcula la escala.
    Versión corregida para cálculo preciso de escala.
    """
    try:
        # Cargar la imagen
        image = cv2.imread(image_path)
        if image is None:
            return {"detected": False, "error": "No se pudo cargar la imagen"}
        
        # Convertir a escala de grises
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Crear detector ArUco para 4x4_50 con parámetros optimizados
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        parameters = cv2.aruco.DetectorParameters()
        
        # Parámetros optimizados para marcadores pequeños (25mm)
        parameters.adaptiveThreshWinSizeMin = 3
        parameters.adaptiveThreshWinSizeMax = 23
        parameters.adaptiveThreshWinSizeStep = 10
        parameters.adaptiveThreshConstant = 7
        
        # Parámetros de contorno más restrictivos para marcadores pequeños
        parameters.minMarkerPerimeterRate = 0.02  # Más restrictivo
        parameters.maxMarkerPerimeterRate = 4.0
        parameters.polygonalApproxAccuracyRate = 0.05  # Más preciso
        
        # Parámetros de esquinas
        parameters.minCornerDistanceRate = 0.01
        parameters.minDistanceToBorder = 3
        
        # Parámetros de bits
        parameters.markerBorderBits = 1
        parameters.minOtsuStdDev = 5.0
        
        # Refinamiento de esquinas más agresivo
        parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        parameters.cornerRefinementWinSize = 3  # Ventana más pequeña para marcadores pequeños
        parameters.cornerRefinementMaxIterations = 50  # Más iteraciones
        parameters.cornerRefinementMinAccuracy = 0.05  # Mayor precisión
        
        # Crear detector
        detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
        
        # Detectar marcadores
        corners, ids, rejected = detector.detectMarkers(gray)
        
        # Debug: mostrar información sobre la detección
        print(f"Imagen cargada: {image.shape}")
        print(f"Marcadores detectados: {len(ids) if ids is not None else 0}")
        print(f"Marcadores rechazados: {len(rejected)}")
        
        if ids is not None and len(ids) > 0:
            # Tomar el primer marcador detectado
            marker_corners = corners[0][0]
            
            # Calcular las distancias entre esquinas adyacentes
            side1 = np.linalg.norm(marker_corners[1] - marker_corners[0])  # Lado superior
            side2 = np.linalg.norm(marker_corners[2] - marker_corners[1])  # Lado derecho
            side3 = np.linalg.norm(marker_corners[3] - marker_corners[2])  # Lado inferior
            side4 = np.linalg.norm(marker_corners[0] - marker_corners[3])  # Lado izquierdo
            
            # Promedio de todos los lados para mayor precisión
            marker_size_pixels = (side1 + side2 + side3 + side4) / 4
            
            # Calcular la escala: mm por píxel (más directo)
            mm_per_pixel = marker_size_mm / marker_size_pixels
            cm_per_pixel = mm_per_pixel / 10  # Convertir a cm por píxel
            pixels_per_mm = marker_size_pixels / marker_size_mm
            pixels_per_cm = pixels_per_mm * 10
            
            # Información adicional
            marker_id = ids[0][0]
            center = np.mean(marker_corners, axis=0)
            
            # Calcular área y perímetro para verificación
            area_pixels = cv2.contourArea(marker_corners)
            perimeter_pixels = cv2.arcLength(marker_corners, True)
            
            print(f"Marcador ID: {marker_id}")
            print(f"Lados en píxeles: {side1:.2f}, {side2:.2f}, {side3:.2f}, {side4:.2f}")
            print(f"Tamaño promedio en píxeles: {marker_size_pixels:.2f}")
            print(f"Escala calculada: {mm_per_pixel:.4f} mm/pixel")
            print(f"Resolución: {pixels_per_mm:.2f} pixels/mm = {pixels_per_cm:.2f} pixels/cm")
            
            return {
                "detected": True,
                "marker_id": int(marker_id),
                "marker_size_pixels": float(marker_size_pixels),
                "marker_size_mm": marker_size_mm,
                "marker_size_cm": marker_size_mm / 10,
                "mm_per_pixel": float(mm_per_pixel),
                "cm_per_pixel": float(cm_per_pixel),
                "pixels_per_mm": float(pixels_per_mm),
                "pixels_per_cm": float(pixels_per_cm),
                "center": center.tolist(),
                "corners": marker_corners.tolist(),
                "area_pixels": float(area_pixels),
                "perimeter_pixels": float(perimeter_pixels),
                "sides_pixels": [float(side1), float(side2), float(side3), float(side4)]
            }
        else:
            # Intentar con diferentes diccionarios ArUco
            dictionaries_to_try = [
                cv2.aruco.DICT_4X4_100,
                cv2.aruco.DICT_4X4_250,
                cv2.aruco.DICT_4X4_1000,
                cv2.aruco.DICT_5X5_100,
                cv2.aruco.DICT_6X6_100
            ]
            
            for dict_type in dictionaries_to_try:
                try_dict = cv2.aruco.getPredefinedDictionary(dict_type)
                try_detector = cv2.aruco.ArucoDetector(try_dict, parameters)
                try_corners, try_ids, _ = try_detector.detectMarkers(gray)
                
                if try_ids is not None and len(try_ids) > 0:
                    print(f"Marcador detectado con diccionario: {dict_type}")
                    return {
                        "detected": False,
                        "message": f"Se detectó un marcador pero con diccionario {dict_type}, no 4X4_50. Revisa el tipo de marcador."
                    }
            
            return {
                "detected": False,
                "message": "No se detectaron marcadores ArUco en la imagen. Verifica que:\n" +
                          "1. El marcador sea visible y esté bien iluminado\n" +
                          "2. El marcador no esté distorsionado\n" +
                          "3. El contraste sea suficiente\n" +
                          "4. El marcador sea del tipo 4X4_50\n" +
                          "5. El marcador tenga al menos 20-30 píxeles de ancho"
            }
            
    except Exception as e:
        print(f"Error en detección ArUco: {str(e)}")
        return {
            "detected": False,
            "error": f"Error al detectar ArUco: {str(e)}"
        }

def draw_aruco_detection(image_path, detection_result, output_path=None):
    """
    Dibuja la detección del marcador ArUco en la imagen.
    
    Args:
        image_path (str): Ruta de la imagen original
        detection_result (dict): Resultado de detect_aruco_marker
        output_path (str): Ruta para guardar la imagen con detección (opcional)
    
    Returns:
        numpy.ndarray: Imagen con la detección dibujada
    """
    try:
        image = cv2.imread(image_path)
        if image is None or not detection_result["detected"]:
            return image
        
        # Convertir corners de vuelta a numpy array
        corners = np.array([detection_result["corners"]], dtype=np.float32)
        
        # Dibujar el marcador
        cv2.aruco.drawDetectedMarkers(image, corners)
        
        # Dibujar información adicional
        center = tuple(map(int, detection_result["center"]))
        marker_id = detection_result["marker_id"]
        scale = detection_result["cm_per_pixel"]
        
        # Texto con información
        text = f"ID: {marker_id}"
        text2 = f"Escala: {scale:.4f} cm/px"
        
        # Posición del texto
        text_x = center[0] + 50
        text_y = center[1] - 30
        
        # Dibujar textos con contorno
        draw_text_with_outline(image, text, (text_x, text_y), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                              (0, 255, 0), (0, 0, 0), 2, 4)
        
        draw_text_with_outline(image, text2, (text_x, text_y + 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                              (0, 255, 0), (0, 0, 0), 2, 4)
        
        # Guardar si se especifica ruta
        if output_path:
            cv2.imwrite(output_path, image)
        
        return image
        
    except Exception as e:
        print(f"Error al dibujar detección ArUco: {e}")
        return cv2.imread(image_path) if image_path else None

def run_segmentation(input_image_path, output_dir="preds", device="cpu"):
    """
    Ejecuta el script de segmentación y retorna la ruta de la máscara generada.
    
    Args:
        input_image_path (str): Ruta de la imagen de entrada
        output_dir (str): Directorio de salida para las máscaras
        device (str): Dispositivo a usar ('cpu' o 'cuda')
    
    Returns:
        dict: Diccionario con las rutas de los archivos generados
    """
    try:
        # Rutas del proyecto
        project_root = Path(__file__).parent.parent
        seg_script = project_root / "seg" / "infer2_seg.py"
        checkpoint = project_root / "seg" / "best_miou_V5.pth"
        
        # Verificar que existen los archivos necesarios
        if not seg_script.exists():
            raise FileNotFoundError(f"Script de segmentación no encontrado: {seg_script}")
        if not checkpoint.exists():
            raise FileNotFoundError(f"Checkpoint no encontrado: {checkpoint}")
        if not Path(input_image_path).exists():
            raise FileNotFoundError(f"Imagen de entrada no encontrada: {input_image_path}")
        
        # Crear directorio de salida
        output_path = project_root / output_dir
        output_path.mkdir(exist_ok=True)
        
        # Comando para ejecutar la segmentación
        cmd = [
            sys.executable,
            str(seg_script),
            "--ckpt", str(checkpoint),
            "--input", str(input_image_path),
            "--out", str(output_path),
            "--device", device
        ]
        
        # Ejecutar el comando
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
        
        if result.returncode != 0:
            raise RuntimeError(f"Error en segmentación: {result.stderr}")
        
        # Construir rutas de archivos generados
        input_name = Path(input_image_path).stem
        generated_files = {
            "mask_color": output_path / f"{input_name}_mask.png",
            "overlay": output_path / f"{input_name}_overlay.png", 
            "mask_ids": output_path / f"{input_name}_mask_ids.png",
            "mask_vis": output_path / f"{input_name}_mask_index_vis.png"
        }
        
        # Verificar que se generaron los archivos
        missing_files = []
        for name, path in generated_files.items():
            if not path.exists():
                missing_files.append(name)
        
        if missing_files:
            print(f"[WARN] Archivos no generados: {missing_files}")
        
        return {
            "success": True,
            "files": generated_files,
            "output_dir": str(output_path),
            "message": "Segmentación completada exitosamente",
            "missing_files": missing_files
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Error en segmentación: {str(e)}"
        }

def check_segmentation_requirements():
    """
    Verifica que estén disponibles los archivos necesarios para segmentación.
    
    Returns:
        dict: Estado de los requisitos
    """
    project_root = Path(__file__).parent.parent
    seg_script = project_root / "seg" / "infer2_seg.py"
    checkpoint = project_root / "seg" / "best_miou_V5.pth"
    
    requirements = {
        "script_exists": seg_script.exists(),
        "checkpoint_exists": checkpoint.exists(),
        "script_path": str(seg_script),
        "checkpoint_path": str(checkpoint)
    }
    
    requirements["all_ready"] = all([
        requirements["script_exists"],
        requirements["checkpoint_exists"]
    ])
    
    return requirements
