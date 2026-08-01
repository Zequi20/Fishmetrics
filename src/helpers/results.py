import os
from tkinter import messagebox, filedialog

class ResultsHelper:
    def __init__(self, gui):
        self.gui = gui
    
    def display_results(self):
        """Mostrar los resultados en el treeview"""
        for item in self.gui.results_tree.get_children():
            self.gui.results_tree.delete(item)
        
        if self.gui.measurements:
            cm_per_pixel = self.gui.pixel_to_cm_ratio.get()
            
            for index, (measurement, value_px) in enumerate(self.gui.measurements.items()):
                value_cm = value_px * cm_per_pixel
                self.gui.results_tree.insert("", "end", values=(
                    measurement, 
                    f"{value_px:.1f} px", 
                    f"{value_cm:.2f} cm"
                ), tags=("even" if index % 2 == 0 else "odd",))
        self.gui._sync_flow_state()
    
    def clear_results(self):
        """Limpiar los resultados mostrados"""
        self.clear_measurements(sync=False)
        self.gui.segmentation_results = None
        self.gui.aruco_detection = None

        # Deshabilitar solo botones de visualización
        self.gui.view_mask_button.config(state="disabled")
        self.gui.view_overlay_button.config(state="disabled")
        self.gui.view_ids_button.config(state="disabled")
        self.gui.show_aruco_button.config(state="disabled")

        # Manejar botón de vista previa de corrección
        if self.gui.undistortion_enabled.get() and self.gui.current_image_path:
            self.gui.view_undist_button.config(state="normal")
        else:
            self.gui.view_undist_button.config(state="disabled")

        # NO deshabilitar detect_aruco_button si hay una imagen cargada
        if not self.gui.current_image_path:
            self.gui.detect_aruco_button.config(state="disabled")

        self.gui.aruco_status_label.config(text="No detectado")
        self.gui._sync_flow_state()

    def clear_measurements(self, sync=True):
        """Elimina solo la morfometría y conserva imagen, escala y segmentación."""
        for item in self.gui.results_tree.get_children():
            self.gui.results_tree.delete(item)
        self.gui.save_button.config(state="disabled")
        self.gui.measurements = None
        self.gui.annotated_image = None
        if sync:
            self.gui._sync_flow_state()
    
    def save_results(self):
        """Guardar los resultados en un archivo de texto"""
        if not self.gui.measurements:
            messagebox.showwarning("Advertencia", "No hay resultados para guardar")
            self.gui.set_status("No hay resultados para guardar", kind="warning", toast=True)
            return
        
        filename = filedialog.asksaveasfilename(
            title="Guardar resultados",
            defaultextension=".txt",
            filetypes=[("Archivo de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        
        if filename:
            try:
                self._write_results_to_file(filename)
                messagebox.showinfo("Éxito", f"Resultados guardados en: {filename}")
                self.gui.set_status("Resultados guardados exitosamente", kind="success", toast=True)
                
            except Exception as e:
                self.gui.show_error(
                    "No se pudieron guardar los resultados",
                    "FishMetrics no pudo crear el archivo. Verifica que la carpeta exista, que tengas permiso para escribir en ella y vuelve a intentarlo.",
                    details=f"Destino: {filename}\n{type(e).__name__}: {e}",
                )
                self.gui.set_status("No se pudieron guardar los resultados", kind="danger", toast=True)
    
    def _write_results_to_file(self, filename):
        """Escribe los resultados al archivo especificado"""
        cm_per_pixel = self.gui.pixel_to_cm_ratio.get()
        pixels_ref = float(self.gui.pixels_entry.get())
        cm_ref = float(self.gui.cm_entry.get())
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Resultados del Análisis Morfológico de Peces\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Archivo analizado: {os.path.basename(self.gui.current_image_path)}\n")
            f.write(f"Ruta completa: {self.gui.current_image_path}\n")
            
            # Información sobre corrección de distorsión
            if self.gui.undistortion_enabled.get():
                f.write(f"Corrección de distorsión: APLICADA (alpha={self.gui.undistortion_alpha.get():.2f})\n")
                calib_info = self.gui.undistorter.get_calibration_info()
                f.write(f"Distancia focal: fx={calib_info['focal_length_x']:.2f}, fy={calib_info['focal_length_y']:.2f}\n")
            else:
                f.write("Corrección de distorsión: NO APLICADA\n")
            f.write("\n")
            
            f.write("Configuración de Escala:\n")
            f.write("-" * 25 + "\n")
            
            if self.gui.aruco_detection and self.gui.aruco_detection["detected"]:
                f.write("Método de escala: Detección automática ArUco\n")
                f.write(f"Marcador detectado: ID {self.gui.aruco_detection['marker_id']}\n")
                f.write(
                    f"Lado real indicado: {self.gui.aruco_detection['marker_size_input']:g} "
                    f"{self.gui.aruco_detection['marker_size_unit']}\n"
                )
                f.write(f"Lado normalizado: {self.gui.aruco_detection['marker_size_mm']:g} mm\n")
                f.write(f"Lado detectado en la imagen: {self.gui.aruco_detection['marker_size_pixels']:.1f} px\n")
                f.write(f"Factor de conversión: {cm_per_pixel:.4f} cm/píxel\n\n")
            else:
                f.write("Método de escala: Configuración manual\n")
                f.write(f"Relación de conversión: {pixels_ref} píxeles = {cm_ref} cm\n")
                f.write(f"Factor de conversión: {cm_per_pixel:.4f} cm/píxel\n\n")
            
            f.write("Mediciones:\n")
            f.write("-" * 15 + "\n")
            f.write(f"{'Medición':<20} {'Píxeles':<15} {'Centímetros':<15}\n")
            f.write("-" * 50 + "\n")
            
            for measurement, value_px in self.gui.measurements.items():
                value_cm = value_px * cm_per_pixel
                f.write(f"{measurement:<20} {value_px:>8.1f} px    {value_cm:>8.2f} cm\n")
