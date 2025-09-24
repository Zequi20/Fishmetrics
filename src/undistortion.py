import cv2
import numpy as np
import json
import os
from pathlib import Path

class CameraUndistortion:
    """
    Clase para manejar la corrección de distorsión de imágenes.
    """
    
    def __init__(self):
        self.camera_matrix = None
        self.dist_coeffs = None
        self.optimal_camera_matrix = None
        self.roi = None
        self.map1 = None
        self.map2 = None
        self.image_size = None
        
        # Parámetros por defecto (los que proporcionaste)
        self.default_camera_matrix = np.array([
            [1193.93, 0, 800],
            [0, 1194.89, 600],
            [0, 0, 1]
        ], dtype=np.float32)
        
        # Coeficientes de distorsión por defecto (ajustables)
        self.default_dist_coeffs = np.array([0.1, -0.2, 0.0, 0.0, 0.1], dtype=np.float32)
    
    def load_calibration_from_file(self, calibration_file):
        """
        Carga los parámetros de calibración desde un archivo JSON.
        
        Args:
            calibration_file (str): Ruta al archivo de calibración
            
        Returns:
            bool: True si la carga fue exitosa, False en caso contrario
        """
        try:
            with open(calibration_file, 'r') as f:
                calib_data = json.load(f)
            
            self.camera_matrix = np.array(calib_data['camera_matrix'], dtype=np.float32)
            self.dist_coeffs = np.array(calib_data['dist_coeffs'], dtype=np.float32)
            
            print(f"Calibración cargada desde: {calibration_file}")
            print(f"Matriz de cámara: \n{self.camera_matrix}")
            print(f"Coeficientes de distorsión: {self.dist_coeffs}")
            
            return True
            
        except Exception as e:
            print(f"Error al cargar calibración: {e}")
            return False
    
    def set_default_calibration(self):
        """
        Establece los parámetros de calibración por defecto.
        """
        self.camera_matrix = self.default_camera_matrix.copy()
        self.dist_coeffs = self.default_dist_coeffs.copy()
        
        print("Usando calibración por defecto:")
        print(f"Matriz de cámara: \n{self.camera_matrix}")
        print(f"Coeficientes de distorsión: {self.dist_coeffs}")
    
    def set_custom_calibration(self, camera_matrix, dist_coeffs):
        """
        Establece parámetros de calibración personalizados.
        
        Args:
            camera_matrix (np.ndarray): Matriz intrínseca de la cámara (3x3)
            dist_coeffs (np.ndarray): Coeficientes de distorsión [k1, k2, p1, p2, k3]
        """
        self.camera_matrix = np.array(camera_matrix, dtype=np.float32)
        self.dist_coeffs = np.array(dist_coeffs, dtype=np.float32)
        
        print("Calibración personalizada establecida:")
        print(f"Matriz de cámara: \n{self.camera_matrix}")
        print(f"Coeficientes de distorsión: {self.dist_coeffs}")
    
    def prepare_undistortion_maps(self, image_shape, alpha=1.0):
        """
        Prepara los mapas de corrección de distorsión para una imagen.
        
        Args:
            image_shape (tuple): Forma de la imagen (height, width)
            alpha (float): Factor de escalado (0.0 = solo área válida, 1.0 = toda la imagen)
        """
        if self.camera_matrix is None or self.dist_coeffs is None:
            raise ValueError("Los parámetros de calibración no están establecidos")
        
        h, w = image_shape[:2]
        self.image_size = (w, h)
        
        # Calcular la matriz de cámara óptima
        self.optimal_camera_matrix, self.roi = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix, self.dist_coeffs, (w, h), alpha, (w, h)
        )
        
        # Generar mapas de corrección
        self.map1, self.map2 = cv2.initUndistortRectifyMap(
            self.camera_matrix, self.dist_coeffs, None, 
            self.optimal_camera_matrix, (w, h), cv2.CV_16SC2
        )
        
        print(f"Mapas de corrección preparados para imagen {w}x{h}")
        print(f"ROI (región de interés): {self.roi}")
    
    def undistort_image(self, image, alpha=1.0, crop_roi=False):
        """
        Corrige la distorsión de una imagen.
        
        Args:
            image (np.ndarray): Imagen a corregir
            alpha (float): Factor de escalado para la matriz óptima
            crop_roi (bool): Si recortar la imagen a la región de interés
            
        Returns:
            np.ndarray: Imagen corregida
        """
        if self.camera_matrix is None or self.dist_coeffs is None:
            raise ValueError("Los parámetros de calibración no están establecidos")
        
        # Preparar mapas si no existen o si cambió el tamaño de imagen
        if (self.map1 is None or self.map2 is None or 
            self.image_size != (image.shape[1], image.shape[0])):
            self.prepare_undistortion_maps(image.shape, alpha)
        
        # Aplicar corrección usando los mapas
        undistorted = cv2.remap(image, self.map1, self.map2, cv2.INTER_LINEAR)
        
        # Opcionalmente recortar a la región de interés
        if crop_roi and self.roi != (0, 0, 0, 0):
            x, y, w, h = self.roi
            undistorted = undistorted[y:y+h, x:x+w]
        
        return undistorted
    
    def undistort_image_simple(self, image, alpha=1.0):
        """
        Método simplificado para corregir distorsión sin usar mapas pre-calculados.
        Útil para imágenes individuales.
        
        Args:
            image (np.ndarray): Imagen a corregir
            alpha (float): Factor de escalado
            
        Returns:
            tuple: (imagen_corregida, matriz_optima, roi)
        """
        if self.camera_matrix is None or self.dist_coeffs is None:
            raise ValueError("Los parámetros de calibración no están establecidos")
        
        h, w = image.shape[:2]
        
        # Calcular matriz óptima
        optimal_matrix, roi = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix, self.dist_coeffs, (w, h), alpha, (w, h)
        )
        
        # Corregir distorsión
        undistorted = cv2.undistort(image, self.camera_matrix, self.dist_coeffs, 
                                   None, optimal_matrix)
        
        return undistorted, optimal_matrix, roi
    
    def save_calibration_to_file(self, filename):
        """
        Guarda los parámetros de calibración actuales en un archivo JSON.
        
        Args:
            filename (str): Ruta del archivo donde guardar
        """
        if self.camera_matrix is None or self.dist_coeffs is None:
            raise ValueError("No hay parámetros de calibración para guardar")
        
        calib_data = {
            'camera_matrix': self.camera_matrix.tolist(),
            'dist_coeffs': self.dist_coeffs.tolist(),
            'image_size': self.image_size
        }
        
        with open(filename, 'w') as f:
            json.dump(calib_data, f, indent=2)
        
        print(f"Calibración guardada en: {filename}")
    
    def get_calibration_info(self):
        """
        Retorna información sobre la calibración actual.
        
        Returns:
            dict: Información de calibración
        """
        if self.camera_matrix is None or self.dist_coeffs is None:
            return {"status": "No calibrado"}
        
        fx = self.camera_matrix[0, 0]
        fy = self.camera_matrix[1, 1]
        cx = self.camera_matrix[0, 2]
        cy = self.camera_matrix[1, 2]
        
        k1, k2, p1, p2, k3 = self.dist_coeffs
        
        return {
            "status": "Calibrado",
            "focal_length_x": fx,
            "focal_length_y": fy,
            "principal_point": (cx, cy),
            "distortion_k1": k1,
            "distortion_k2": k2,
            "distortion_p1": p1,
            "distortion_p2": p2,
            "distortion_k3": k3,
            "image_size": self.image_size
        }

def undistort_image_file(input_path, output_path, camera_matrix=None, dist_coeffs=None, alpha=1.0):
    """
    Función utilitaria para corregir distorsión de un archivo de imagen.
    
    Args:
        input_path (str): Ruta de la imagen de entrada
        output_path (str): Ruta de la imagen corregida
        camera_matrix (np.ndarray): Matriz de cámara (opcional, usa la por defecto)
        dist_coeffs (np.ndarray): Coeficientes de distorsión (opcional)
        alpha (float): Factor de escalado
        
    Returns:
        bool: True si fue exitoso
    """
    try:
        # Crear instancia del corrector
        undistorter = CameraUndistortion()
        
        # Establecer calibración
        if camera_matrix is not None and dist_coeffs is not None:
            undistorter.set_custom_calibration(camera_matrix, dist_coeffs)
        else:
            undistorter.set_default_calibration()
        
        # Cargar imagen
        image = cv2.imread(input_path)
        if image is None:
            print(f"Error: No se pudo cargar la imagen {input_path}")
            return False
        
        # Corregir distorsión
        undistorted_image = undistorter.undistort_image(image, alpha)
        
        # Guardar imagen corregida
        cv2.imwrite(output_path, undistorted_image)
        
        print(f"Imagen corregida guardada en: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error al corregir imagen: {e}")
        return False

# Ejemplo de archivo de calibración por defecto
def create_default_calibration_file(filename="camera_calibration.json"):
    """
    Crea un archivo de calibración por defecto con los parámetros proporcionados.
    """
    default_calib = {
        "camera_matrix": [
            [1193.93, 0.0, 800.0],
            [0.0, 1194.89, 600.0],
            [0.0, 0.0, 1.0]
        ],
        "dist_coeffs": [0.1, -0.2, 0.0, 0.0, 0.1],
        "description": "Parámetros de calibración por defecto"
    }
    
    with open(filename, 'w') as f:
        json.dump(default_calib, f, indent=2)
    
    print(f"Archivo de calibración por defecto creado: {filename}")