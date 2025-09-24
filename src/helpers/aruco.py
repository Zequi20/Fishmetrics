from utils import detect_aruco_marker, draw_aruco_detection
import tkinter as tk

class ArucoHelper:
    def __init__(self, gui):
        self.gui = gui
    
    def detect_aruco_scale(self):
        """Detecta marcadores ArUco y actualiza la escala automáticamente."""
        from tkinter import messagebox
        
        if not self.gui.current_image_path:
            messagebox.showwarning("Advertencia", "Primero selecciona una imagen")
            return
        
        try:
            self.gui.status_label.config(text="Detectando marcador ArUco...")
            self.gui.root.update()
            
            # Usar imagen procesada (con corrección si está habilitada)
            image_path = self.gui.get_processed_image_path()
            
            # Detectar ArUco
            self.gui.aruco_detection = detect_aruco_marker(image_path)
            
            if self.gui.aruco_detection["detected"]:
                # Actualizar la escala automáticamente
                cm_per_pixel = self.gui.aruco_detection["cm_per_pixel"]
                pixels_per_cm = self.gui.aruco_detection["pixels_per_cm"]
                
                self.gui.pixel_to_cm_ratio.set(cm_per_pixel)
                
                # Actualizar campos de entrada
                self.gui.pixels_entry.delete(0, tk.END)
                self.gui.pixels_entry.insert(0, f"{pixels_per_cm:.1f}")
                self.gui.cm_entry.delete(0, tk.END)
                self.gui.cm_entry.insert(0, "10.0")
                
                # Actualizar etiquetas
                marker_id = self.gui.aruco_detection["marker_id"]
                self.gui.aruco_status_label.config(text=f"Detectado ID: {marker_id}")
                self.gui.scale_info_label.config(text=f"Escala ArUco: {cm_per_pixel:.4f} cm/píxel")
                
                # Habilitar botón para ver detección
                self.gui.show_aruco_button.config(state="normal")
                
                # Actualizar resultados si ya hay mediciones
                if self.gui.measurements:
                    self.gui.display_results()
                
                correction_text = " (con corrección)" if self.gui.undistortion_enabled.get() else ""
                self.gui.status_label.config(text=f"ArUco detectado{correction_text} - Escala automática aplicada")
                messagebox.showinfo("Éxito", f"Marcador ArUco detectado (ID: {marker_id})\n"
                                             f"Escala aplicada automáticamente: {cm_per_pixel:.4f} cm/píxel")
                
            else:
                self.gui.aruco_status_label.config(text="No detectado")
                self.gui.status_label.config(text="No se detectó marcador ArUco")
                error_msg = self.gui.aruco_detection.get("error", "No se encontraron marcadores ArUco 4x4 en la imagen")
                messagebox.showinfo("No detectado", f"No se detectó marcador ArUco.\n{error_msg}\n\nPuedes usar la escala manual.")
                
        except Exception as e:
            self.gui.aruco_status_label.config(text="Error en detección")
            self.gui.status_label.config(text="Error al detectar ArUco")
            messagebox.showerror("Error", f"Error al detectar ArUco: {str(e)}")
    
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
                self.gui.status_label.config(text="Mostrando detección de ArUco")
            else:
                messagebox.showerror("Error", "No se pudo generar la imagen con detección")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al mostrar detección ArUco: {str(e)}")