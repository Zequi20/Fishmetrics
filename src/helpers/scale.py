import tkinter as tk
from tkinter import messagebox

class ScaleHelper:
    def __init__(self, gui):
        self.gui = gui
    
    def calculate_scale(self):
        """Calcular la relación píxel a centímetro"""
        try:
            pixels = float(self.gui.pixels_entry.get())
            cm = float(self.gui.cm_entry.get())
            
            if pixels <= 0 or cm <= 0:
                messagebox.showerror("Error", "Los valores deben ser positivos")
                self.gui.set_status("Los valores de escala deben ser positivos", kind="danger", toast=True)
                return
            
            cm_per_pixel = cm / pixels
            self.gui.pixel_to_cm_ratio.set(cm_per_pixel)
            
            self.gui.scale_info_label.config(text=f"Escala manual: {cm_per_pixel:.4f} cm/píxel")
            self.gui.aruco_status_label.config(text="Escala manual activa")
            
            if self.gui.measurements:
                self.gui.results_helper.display_results()
                
            self.gui.set_status(f"Escala manual aplicada: {pixels} píxeles = {cm} cm", kind="success", toast=True)
            self.gui._sync_flow_state()
            
        except ValueError:
            messagebox.showerror("Error", "Por favor ingrese valores numéricos válidos")
            self.gui.set_status("Valores de escala inválidos", kind="danger", toast=True)
