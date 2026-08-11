class ScaleHelper:
    def __init__(self, gui):
        self.gui = gui
    
    def calculate_scale(self):
        """Calcular la relación píxel a centímetro"""
        try:
            pixels = float(self.gui.pixels_entry.get())
            cm = float(self.gui.cm_entry.get())
            
            if pixels <= 0 or cm <= 0:
                self.gui.show_error(
                    "No se pudo aplicar la escala",
                    "La cantidad de píxeles y la medida en centímetros deben ser mayores que cero. Corrige ambos valores e inténtalo nuevamente.",
                    details=f"Valores recibidos: píxeles={pixels!r}, centímetros={cm!r}",
                )
                self.gui.set_status("Los valores de escala deben ser positivos", kind="danger", toast=True)
                return
            
            cm_per_pixel = cm / pixels
            self.gui.pixel_to_cm_ratio.set(cm_per_pixel)
            
            self.gui.scale_info_label.config(text=f"Escala manual: {cm_per_pixel:.4f} cm/píxel")
            self.gui.aruco_status_label.config(text="Escala manual activa")
            
            if self.gui.measurements:
                self.gui.morphology_helper.refresh_visualizations()
                self.gui.results_helper.display_results()
                
            self.gui.set_status(f"Escala manual aplicada: {pixels} píxeles = {cm} cm", kind="success", toast=True)
            self.gui._sync_flow_state()
            
        except ValueError as error:
            self.gui.show_error(
                "No se pudo aplicar la escala",
                "Usa solamente números en los campos de píxeles y centímetros. Por ejemplo: 250 y 10.",
                details=f"Error de conversión: {error}\nPíxeles: {self.gui.pixels_entry.get()!r}\nCentímetros: {self.gui.cm_entry.get()!r}",
            )
            self.gui.set_status("Valores de escala inválidos", kind="danger", toast=True)
