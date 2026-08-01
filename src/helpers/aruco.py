import math
import tkinter as tk

from utils import detect_aruco_marker, draw_aruco_detection


class ArucoHelper:
    def __init__(self, gui):
        self.gui = gui
    
    def detect_aruco_scale(self):
        """Detecta marcadores ArUco y actualiza la escala automáticamente."""
        from tkinter import messagebox
        
        if not self.gui.current_image_path:
            messagebox.showwarning("Advertencia", "Primero selecciona una imagen")
            return

        marker_size = self._get_marker_size()
        if marker_size is None:
            return

        marker_size_mm, marker_size_value, marker_size_unit = marker_size
        
        try:
            self.gui.set_status("Detectando marcador ArUco...", kind="active", busy=True)
            self.gui.root.update()
            
            # Usar imagen procesada (con corrección si está habilitada)
            image_path = self.gui.get_processed_image_path()
            
            # Detectar ArUco
            self.gui.aruco_detection = detect_aruco_marker(image_path, marker_size_mm)
            self.gui.aruco_detection["marker_size_input"] = marker_size_value
            self.gui.aruco_detection["marker_size_unit"] = marker_size_unit
            
            if self.gui.aruco_detection["detected"]:
                # Actualizar la escala automáticamente
                cm_per_pixel = self.gui.aruco_detection["cm_per_pixel"]
                marker_size_pixels = self.gui.aruco_detection["marker_size_pixels"]
                marker_size_cm = self.gui.aruco_detection["marker_size_cm"]
                
                self.gui.pixel_to_cm_ratio.set(cm_per_pixel)
                
                # Reflejar en la escala manual la misma relación física detectada.
                self.gui.pixels_entry.delete(0, tk.END)
                self.gui.pixels_entry.insert(0, f"{marker_size_pixels:.1f}")
                self.gui.cm_entry.delete(0, tk.END)
                self.gui.cm_entry.insert(0, f"{marker_size_cm:g}")
                
                # Actualizar etiquetas
                marker_id = self.gui.aruco_detection["marker_id"]
                self.gui.aruco_status_label.config(
                    text=f"Detectado ID: {marker_id} · lado {marker_size_value:g} {marker_size_unit}"
                )
                self.gui.scale_info_label.config(
                    text=f"Escala ArUco: {cm_per_pixel:.4f} cm/píxel"
                )
                
                # Habilitar botón para ver detección
                self.gui.show_aruco_button.config(state="normal")
                
                # Actualizar resultados si ya hay mediciones
                if self.gui.measurements:
                    self.gui.results_helper.display_results()
                
                correction_text = " (con corrección)" if self.gui.undistortion_enabled.get() else ""
                self.gui.set_status(f"ArUco detectado{correction_text} - Escala automática aplicada", kind="success", toast=True)
                self.gui._sync_flow_state()
                messagebox.showinfo("Éxito", f"Marcador ArUco detectado (ID: {marker_id})\n"
                                             f"Lado indicado: {marker_size_value:g} {marker_size_unit}\n"
                                             f"Escala aplicada automáticamente: {cm_per_pixel:.4f} cm/píxel")
                
            else:
                self.gui.aruco_status_label.config(text="No detectado")
                self.gui._sync_flow_state()
                technical_error = self.gui.aruco_detection.get("error")
                if technical_error:
                    self.gui.set_status("No se pudo analizar el marcador ArUco", kind="danger", toast=True)
                    self.gui.show_error(
                        "No se pudo analizar el marcador",
                        "Ocurrió un problema al procesar la imagen. Comprueba que el archivo sea válido y vuelve a intentarlo.",
                        details=technical_error,
                    )
                else:
                    self.gui.set_status("No se detectó marcador ArUco", kind="warning", toast=True)
                    messagebox.showinfo(
                        "Marcador no detectado",
                        "No encontramos un marcador ArUco compatible en la imagen. "
                        "Procura que esté completo, enfocado y bien iluminado, o continúa usando la escala manual.",
                    )
                
        except Exception as e:
            self.gui.aruco_status_label.config(text="Error en detección")
            self.gui.set_status("Error al detectar ArUco", kind="danger", toast=True)
            self.gui.show_error(
                "No se pudo buscar el marcador",
                "Ocurrió un problema al analizar la imagen. Verifica que el archivo siga disponible y vuelve a intentarlo.",
                details=f"{type(e).__name__}: {e}",
            )
        finally:
            self.gui.set_busy(False)

    def _get_marker_size(self):
        """Lee el lado físico indicado y lo normaliza a milímetros."""
        raw_value = self.gui.aruco_size_entry.get().strip()
        unit = self.gui.aruco_size_unit_var.get()

        try:
            value = float(raw_value.replace(",", "."))
            if not math.isfinite(value) or value <= 0:
                raise ValueError("el tamaño debe ser un número finito mayor que cero")
            if unit not in ("mm", "cm"):
                raise ValueError(f"unidad no compatible: {unit!r}")
        except ValueError as error:
            self.gui.show_error(
                "Indica el tamaño del marcador",
                "Antes de detectar el ArUco, escribe cuánto mide realmente uno de sus lados y selecciona la unidad. El valor debe ser mayor que cero.",
                details=f"Valor recibido: {raw_value!r}\nUnidad recibida: {unit!r}\n{error}",
            )
            self.gui.set_status("Falta una medida válida para el marcador ArUco", kind="warning", toast=True)
            self.gui.aruco_size_entry.focus_set()
            return None

        size_mm = value * 10 if unit == "cm" else value
        return size_mm, value, unit
    
    def show_aruco_detection(self):
        """Muestra la imagen con la detección de ArUco resaltada."""
        from tkinter import messagebox
        
        if not self.gui.aruco_detection or not self.gui.aruco_detection["detected"]:
            messagebox.showwarning("Advertencia", "Primero detecta un marcador ArUco")
            return
        
        try:
            # Usar imagen procesada si la corrección está habilitada
            image_path = self.gui.get_processed_image_path()
            output_path = "aruco_detection.png"
            img_with_aruco = draw_aruco_detection(image_path, self.gui.aruco_detection, output_path)
            
            if img_with_aruco is not None:
                self.gui.display_image(output_path)
                self.gui.set_status("Mostrando detección de ArUco", kind="info")
            else:
                self.gui.show_error(
                    "No se pudo mostrar el marcador",
                    "La detección existe, pero FishMetrics no pudo preparar la imagen resaltada. Puedes continuar con la escala ya calculada.",
                    details=f"La función de dibujo no produjo una imagen. Archivo de entrada: {image_path}",
                )
                self.gui.set_status("No se pudo generar la imagen con detección", kind="danger", toast=True)
                
        except Exception as e:
            self.gui.show_error(
                "No se pudo mostrar el marcador",
                "La imagen con el marcador resaltado no pudo generarse. La escala detectada no se modificó; puedes volver a intentarlo.",
                details=f"{type(e).__name__}: {e}",
            )
            self.gui.set_status("Error al mostrar detección ArUco", kind="danger", toast=True)
