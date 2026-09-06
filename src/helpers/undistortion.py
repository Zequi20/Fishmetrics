import os
from tkinter import filedialog, messagebox
import yaml


YAML_CAMERA_MODELS = {
    "SIMPLE_PINHOLE": 3,
    "RADIAL": 5,
}


class UndistortionHelper:
    def __init__(self, gui):
        self.gui = gui
    
    def update_alpha_label(self, *args):
        """Actualiza la etiqueta del valor alpha."""
        alpha_value = self.gui.undistortion_alpha.get()
        self.gui.alpha_label.config(text=f"{alpha_value:.2f}")
    
    def on_undistortion_toggle(self):
        """Callback cuando se habilita/deshabilita la corrección de distorsión."""
        enabled = self.gui.undistortion_enabled.get()
        state = "normal" if enabled else "disabled"
        
        self.gui.alpha_scale.config(state=state)
        
        if enabled and self.gui.current_image_path:
            self.gui.view_undist_button.config(state="normal")
        else:
            self.gui.view_undist_button.config(state="disabled")
        
        self.gui.set_status(
            f"Corrección de distorsión {'habilitada' if enabled else 'deshabilitada'}",
            kind="success" if enabled else "info",
            toast=True,
        )
        self.gui._sync_flow_state()
    
    def load_calibration(self):
        """Carga parámetros de calibración desde un archivo YAML."""
        file_types = [
            ("Archivos YAML", "*.yaml *.yml"),
            ("Todos los archivos", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Cargar archivo de calibración",
            filetypes=file_types
        )
        
        if filename:
            try:
                with open(filename, 'r') as file:
                    calibration_data = yaml.safe_load(file)
                
                if not isinstance(calibration_data, dict):
                    raise ValueError("El contenido raíz del YAML debe ser un objeto")

                # Extraer parámetros del YAML de COLMAP.
                raw_model = calibration_data.get('model')
                model = str(raw_model).strip().upper() if raw_model else None
                parameters = calibration_data.get('parameters', [])
                width = calibration_data.get('width')
                height = calibration_data.get('height')

                expected_parameters = YAML_CAMERA_MODELS.get(model)
                if (
                    expected_parameters is None
                    or not isinstance(parameters, list)
                    or len(parameters) != expected_parameters
                    or width is None
                    or height is None
                ):
                    self.gui.set_status("Formato de calibración no compatible", kind="danger", toast=True)
                    self.gui.show_error(
                        "Archivo de calibración no compatible",
                        "El archivo no contiene una calibración que FishMetrics pueda usar. Selecciona un YAML SIMPLE_PINHOLE [f, cx, cy] o RADIAL [f, cx, cy, k1, k2], con ancho y alto.",
                        details=(
                            f"Archivo: {filename}\nModelo recibido: {raw_model!r}\n"
                            f"Cantidad de parámetros: {len(parameters) if isinstance(parameters, list) else 'formato no válido'}"
                        ),
                    )
                    return

                success = self.gui.undistorter.load_calibration_from_yaml(
                    model=model,
                    parameters=parameters,
                    image_size=(width, height),
                    non_svp_model=calibration_data.get('non_svp_model'),
                    non_svp_parameters=calibration_data.get('non_svp_parameters'),
                )

                if success:
                    refractive_model = calibration_data.get('non_svp_model')
                    if str(refractive_model).strip().upper() in ('', 'NONE'):
                        refractive_model = None
                    status_suffix = f" + {refractive_model}" if refractive_model else ""
                    self.gui.set_status(
                        f"Calibración {model}{status_suffix} cargada desde {os.path.basename(filename)}",
                        kind="success",
                        toast=True,
                    )
                    success_message = f"Calibración {model} cargada correctamente."
                    if refractive_model:
                        success_message += (
                            f"\n\nLos parámetros {refractive_model} se conservaron como "
                            "metadatos. La corrección 2D aplica la distorsión radial; la "
                            "refracción del puerto depende también de la profundidad de la escena."
                        )
                    messagebox.showinfo("Éxito", success_message)
                else:
                    self.gui.set_status("No se pudo cargar el archivo de calibración", kind="danger", toast=True)
                    self.gui.show_error(
                        "No se pudo aplicar la calibración",
                        "El archivo parece válido, pero sus parámetros no pudieron aplicarse. Revisa que el tamaño de imagen y los valores de cámara estén completos.",
                        details=f"Archivo: {filename}\nModelo: {model}\nTamaño declarado: {width} x {height}\nParámetros: {parameters!r}",
                    )
            
            except Exception as e:
                self.gui.set_status("Error al leer el archivo YAML", kind="danger", toast=True)
                self.gui.show_error(
                    "No se pudo leer la calibración",
                    "FishMetrics no pudo interpretar el archivo seleccionado. Comprueba que sea un YAML válido y vuelve a intentarlo.",
                    details=f"Archivo: {filename}\n{type(e).__name__}: {e}",
                )
    
    def show_calibration_info(self):
        """Muestra información sobre la calibración actual."""
        info = self.gui.undistorter.get_calibration_info()
        
        if info["status"] == "No calibrado":
            messagebox.showwarning("Calibración", "No hay parámetros de calibración cargados")
            return
        
        image_size = info.get('image_size') or 'No definido'
        info_text = f"""Información de Calibración:

Modelo de cámara: {info.get('camera_model', 'DESCONOCIDO')}
Distancia focal X: {info['focal_length_x']:.2f}
Distancia focal Y: {info['focal_length_y']:.2f}
Punto principal: ({info['principal_point'][0]:.1f}, {info['principal_point'][1]:.1f})

Coeficientes de distorsión:
k1: {info['distortion_k1']:.4f}
k2: {info['distortion_k2']:.4f}
p1: {info['distortion_p1']:.4f}
p2: {info['distortion_p2']:.4f}
k3: {info['distortion_k3']:.4f}

Tamaño de imagen: {image_size}"""

        if info.get('non_svp_model'):
            info_text += (
                f"\n\nModelo refractivo: {info['non_svp_model']}"
                "\nEstado: parámetros registrados; la corrección 2D aplica "
                "solamente la componente radial."
            )
        
        messagebox.showinfo("Información de Calibración", info_text)
    
    def show_undistortion_preview(self):
        """Muestra una vista previa de la corrección de distorsión."""
        if not self.gui.current_image_path:
            messagebox.showwarning("Advertencia", "Primero selecciona una imagen")
            return
        
        try:
            import cv2
            self.gui.set_status("Generando vista previa de corrección...", kind="active", busy=True)
            self.gui.root.update()
            
            # Cargar imagen original
            original = cv2.imread(self.gui.current_image_path)
            if original is None:
                self.gui.show_error(
                    "No se pudo preparar la vista previa",
                    "La imagen original ya no puede abrirse. Comprueba que el archivo exista y no esté dañado, o selecciona otra imagen.",
                    details=f"OpenCV no pudo cargar: {self.gui.current_image_path}",
                )
                self.gui.set_status("No se pudo cargar la imagen", kind="danger", toast=True)
                return
            
            # Aplicar corrección
            alpha = self.gui.undistortion_alpha.get()
            undistorted = self.gui.undistorter.undistort_image(original, alpha)
            
            # Crear imagen combinada para comparación
            h, w = original.shape[:2]
            new_w, new_h = w, h
            
            # Redimensionar si es muy grande
            if w > 800:
                scale = 800 / w
                new_w, new_h = int(w * scale), int(h * scale)
                original = cv2.resize(original, (new_w, new_h))
                undistorted = cv2.resize(undistorted, (new_w, new_h))
            
            # Combinar imágenes lado a lado
            combined = cv2.hconcat([original, undistorted])
            
            # Añadir etiquetas
            from utils import draw_text_with_outline
            draw_text_with_outline(combined, "ORIGINAL", (10, 30), 
                                 cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), (0, 0, 0), 2, 4)
            draw_text_with_outline(combined, "CORREGIDA", (new_w + 10, 30), 
                                 cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), (0, 0, 0), 2, 4)
            
            # Guardar y mostrar
            preview_path = "undistortion_preview.png"
            cv2.imwrite(preview_path, combined)
            self.gui.display_image(preview_path)
            
            self.gui.set_status("Vista previa de corrección mostrada", kind="success", toast=True)
            
        except Exception as e:
            self.gui.show_error(
                "No se pudo generar la vista previa",
                "Ocurrió un problema al corregir la distorsión de la imagen. Revisa la calibración activa y vuelve a intentarlo.",
                details=f"{type(e).__name__}: {e}\nImagen: {self.gui.current_image_path}",
            )
            self.gui.set_status("Error en vista previa", kind="danger", toast=True)
        finally:
            self.gui.set_busy(False)
