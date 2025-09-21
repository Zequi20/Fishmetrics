import cv2
import os
import sys
import subprocess
import numpy as np
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

def detect_aruco_marker(image_path, marker_size_mm=100):
    """
    Detecta marcadores ArUco 4x4 en la imagen y calcula la escala.
    Versión mejorada con mejor configuración de parámetros.
    """
    try:
        # Cargar la imagen
        image = cv2.imread(image_path)
        if image is None:
            return {"detected": False, "error": "No se pudo cargar la imagen"}
        
        # Convertir a escala de grises
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Crear detector ArUco para 4x4_100 con parámetros optimizados
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)
        parameters = cv2.aruco.DetectorParameters()
        
        # Ajustar parámetros para mejorar detección
        parameters.adaptiveThreshWinSizeMin = 3
        parameters.adaptiveThreshWinSizeMax = 23
        parameters.adaptiveThreshWinSizeStep = 10
        parameters.adaptiveThreshConstant = 7
        
        # Parámetros de contorno
        parameters.minMarkerPerimeterRate = 0.03
        parameters.maxMarkerPerimeterRate = 4.0
        parameters.polygonalApproxAccuracyRate = 0.03
        
        # Parámetros de esquinas
        parameters.minCornerDistanceRate = 0.01
        parameters.minDistanceToBorder = 3
        
        # Parámetros de bits
        parameters.markerBorderBits = 1
        parameters.minOtsuStdDev = 5.0
        
        # Refinamiento de esquinas
        parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        parameters.cornerRefinementWinSize = 5
        parameters.cornerRefinementMaxIterations = 30
        parameters.cornerRefinementMinAccuracy = 0.1
        
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
            
            # Calcular el tamaño del marcador en píxeles
            corner1 = marker_corners[0]
            corner2 = marker_corners[1] 
            corner3 = marker_corners[2]
            corner4 = marker_corners[3]
            
            # Calcular las dimensiones del marcador
            width1 = np.linalg.norm(corner2 - corner1)
            width2 = np.linalg.norm(corner3 - corner4)
            height1 = np.linalg.norm(corner4 - corner1)
            height2 = np.linalg.norm(corner3 - corner2)
            
            # Promedio de las medidas para mayor precisión
            avg_width = (width1 + width2) / 2
            avg_height = (height1 + height2) / 2
            marker_size_pixels = (avg_width + avg_height) / 2
            
            # Calcular la escala: cm por píxel
            marker_size_cm = marker_size_mm / 10  # Convertir mm a cm
            cm_per_pixel = marker_size_cm / marker_size_pixels
            
            # Información adicional
            marker_id = ids[0][0]
            center = np.mean(marker_corners, axis=0)
            
            print(f"Marcador ID: {marker_id}")
            print(f"Tamaño en píxeles: {marker_size_pixels:.2f}")
            print(f"Escala calculada: {cm_per_pixel:.4f} cm/pixel")
            
            return {
                "detected": True,
                "marker_id": int(marker_id),
                "marker_size_pixels": float(marker_size_pixels),
                "marker_size_mm": marker_size_mm,
                "marker_size_cm": marker_size_cm,
                "cm_per_pixel": float(cm_per_pixel),
                "center": center.tolist(),
                "corners": marker_corners.tolist(),
                "pixels_per_cm": float(marker_size_pixels / marker_size_cm)
            }
        else:
            # Intentar con diferentes diccionarios ArUco
            dictionaries_to_try = [
                cv2.aruco.DICT_4X4_50,
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
                        "message": f"Se detectó un marcador pero con diccionario {dict_type}, no 4X4_100. Revisa el tipo de marcador."
                    }
            
            return {
                "detected": False,
                "message": "No se detectaron marcadores ArUco en la imagen. Verifica que:\n" +
                          "1. El marcador sea visible y esté bien iluminado\n" +
                          "2. El marcador no esté distorsionado\n" +
                          "3. El contraste sea suficiente\n" +
                          "4. El marcador sea del tipo 4X4_100"
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
