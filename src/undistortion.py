import cv2
import numpy as np
import json


SUPPORTED_YAML_MODELS = {
    "SIMPLE_PINHOLE": 3,
    "RADIAL": 5,
}

SUPPORTED_NON_SVP_MODELS = {
    "FLATPORT": 8,
}


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
        self.map_image_size = None
        self.map_alpha = None
        self.calibration_model = None
        self.non_svp_model = None
        self.non_svp_parameters = None
        
        # Parámetros por defecto (los que proporcionaste)
        self.default_camera_matrix = np.array([
            [1193.93, 0, 800],
            [0, 1194.89, 600],
            [0, 0, 1]
        ], dtype=np.float32)
        
        # Coeficientes de distorsión por defecto (ajustables)
        self.default_dist_coeffs = np.array([0.1, -0.2, 0.0, 0.0, 0.1], dtype=np.float32)
    
    def _clear_maps(self):
        """Descarta mapas calculados con una calibración anterior."""
        self.optimal_camera_matrix = None
        self.roi = None
        self.map1 = None
        self.map2 = None
        self.map_image_size = None
        self.map_alpha = None

    @staticmethod
    def _validate_image_size(image_size):
        if not isinstance(image_size, (tuple, list)) or len(image_size) != 2:
            raise ValueError("El tamaño de imagen debe contener width y height")

        width, height = image_size
        if isinstance(width, bool) or isinstance(height, bool):
            raise ValueError("El ancho y el alto deben ser números enteros positivos")

        width = int(width)
        height = int(height)
        if width <= 0 or height <= 0:
            raise ValueError("El ancho y el alto deben ser mayores que cero")
        return width, height

    @staticmethod
    def _numeric_parameters(parameters, expected_count, label):
        if not isinstance(parameters, (tuple, list)):
            raise ValueError(f"{label} debe ser una lista de parámetros")
        if len(parameters) != expected_count:
            raise ValueError(
                f"{label} requiere {expected_count} parámetros; "
                f"se recibieron {len(parameters)}"
            )

        values = np.asarray(parameters, dtype=np.float64)
        if values.ndim != 1 or not np.all(np.isfinite(values)):
            raise ValueError(f"{label} contiene valores no numéricos o no finitos")
        return values

    def load_calibration_from_yaml(
        self,
        model,
        focal_length=None,
        principal_point=None,
        image_size=None,
        parameters=None,
        non_svp_model=None,
        non_svp_parameters=None,
    ):
        """
        Carga parámetros de calibración provenientes de un YAML de COLMAP.

        Admite SIMPLE_PINHOLE ``[f, cx, cy]`` y RADIAL
        ``[f, cx, cy, k1, k2]``. La firma anterior basada en
        ``focal_length`` y ``principal_point`` se mantiene por compatibilidad.
        
        Args:
            model (str): Modelo de cámara (SIMPLE_PINHOLE o RADIAL)
            focal_length (float): Distancia focal f (API anterior)
            principal_point (tuple): Punto principal (cx, cy; API anterior)
            image_size (tuple): Dimensiones de la imagen (width, height)
            parameters (list): Lista de parámetros en el orden del modelo
            non_svp_model (str): Modelo refractivo opcional (FLATPORT)
            non_svp_parameters (list): Parámetros refractivos opcionales
            
        Returns:
            bool: True si la carga fue exitosa, False en caso contrario
        """
        try:
            normalized_model = str(model).strip().upper()
            if normalized_model not in SUPPORTED_YAML_MODELS:
                raise ValueError(f"Modelo de cámara no soportado: {model}")

            if parameters is None:
                if focal_length is None or principal_point is None:
                    raise ValueError("Faltan los parámetros de la cámara")
                cx, cy = principal_point
                parameters = [focal_length, cx, cy]
                if normalized_model == "RADIAL":
                    raise ValueError(
                        "RADIAL requiere parameters=[f, cx, cy, k1, k2]"
                    )

            values = self._numeric_parameters(
                parameters,
                SUPPORTED_YAML_MODELS[normalized_model],
                normalized_model,
            )
            width, height = self._validate_image_size(image_size)
            focal_length, cx, cy = values[:3]
            if focal_length <= 0:
                raise ValueError("La distancia focal debe ser mayor que cero")

            camera_matrix = np.array([
                [focal_length, 0, cx],
                [0, focal_length, cy],
                [0, 0, 1]
            ], dtype=np.float64)

            dist_coeffs = np.zeros(5, dtype=np.float64)
            if normalized_model == "RADIAL":
                dist_coeffs[:2] = values[3:5]

            normalized_non_svp_model = None
            validated_non_svp_parameters = None
            candidate_non_svp_model = None
            if non_svp_model is not None:
                candidate_non_svp_model = str(non_svp_model).strip().upper()
                if candidate_non_svp_model in ("", "NONE"):
                    candidate_non_svp_model = None

            if candidate_non_svp_model is not None:
                normalized_non_svp_model = candidate_non_svp_model
                if normalized_non_svp_model not in SUPPORTED_NON_SVP_MODELS:
                    raise ValueError(
                        f"Modelo refractivo no soportado: {non_svp_model}"
                    )
                validated_non_svp_parameters = self._numeric_parameters(
                    non_svp_parameters,
                    SUPPORTED_NON_SVP_MODELS[normalized_non_svp_model],
                    normalized_non_svp_model,
                )
                normal_length = np.linalg.norm(validated_non_svp_parameters[:3])
                if not np.isclose(normal_length, 1.0, atol=1e-3):
                    raise ValueError(
                        "La normal [Nx, Ny, Nz] de FLATPORT debe ser un vector unitario"
                    )

            self.camera_matrix = camera_matrix
            self.dist_coeffs = dist_coeffs
            self.image_size = (width, height)
            self.calibration_model = normalized_model
            self.non_svp_model = normalized_non_svp_model
            self.non_svp_parameters = validated_non_svp_parameters
            self._clear_maps()

            print("Calibración cargada desde YAML")
            print(f"Modelo: {normalized_model}")
            print(f"Matriz de cámara: \n{self.camera_matrix}")
            print(f"Coeficientes de distorsión: {self.dist_coeffs}")
            print(f"Tamaño de imagen: {self.image_size}")

            return True

        except Exception as e:
            print(f"Error al procesar calibración YAML: {e}")
            return False
    
    def load_calibration_from_json(self, calibration_file):
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
            json_image_size = calib_data.get('image_size')
            self.image_size = (
                self._validate_image_size(json_image_size)
                if json_image_size is not None
                else None
            )
            self.calibration_model = calib_data.get('camera_model', 'OPENCV')
            self.non_svp_model = None
            self.non_svp_parameters = None
            self._clear_maps()
            
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
        self.image_size = None
        self.calibration_model = "OPENCV"
        self.non_svp_model = None
        self.non_svp_parameters = None
        self._clear_maps()
        
        print("Usando calibración por defecto:")
        print(f"Matriz de cámara: \n{self.camera_matrix}")
        print(f"Coeficientes de distorsión: {self.dist_coeffs}")
    
    def set_custom_calibration(self, camera_matrix, dist_coeffs, image_size=None):
        """
        Establece parámetros de calibración personalizados.
        
        Args:
            camera_matrix (np.ndarray): Matriz intrínseca de la cámara (3x3)
            dist_coeffs (np.ndarray): Coeficientes de distorsión [k1, k2, p1, p2, k3]
        """
        self.camera_matrix = np.array(camera_matrix, dtype=np.float32)
        self.dist_coeffs = np.array(dist_coeffs, dtype=np.float32)
        self.image_size = (
            self._validate_image_size(image_size)
            if image_size is not None
            else None
        )
        self.calibration_model = "OPENCV"
        self.non_svp_model = None
        self.non_svp_parameters = None
        self._clear_maps()
        
        print("Calibración personalizada establecida:")
        print(f"Matriz de cámara: \n{self.camera_matrix}")
        print(f"Coeficientes de distorsión: {self.dist_coeffs}")
    
    def _camera_matrix_for_image_size(self, image_size):
        """Escala los intrínsecos si la imagen no usa la resolución calibrada."""
        camera_matrix = self.camera_matrix.astype(np.float64, copy=True)
        if self.image_size is None or self.image_size == image_size:
            return camera_matrix

        calibration_width, calibration_height = self.image_size
        width, height = image_size
        scale_x = width / calibration_width
        scale_y = height / calibration_height
        camera_matrix[0, 0] *= scale_x
        camera_matrix[0, 2] *= scale_x
        camera_matrix[1, 1] *= scale_y
        camera_matrix[1, 2] *= scale_y
        return camera_matrix

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
        map_image_size = (w, h)
        scaled_camera_matrix = self._camera_matrix_for_image_size(map_image_size)

        # Calcular la matriz de cámara óptima
        self.optimal_camera_matrix, self.roi = cv2.getOptimalNewCameraMatrix(
            scaled_camera_matrix, self.dist_coeffs, map_image_size, alpha, map_image_size
        )

        # Generar mapas de corrección
        self.map1, self.map2 = cv2.initUndistortRectifyMap(
            scaled_camera_matrix, self.dist_coeffs, None,
            self.optimal_camera_matrix, map_image_size, cv2.CV_16SC2
        )
        self.map_image_size = map_image_size
        self.map_alpha = float(alpha)
        
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
        requested_image_size = (image.shape[1], image.shape[0])
        if (self.map1 is None or self.map2 is None or
            self.map_image_size != requested_image_size or
            self.map_alpha != float(alpha)):
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
        image_size = (w, h)
        scaled_camera_matrix = self._camera_matrix_for_image_size(image_size)

        # Calcular matriz óptima
        optimal_matrix, roi = cv2.getOptimalNewCameraMatrix(
            scaled_camera_matrix, self.dist_coeffs, image_size, alpha, image_size
        )

        # Corregir distorsión
        undistorted = cv2.undistort(image, scaled_camera_matrix, self.dist_coeffs,
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
        
        coefficients = np.zeros(5, dtype=np.float64)
        source_coefficients = np.asarray(self.dist_coeffs).reshape(-1)
        coefficients[:min(5, source_coefficients.size)] = source_coefficients[:5]
        k1, k2, p1, p2, k3 = coefficients

        return {
            "status": "Calibrado",
            "camera_model": self.calibration_model or "DESCONOCIDO",
            "focal_length_x": fx,
            "focal_length_y": fy,
            "principal_point": (cx, cy),
            "distortion_k1": k1,
            "distortion_k2": k2,
            "distortion_p1": p1,
            "distortion_p2": p2,
            "distortion_k3": k3,
            "image_size": self.image_size,
            "non_svp_model": self.non_svp_model,
            "non_svp_parameters": (
                self.non_svp_parameters.copy()
                if self.non_svp_parameters is not None
                else None
            ),
            "non_svp_correction_applied": False,
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
