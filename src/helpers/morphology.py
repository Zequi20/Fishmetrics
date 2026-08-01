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
        
        is_reanalysis = bool(self.gui.measurements)

        try:
            self.gui.analysis_running = True
            self.gui._sync_flow_state()
            correction_text = " (con corrección)" if self.gui.undistortion_enabled.get() else ""
            action_text = "Reanalizando morfometría" if is_reanalysis else "Analizando morfometría"
            self.gui.set_status(f"{action_text}{correction_text}...", kind="active", busy=True)
            self.gui._set_step_state("analysis", "active", "Midiendo")
            self.gui.root.update()
            
            new_measurements, new_annotated_image = measure_morphology(
                str(mask_path), show_visualization=False
            )
            
            if new_measurements:
                self.gui.measurements = new_measurements
                self.gui.annotated_image = new_annotated_image
                self.gui.results_helper.display_results()
                
                annotated_path = "mediciones_pez.png"
                if os.path.exists(annotated_path):
                    self.gui.display_image(annotated_path)
                
                completed_text = "Morfometría recalculada" if is_reanalysis else "Análisis morfológico completado"
                self.gui.set_status(completed_text, kind="success", toast=True)
                self.gui.save_button.config(state="normal")
                self.gui._sync_flow_state()
            else:
                user_message = (
                    "La nueva medición no produjo resultados válidos. Revisa la máscara de segmentación e inténtalo nuevamente; las mediciones anteriores se conservaron."
                    if is_reanalysis
                    else "La imagen se procesó, pero no fue posible reconocer una silueta de pez medible. Revisa la máscara de segmentación e intenta con una imagen más clara."
                )
                self.gui.show_error(
                    "No se encontraron medidas válidas",
                    user_message,
                    details=f"El análisis no devolvió mediciones. Máscara utilizada: {mask_path}",
                )
                failure_text = (
                    "No se pudo recalcular; se conservaron las mediciones anteriores"
                    if is_reanalysis
                    else "Error en el análisis"
                )
                self.gui.set_status(failure_text, kind="danger", toast=True)
                self.gui._sync_flow_state()
                
        except Exception as e:
            user_message = (
                "Ocurrió un problema mientras se recalculaban las medidas. Las mediciones anteriores se conservaron y puedes volver a intentarlo."
                if is_reanalysis
                else "Ocurrió un problema mientras se calculaban las medidas. Comprueba la segmentación e inténtalo nuevamente."
            )
            self.gui.show_error(
                "No se pudo completar la medición",
                user_message,
                details=f"{type(e).__name__}: {e}\nMáscara utilizada: {mask_path}",
            )
            failure_text = (
                "No se pudo recalcular; se conservaron las mediciones anteriores"
                if is_reanalysis
                else "Error en el análisis"
            )
            self.gui.set_status(failure_text, kind="danger", toast=True)
            self.gui._sync_flow_state()
        finally:
            self.gui.analysis_running = False
            self.gui.set_busy(False)
            self.gui._sync_flow_state()
