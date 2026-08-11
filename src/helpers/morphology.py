import os
from tkinter import messagebox
from morphology import measure_morphology_with_overlay


MEASUREMENT_MASK_PATH = "mediciones_pez.png"
MEASUREMENT_OVERLAY_PATH = "mediciones_pez_overlay.png"

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
            
            new_measurements, new_annotated_image, new_overlay_image = measure_morphology_with_overlay(
                str(mask_path),
                original_image_path=self.gui.get_processed_image_path(),
                cm_per_pixel=self.gui.pixel_to_cm_ratio.get(),
                show_visualization=False,
                annotated_output_path=MEASUREMENT_MASK_PATH,
                overlay_output_path=MEASUREMENT_OVERLAY_PATH,
            )
            
            if new_measurements and new_annotated_image is not None:
                self.gui.measurements = new_measurements
                self.gui.annotated_image = new_annotated_image
                self.gui.annotated_overlay_image = new_overlay_image
                self.gui.measurement_view_paths = {
                    "mask": MEASUREMENT_MASK_PATH,
                    "overlay": MEASUREMENT_OVERLAY_PATH,
                }
                self.gui.results_helper.display_results()

                self._sync_measurement_view_buttons()
                if os.path.exists(MEASUREMENT_MASK_PATH):
                    self.gui.display_image(MEASUREMENT_MASK_PATH)
                
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

    def show_measurement_result(self, result_type):
        """Muestra las mediciones sobre la máscara o sobre la imagen original."""
        view_path = self.gui.measurement_view_paths.get(result_type)
        if view_path and os.path.exists(view_path):
            self.gui.display_image(view_path)
            description = "la imagen original" if result_type == "overlay" else "la máscara"
            self.gui.set_status(f"Mostrando mediciones en cm sobre {description}", kind="info")
            return

        self.gui.show_error(
            "No se pudo mostrar la vista de mediciones",
            "La imagen anotada ya no está disponible. Reanaliza la morfometría para generarla nuevamente.",
            details=f"Vista solicitada: {result_type}\nRuta esperada: {view_path or 'no informada'}",
        )

    def refresh_visualizations(self):
        """Regenera los rótulos cuando cambia la escala sin alterar el flujo."""
        if not self.gui.measurements or not self.gui.segmentation_results:
            return

        mask_path = self.gui.segmentation_results.get("mask_color")
        if not mask_path or not mask_path.exists():
            return

        current_view = None
        for result_type, view_path in self.gui.measurement_view_paths.items():
            if str(self.gui.current_display_path) == str(view_path):
                current_view = result_type
                break

        measurements, annotated_image, overlay_image = measure_morphology_with_overlay(
            str(mask_path),
            original_image_path=self.gui.get_processed_image_path(),
            cm_per_pixel=self.gui.pixel_to_cm_ratio.get(),
            show_visualization=False,
            annotated_output_path=MEASUREMENT_MASK_PATH,
            overlay_output_path=MEASUREMENT_OVERLAY_PATH,
        )
        if not measurements or annotated_image is None:
            return

        self.gui.measurements = measurements
        self.gui.annotated_image = annotated_image
        self.gui.annotated_overlay_image = overlay_image
        self.gui.measurement_view_paths = {
            "mask": MEASUREMENT_MASK_PATH,
            "overlay": MEASUREMENT_OVERLAY_PATH,
        }
        self._sync_measurement_view_buttons()
        if current_view:
            self.show_measurement_result(current_view)

    def _sync_measurement_view_buttons(self):
        mask_available = os.path.exists(self.gui.measurement_view_paths.get("mask", ""))
        overlay_available = (
            self.gui.annotated_overlay_image is not None
            and os.path.exists(self.gui.measurement_view_paths.get("overlay", ""))
        )
        self.gui.view_measurements_mask_button.config(
            state="normal" if mask_available else "disabled"
        )
        self.gui.view_measurements_overlay_button.config(
            state="normal" if overlay_available else "disabled"
        )
