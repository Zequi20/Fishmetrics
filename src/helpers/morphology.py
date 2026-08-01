import os
from tkinter import messagebox
from morphology import measure_morphology

class MorphologyHelper:
    def __init__(self, gui):
        self.gui = gui
    
    def analyze_image(self):
        """Analizar la imagen seleccionada"""
        if not self.gui.current_image_path:
            messagebox.showwarning("Advertencia", "Por favor seleccione una imagen primero")
            return
        
        if not self.gui.segmentation_results:
            response = messagebox.askyesno(
                "Segmentación requerida", 
                "Para el análisis morfológico se necesita primero generar la segmentación.\n¿Desea ejecutarla automáticamente?"
            )
            if response:
                self.gui.segmentation_helper.run_segmentation_and_analyze_async()
            return
        
        mask_path = self.gui.segmentation_results.get("mask_color")
        if not mask_path or not mask_path.exists():
            self.gui.show_error(
                "No se puede iniciar la medición",
                "Falta la máscara que identifica al pez. Ejecuta nuevamente la segmentación y después vuelve a analizar la imagen.",
                details=f"Ruta esperada de la máscara: {mask_path or 'no informada'}",
            )
            return
        
        try:
            correction_text = " (con corrección)" if self.gui.undistortion_enabled.get() else ""
            self.gui.set_status(f"Analizando morfología{correction_text}...", kind="active", busy=True)
            self.gui._set_step_state("analysis", "active", "Midiendo")
            self.gui.root.update()
            
            self.gui.measurements, self.gui.annotated_image = measure_morphology(
                str(mask_path), show_visualization=False
            )
            
            if self.gui.measurements:
                self.gui.results_helper.display_results()
                
                annotated_path = "mediciones_pez.png"
                if os.path.exists(annotated_path):
                    self.gui.display_image(annotated_path)
                
                self.gui.set_status("Análisis morfológico completado", kind="success", toast=True)
                self.gui.save_button.config(state="normal")
                self.gui._sync_flow_state()
            else:
                self.gui.show_error(
                    "No se encontraron medidas válidas",
                    "La imagen se procesó, pero no fue posible reconocer una silueta de pez medible. Revisa la máscara de segmentación e intenta con una imagen más clara.",
                    details=f"El análisis no devolvió mediciones. Máscara utilizada: {mask_path}",
                )
                self.gui.set_status("Error en el análisis", kind="danger", toast=True)
                self.gui._sync_flow_state()
                
        except Exception as e:
            self.gui.show_error(
                "No se pudo completar la medición",
                "Ocurrió un problema mientras se calculaban las medidas. Comprueba la segmentación e inténtalo nuevamente.",
                details=f"{type(e).__name__}: {e}\nMáscara utilizada: {mask_path}",
            )
            self.gui.set_status("Error en el análisis", kind="danger", toast=True)
            self.gui._sync_flow_state()
        finally:
            self.gui.set_busy(False)
