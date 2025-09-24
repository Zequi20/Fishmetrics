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
                return
            
            cm_per_pixel = cm / pixels
            self.gui.pixel_to_cm_ratio.set(cm_per_pixel)
            
            self.gui.scale_info_label.config(text=f"Escala manual: {cm_per_pixel:.4f} cm/píxel")
            self.gui.aruco_status_label.config(text="Escala manual activa")
            
            if self.gui.measurements:
                self.gui.results_helper.display_results()
                
            self.gui.status_label.config(text=f"Escala manual aplicada: {pixels} píxeles = {cm} cm")
            
        except ValueError:
            messagebox.showerror("Error", "Por favor ingrese valores numéricos válidos")