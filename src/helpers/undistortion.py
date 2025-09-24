import os
from tkinter import filedialog, messagebox

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
        
        self.gui.status_label.config(text=f"Corrección de distorsión {'habilitada' if enabled else 'deshabilitada'}")
    
    def load_calibration(self):
        """Carga parámetros de calibración desde un archivo."""
        file_types = [
            ("Archivos JSON", "*.json"),
            ("Todos los archivos", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Cargar archivo de calibración",
            filetypes=file_types
        )
        
        if filename:
            success = self.gui.undistorter.load_calibration_from_file(filename)
            if success:
                self.gui.status_label.config(text=f"Calibración cargada desde {os.path.basename(filename)}")
                messagebox.showinfo("Éxito", "Calibración cargada correctamente")
            else:
                messagebox.showerror("Error", "No se pudo cargar el archivo de calibración")
    
    def show_calibration_info(self):
        """Muestra información sobre la calibración actual."""
        info = self.gui.undistorter.get_calibration_info()
        
        if info["status"] == "No calibrado":
            messagebox.showwarning("Calibración", "No hay parámetros de calibración cargados")
            return
        
        info_text = f"""Información de Calibración:

Distancia focal X: {info['focal_length_x']:.2f}
Distancia focal Y: {info['focal_length_y']:.2f}
Punto principal: ({info['principal_point'][0]:.1f}, {info['principal_point'][1]:.1f})

Coeficientes de distorsión:
k1: {info['distortion_k1']:.4f}
k2: {info['distortion_k2']:.4f}
p1: {info['distortion_p1']:.4f}
p2: {info['distortion_p2']:.4f}
k3: {info['distortion_k3']:.4f}

Tamaño de imagen: {info.get('image_size', 'No definido')}"""
        
        messagebox.showinfo("Información de Calibración", info_text)
    
    def show_undistortion_preview(self):
        """Muestra una vista previa de la corrección de distorsión."""
        if not self.gui.current_image_path:
            messagebox.showwarning("Advertencia", "Primero selecciona una imagen")
            return
        
        try:
            import cv2
            self.gui.status_label.config(text="Generando vista previa de corrección...")
            self.gui.root.update()
            
            # Cargar imagen original
            original = cv2.imread(self.gui.current_image_path)
            if original is None:
                messagebox.showerror("Error", "No se pudo cargar la imagen")
                return
            
            # Aplicar corrección
            alpha = self.gui.undistortion_alpha.get()
            undistorted = self.gui.undistorter.undistort_image(original, alpha)
            
            # Crear imagen combinada para comparación
            h, w = original.shape[:2]
            
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
            
            self.gui.status_label.config(text="Vista previa de corrección mostrada")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar vista previa: {str(e)}")
            self.gui.status_label.config(text="Error en vista previa")