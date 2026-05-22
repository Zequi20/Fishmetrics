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
            messagebox.showerror("Error", "No se encontró la máscara de segmentación")
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
                messagebox.showerror("Error", "No se pudieron obtener mediciones de la imagen")
                self.gui.set_status("Error en el análisis", kind="danger", toast=True)
                self.gui._sync_flow_state()
                
        except Exception as e:
            messagebox.showerror("Error", f"Error durante el análisis: {str(e)}")
            self.gui.set_status("Error en el análisis", kind="danger", toast=True)
            self.gui._sync_flow_state()
        finally:
            self.gui.set_busy(False)
