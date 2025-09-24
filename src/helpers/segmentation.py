import threading
from utils import run_segmentation, check_segmentation_requirements

class SegmentationHelper:
    def __init__(self, gui):
        self.gui = gui
        self.requirements = check_segmentation_requirements()
    
    @staticmethod
    def check_segmentation_requirements():
        """Verificar si los requisitos de segmentación están listos"""
        return check_segmentation_requirements()
    
    def run_segmentation_async(self):
        """Ejecuta la segmentación en un hilo separado."""
        if not self.gui.current_image_path:
            from tkinter import messagebox
            messagebox.showwarning("Advertencia", "Primero selecciona una imagen")
            return
        
        self.gui.segment_button.config(state="disabled")
        correction_text = " (con corrección)" if self.gui.undistortion_enabled.get() else ""
        self.gui.seg_progress_var.set(f"Ejecutando segmentación{correction_text}...")
        self.gui.seg_progress_bar.start()
        
        thread = threading.Thread(target=self.run_segmentation_thread)
        thread.daemon = True
        thread.start()

    def run_segmentation_thread(self):
        """Ejecuta la segmentación en hilo separado."""
        try:
            device = self.gui.device_var.get()
            # Usar imagen procesada (con corrección si está habilitada)
            image_path = self.gui.get_processed_image_path()
            result = run_segmentation(image_path, device=device)
            self.gui.root.after(0, self.segmentation_completed, result)
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            self.gui.root.after(0, self.segmentation_completed, error_result)

    def segmentation_completed(self, result):
        """Callback cuando la segmentación se completa."""
        self.gui.seg_progress_bar.stop()
        if self.requirements["all_ready"]:
            self.gui.segment_button.config(state="normal")
        
        if result["success"]:
            self.gui.segmentation_results = result["files"]
            correction_text = " (con corrección)" if self.gui.undistortion_enabled.get() else ""
            self.gui.seg_progress_var.set(f"Segmentación completada{correction_text}")
            
            self.gui.view_mask_button.config(state="normal")
            self.gui.view_overlay_button.config(state="normal")
            self.gui.view_ids_button.config(state="normal")
            
            self.show_segmentation_result("mask_color")
            self.gui.status_label.config(text="Segmentación exitosa")
        else:
            from tkinter import messagebox
            self.gui.seg_progress_var.set("Error en segmentación")
            self.gui.status_label.config(text=f"Error: {result.get('error', 'Error desconocido')}")
            messagebox.showerror("Error de Segmentación", result.get("message", "Error desconocido"))
    
    def show_segmentation_result(self, result_type):
        """Muestra un resultado específico de la segmentación."""
        if not self.gui.segmentation_results:
            from tkinter import messagebox
            messagebox.showwarning("Advertencia", "Primero ejecuta la segmentación")
            return
        
        file_path = self.gui.segmentation_results.get(result_type)
        if file_path and file_path.exists():
            self.gui.display_image(str(file_path))
            self.gui.status_label.config(text=f"Mostrando: {result_type}")
        else:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Archivo no encontrado: {result_type}")

    def run_segmentation_and_analyze_async(self):
        """Ejecuta segmentación y luego análisis automáticamente"""
        if not self.gui.current_image_path:
            return
        
        self.gui.segment_button.config(state="disabled")
        self.gui.analyze_button.config(state="disabled")
        correction_text = " (con corrección)" if self.gui.undistortion_enabled.get() else ""
        self.gui.seg_progress_var.set(f"Ejecutando segmentación{correction_text}...")
        self.gui.seg_progress_bar.start()
        
        thread = threading.Thread(target=self.run_segmentation_and_analyze_thread)
        thread.daemon = True
        thread.start()

    def run_segmentation_and_analyze_thread(self):
        """Ejecuta segmentación y análisis en hilo separado"""
        try:
            device = self.gui.device_var.get()
            # Usar imagen procesada
            image_path = self.gui.get_processed_image_path()
            result = run_segmentation(image_path, device=device)
            self.gui.root.after(0, self.segmentation_completed_with_analysis, result)
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            self.gui.root.after(0, self.segmentation_completed, error_result)

    def segmentation_completed_with_analysis(self, result):
        """Callback cuando segmentación se completa, seguido de análisis automático"""
        self.segmentation_completed(result)
        
        if result["success"]:
            self.gui.root.after(1000, self.gui.analyze_image)

    def check_segmentation_status(self):
        """Verifica y actualiza el estado de la segmentación."""
        if not self.requirements["all_ready"]:
            missing = []
            if not self.requirements["script_exists"]:
                missing.append("script de segmentación")
            if not self.requirements["checkpoint_exists"]:
                missing.append("modelo checkpoint")
            
            self.gui.segment_button.config(state="disabled")
            self.gui.seg_progress_var.set(f"No disponible - Faltan: {', '.join(missing)}")
        else:
            self.gui.seg_progress_var.set("Listo para segmentar")