import os
from pathlib import Path
from tkinter import messagebox, filedialog

import yaml


MEASUREMENT_DISPLAY_UNITS = ("m", "cm", "mm", "píxeles")


def convert_measurement(value_px, cm_per_pixel, unit):
    """Convierte una medida almacenada en píxeles a la unidad solicitada."""
    value_px = float(value_px)
    value_cm = value_px * float(cm_per_pixel)
    conversions = {
        "m": value_cm / 100,
        "cm": value_cm,
        "mm": value_cm * 10,
        "píxeles": value_px,
    }
    if unit not in conversions:
        raise ValueError(f"Unidad de medida no compatible: {unit!r}")
    return conversions[unit]


def format_measurement(value_px, cm_per_pixel, unit):
    """Formatea una medida para mostrarla en la tabla."""
    value = convert_measurement(value_px, cm_per_pixel, unit)
    precision = {"m": 4, "cm": 2, "mm": 2, "píxeles": 1}[unit]
    suffix = "px" if unit == "píxeles" else unit
    return f"{value:.{precision}f} {suffix}"


def measurement_values_for_export(value_px, cm_per_pixel):
    """Devuelve las cuatro unidades como números YAML interoperables."""
    return {
        "m": round(convert_measurement(value_px, cm_per_pixel, "m"), 6),
        "cm": round(convert_measurement(value_px, cm_per_pixel, "cm"), 4),
        "mm": round(convert_measurement(value_px, cm_per_pixel, "mm"), 3),
        "pixeles": round(convert_measurement(value_px, cm_per_pixel, "píxeles"), 2),
    }


class ResultsHelper:
    def __init__(self, gui):
        self.gui = gui
    
    def display_results(self):
        """Mostrar los resultados en el treeview"""
        for item in self.gui.results_tree.get_children():
            self.gui.results_tree.delete(item)
        
        if self.gui.measurements:
            cm_per_pixel = self.gui.pixel_to_cm_ratio.get()
            unit = self.gui.measurement_unit_var.get()
            self.gui.results_tree.heading("Valor", text=f"Valor ({unit})")
            
            for index, (measurement, value_px) in enumerate(self.gui.measurements.items()):
                self.gui.results_tree.insert("", "end", values=(
                    measurement,
                    format_measurement(value_px, cm_per_pixel, unit),
                ), tags=("even" if index % 2 == 0 else "odd",))
        else:
            unit = self.gui.measurement_unit_var.get()
            self.gui.results_tree.heading("Valor", text=f"Valor ({unit})")
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
        self.gui.annotated_overlay_image = None
        self.gui.measurement_view_paths = {}
        if hasattr(self.gui, "view_measurements_mask_button"):
            self.gui.view_measurements_mask_button.config(state="disabled")
        if hasattr(self.gui, "view_measurements_overlay_button"):
            self.gui.view_measurements_overlay_button.config(state="disabled")
        if sync:
            self.gui._sync_flow_state()
    
    def save_results(self):
        """Guardar los resultados en un archivo YAML."""
        if not self.gui.measurements:
            messagebox.showwarning("Advertencia", "No hay resultados para guardar")
            self.gui.set_status("No hay resultados para guardar", kind="warning", toast=True)
            return
        
        filename = filedialog.asksaveasfilename(
            title="Exportar resultados en YAML",
            defaultextension=".yaml",
            filetypes=[
                ("Archivo YAML", "*.yaml"),
                ("Archivo YML", "*.yml"),
                ("Todos los archivos", "*.*"),
            ],
        )
        
        if filename:
            try:
                self._write_results_to_yaml(filename)
                messagebox.showinfo("Éxito", f"Resultados guardados en: {filename}")
                self.gui.set_status("Resultados YAML exportados exitosamente", kind="success", toast=True)
                
            except Exception as e:
                self.gui.show_error(
                    "No se pudieron guardar los resultados",
                    "FishMetrics no pudo crear el archivo. Verifica que la carpeta exista, que tengas permiso para escribir en ella y vuelve a intentarlo.",
                    details=f"Destino: {filename}\n{type(e).__name__}: {e}",
                )
                self.gui.set_status("No se pudieron guardar los resultados", kind="danger", toast=True)
    
    def _write_results_to_yaml(self, filename):
        """Escribe metadatos y mediciones en las cuatro unidades solicitadas."""
        cm_per_pixel = self.gui.pixel_to_cm_ratio.get()
        export_data = {
            "fishmetrics": {
                "formato_version": 1,
                "archivo": {
                    "nombre": os.path.basename(self.gui.current_image_path),
                    "ruta": str(self.gui.current_image_path),
                },
                "correccion_distorsion": self._distortion_export_data(),
                "escala": self._scale_export_data(cm_per_pixel),
                "mediciones": [
                    {
                        "nombre": measurement,
                        "valores": measurement_values_for_export(value_px, cm_per_pixel),
                    }
                    for measurement, value_px in self.gui.measurements.items()
                ],
            }
        }

        output_path = Path(filename)
        with output_path.open("w", encoding="utf-8") as output_file:
            yaml.safe_dump(
                export_data,
                output_file,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )

    def _distortion_export_data(self):
        enabled = bool(self.gui.undistortion_enabled.get())
        data = {"aplicada": enabled}
        if enabled:
            calibration = self.gui.undistorter.get_calibration_info()
            data.update({
                "alpha": float(self.gui.undistortion_alpha.get()),
                "distancia_focal_px": {
                    "fx": float(calibration["focal_length_x"]),
                    "fy": float(calibration["focal_length_y"]),
                },
            })
        return data

    def _scale_export_data(self, cm_per_pixel):
        data = {"cm_por_pixel": float(cm_per_pixel)}
        detection = self.gui.aruco_detection
        if detection and detection.get("detected"):
            data.update({
                "metodo": "aruco",
                "marcador_id": int(detection["marker_id"]),
                "lado_real": {
                    "valor": float(detection["marker_size_input"]),
                    "unidad": detection["marker_size_unit"],
                },
                "lado_mm": float(detection["marker_size_mm"]),
                "lado_pixeles": float(detection["marker_size_pixels"]),
            })
        else:
            data.update({
                "metodo": "manual",
                "referencia": {
                    "pixeles": float(self.gui.pixels_entry.get()),
                    "cm": float(self.gui.cm_entry.get()),
                },
            })
        return data

    def _write_results_to_file(self, filename):
        """Alias compatible: el formato de exportación actual es YAML."""
        self._write_results_to_yaml(filename)
