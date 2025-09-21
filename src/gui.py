import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import threading
from morphology import measure_morphology
from utils import run_segmentation, check_segmentation_requirements, detect_aruco_marker, draw_aruco_detection

class FishMorphologyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Análisis Morfológico de Peces")
        self.root.geometry("1400x900")
        
        # Variables
        self.current_image_path = None
        self.measurements = None
        self.annotated_image = None
        self.pixel_to_cm_ratio = tk.DoubleVar(value=1.0)
        self.segmentation_results = None
        self.aruco_detection = None
        
        # Verificar requisitos de segmentación
        self.seg_requirements = check_segmentation_requirements()
        
        # Crear la interfaz
        self.create_widgets()
        
    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar el grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Título
        title_label = ttk.Label(main_frame, text="Análisis Morfológico de Peces", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 1. BOTONES PRINCIPALES
        button_frame = ttk.LabelFrame(main_frame, text="Controles Principales", padding="10")
        button_frame.grid(row=1, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        
        self.select_button = ttk.Button(button_frame, text="Seleccionar Imagen", 
                                       command=self.select_image)
        self.select_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.analyze_button = ttk.Button(button_frame, text="Analizar Morfología", 
                                        command=self.analyze_image, state="disabled")
        self.analyze_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.save_button = ttk.Button(button_frame, text="Guardar Resultados", 
                                     command=self.save_results, state="disabled")
        self.save_button.pack(side=tk.LEFT)
        
        # 2. SEGMENTACIÓN
        seg_frame = ttk.LabelFrame(main_frame, text="Segmentación", padding="10")
        seg_frame.grid(row=2, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        
        seg_controls_frame = ttk.Frame(seg_frame)
        seg_controls_frame.pack(fill=tk.X)
        
        ttk.Label(seg_controls_frame, text="Dispositivo:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.device_var = tk.StringVar(value="cpu")
        device_combo = ttk.Combobox(seg_controls_frame, textvariable=self.device_var, 
                                   values=["cpu", "cuda"], state="readonly", width=8)
        device_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        self.segment_button = ttk.Button(seg_controls_frame, text="Generar Segmentación", 
                                        command=self.run_segmentation_async)
        self.segment_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.seg_progress_var = tk.StringVar(value="Listo")
        self.seg_status_label = ttk.Label(seg_frame, textvariable=self.seg_progress_var, 
                                         font=("Arial", 9))
        self.seg_status_label.pack(pady=(5, 0))
        
        self.seg_progress_bar = ttk.Progressbar(seg_frame, mode='indeterminate')
        self.seg_progress_bar.pack(fill=tk.X, pady=(2, 5))
        
        seg_results_frame = ttk.Frame(seg_frame)
        seg_results_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.view_mask_button = ttk.Button(seg_results_frame, text="Ver Máscara", 
                                          command=lambda: self.show_segmentation_result("mask_color"),
                                          state="disabled")
        self.view_mask_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.view_overlay_button = ttk.Button(seg_results_frame, text="Ver Overlay", 
                                             command=lambda: self.show_segmentation_result("overlay"),
                                             state="disabled")
        self.view_overlay_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.view_ids_button = ttk.Button(seg_results_frame, text="Ver IDs", 
                                         command=lambda: self.show_segmentation_result("mask_vis"),
                                         state="disabled")
        self.view_ids_button.pack(side=tk.LEFT)
        
        # 3. CONFIGURACIÓN DE ESCALA CON ARUCO
        scale_frame = ttk.LabelFrame(main_frame, text="Configuración de Escala", padding="10")
        scale_frame.grid(row=3, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        scale_frame.columnconfigure(3, weight=1)
        
        # Detección ArUco
        aruco_frame = ttk.Frame(scale_frame)
        aruco_frame.grid(row=0, column=0, columnspan=6, pady=(0, 10), sticky=(tk.W, tk.E))
        
        ttk.Label(aruco_frame, text="ArUco 4x4 (100mm):").pack(side=tk.LEFT, padx=(0, 5))
        
        self.detect_aruco_button = ttk.Button(aruco_frame, text="Detectar ArUco", 
                                             command=self.detect_aruco_scale, state="disabled")
        self.detect_aruco_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.show_aruco_button = ttk.Button(aruco_frame, text="Ver Detección", 
                                           command=self.show_aruco_detection, state="disabled")
        self.show_aruco_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.aruco_status_label = ttk.Label(aruco_frame, text="No detectado", 
                                           font=("Arial", 9, "italic"))
        self.aruco_status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Separador
        ttk.Separator(scale_frame, orient='horizontal').grid(row=1, column=0, columnspan=6, 
                                                            sticky=(tk.W, tk.E), pady=5)
        
        # Campos para la conversión píxel-cm manual
        ttk.Label(scale_frame, text="Relación manual:").grid(row=2, column=0, padx=(0, 5))
        
        self.pixels_entry = ttk.Entry(scale_frame, width=10)
        self.pixels_entry.grid(row=2, column=1, padx=(0, 5))
        self.pixels_entry.insert(0, "100")
        
        ttk.Label(scale_frame, text="píxeles =").grid(row=2, column=2, padx=(0, 5))
        
        self.cm_entry = ttk.Entry(scale_frame, width=10)
        self.cm_entry.grid(row=2, column=3, padx=(0, 5))
        self.cm_entry.insert(0, "1.0")
        
        ttk.Label(scale_frame, text="cm").grid(row=2, column=4, padx=(0, 10))
        
        self.calculate_scale_button = ttk.Button(scale_frame, text="Aplicar Escala Manual", 
                                               command=self.calculate_scale)
        self.calculate_scale_button.grid(row=2, column=5, padx=(0, 10))
        
        self.scale_info_label = ttk.Label(scale_frame, text="Escala actual: 1.0 cm/píxel", 
                                         font=("Arial", 9, "italic"))
        self.scale_info_label.grid(row=3, column=0, columnspan=6, pady=(5, 0), sticky=(tk.W))
        
        # 4. CONTENIDO PRINCIPAL
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        content_frame.columnconfigure(0, weight=2)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Frame para la imagen
        image_frame = ttk.LabelFrame(content_frame, text="Imagen", padding="5")
        image_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(0, weight=1)
        
        self.image_canvas = tk.Canvas(image_frame, bg="white", width=700, height=500)
        self.image_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        h_scrollbar = ttk.Scrollbar(image_frame, orient="horizontal", command=self.image_canvas.xview)
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        v_scrollbar = ttk.Scrollbar(image_frame, orient="vertical", command=self.image_canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.image_canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        # Frame para los resultados
        results_frame = ttk.LabelFrame(content_frame, text="Resultados", padding="5")
        results_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(1, weight=1)
        
        self.file_info = ttk.Label(results_frame, text="Ningún archivo seleccionado", 
                                  font=("Arial", 10))
        self.file_info.grid(row=0, column=0, pady=(0, 10), sticky=(tk.W, tk.E))
        
        columns = ("Medición", "Píxeles", "Centímetros")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=10)
        
        self.results_tree.heading("Medición", text="Medición")
        self.results_tree.heading("Píxeles", text="Píxeles")
        self.results_tree.heading("Centímetros", text="Centímetros")
        self.results_tree.column("Medición", width=120)
        self.results_tree.column("Píxeles", width=80)
        self.results_tree.column("Centímetros", width=100)
        
        self.results_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        tree_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        tree_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.results_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # 5. BARRA DE ESTADO
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=5, column=0, columnspan=3, pady=(10, 0), sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(status_frame, text="Listo para seleccionar imagen")
        self.status_label.grid(row=0, column=0, sticky=(tk.W))
        
        # Verificar estado inicial
        self.check_segmentation_status()
    
    def detect_aruco_scale(self):
        """Detecta marcadores ArUco y actualiza la escala automáticamente."""
        if not self.current_image_path:
            messagebox.showwarning("Advertencia", "Primero selecciona una imagen")
            return
        
        try:
            self.status_label.config(text="Detectando marcador ArUco...")
            self.root.update()
            
            # Detectar ArUco
            self.aruco_detection = detect_aruco_marker(self.current_image_path, marker_size_mm=100)
            
            if self.aruco_detection["detected"]:
                # Actualizar la escala automáticamente
                cm_per_pixel = self.aruco_detection["cm_per_pixel"]
                pixels_per_cm = self.aruco_detection["pixels_per_cm"]
                
                self.pixel_to_cm_ratio.set(cm_per_pixel)
                
                # Actualizar campos de entrada
                self.pixels_entry.delete(0, tk.END)
                self.pixels_entry.insert(0, f"{pixels_per_cm:.1f}")
                self.cm_entry.delete(0, tk.END)
                self.cm_entry.insert(0, "10.0")
                
                # Actualizar etiquetas
                marker_id = self.aruco_detection["marker_id"]
                self.aruco_status_label.config(text=f"Detectado ID: {marker_id}")
                self.scale_info_label.config(text=f"Escala ArUco: {cm_per_pixel:.4f} cm/píxel")
                
                # Habilitar botón para ver detección
                self.show_aruco_button.config(state="normal")
                
                # Actualizar resultados si ya hay mediciones
                if self.measurements:
                    self.display_results()
                
                self.status_label.config(text=f"ArUco detectado - Escala automática aplicada")
                messagebox.showinfo("Éxito", f"Marcador ArUco detectado (ID: {marker_id})\n"
                                             f"Escala aplicada automáticamente: {cm_per_pixel:.4f} cm/píxel")
                
            else:
                self.aruco_status_label.config(text="No detectado")
                self.status_label.config(text="No se detectó marcador ArUco")
                error_msg = self.aruco_detection.get("error", "No se encontraron marcadores ArUco 4x4 en la imagen")
                messagebox.showinfo("No detectado", f"No se detectó marcador ArUco.\n{error_msg}\n\nPuedes usar la escala manual.")
                
        except Exception as e:
            self.aruco_status_label.config(text="Error en detección")
            self.status_label.config(text="Error al detectar ArUco")
            messagebox.showerror("Error", f"Error al detectar ArUco: {str(e)}")
    
    def show_aruco_detection(self):
        """Muestra la imagen con la detección de ArUco resaltada."""
        if not self.aruco_detection or not self.aruco_detection["detected"]:
            messagebox.showwarning("Advertencia", "Primero detecta un marcador ArUco")
            return
        
        try:
            output_path = "aruco_detection.png"
            img_with_aruco = draw_aruco_detection(self.current_image_path, self.aruco_detection, output_path)
            
            if img_with_aruco is not None:
                self.display_image(output_path)
                self.status_label.config(text="Mostrando detección de ArUco")
            else:
                messagebox.showerror("Error", "No se pudo generar la imagen con detección")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al mostrar detección ArUco: {str(e)}")
    
    def check_segmentation_status(self):
        """Verifica y actualiza el estado de la segmentación."""
        if not self.seg_requirements["all_ready"]:
            missing = []
            if not self.seg_requirements["script_exists"]:
                missing.append("script de segmentación")
            if not self.seg_requirements["checkpoint_exists"]:
                missing.append("modelo checkpoint")
            
            self.segment_button.config(state="disabled")
            self.seg_progress_var.set(f"No disponible - Faltan: {', '.join(missing)}")
        else:
            self.seg_progress_var.set("Listo para segmentar")

    def run_segmentation_async(self):
        """Ejecuta la segmentación en un hilo separado."""
        if not self.current_image_path:
            messagebox.showwarning("Advertencia", "Primero selecciona una imagen")
            return
        
        self.segment_button.config(state="disabled")
        self.seg_progress_var.set("Ejecutando segmentación...")
        self.seg_progress_bar.start()
        
        thread = threading.Thread(target=self.run_segmentation_thread)
        thread.daemon = True
        thread.start()

    def run_segmentation_thread(self):
        """Ejecuta la segmentación en hilo separado."""
        try:
            device = self.device_var.get()
            result = run_segmentation(self.current_image_path, device=device)
            self.root.after(0, self.segmentation_completed, result)
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            self.root.after(0, self.segmentation_completed, error_result)
    
    def segmentation_completed(self, result):
        """Callback cuando la segmentación se completa."""
        self.seg_progress_bar.stop()
        if self.seg_requirements["all_ready"]:
            self.segment_button.config(state="normal")
        
        if result["success"]:
            self.segmentation_results = result["files"]
            self.seg_progress_var.set("Segmentación completada")
            
            self.view_mask_button.config(state="normal")
            self.view_overlay_button.config(state="normal")
            self.view_ids_button.config(state="normal")
            
            self.show_segmentation_result("mask_color")
            self.status_label.config(text="Segmentación exitosa")
        else:
            self.seg_progress_var.set("Error en segmentación")
            self.status_label.config(text=f"Error: {result.get('error', 'Error desconocido')}")
            messagebox.showerror("Error de Segmentación", result.get("message", "Error desconocido"))
    
    def show_segmentation_result(self, result_type):
        """Muestra un resultado específico de la segmentación."""
        if not self.segmentation_results:
            messagebox.showwarning("Advertencia", "Primero ejecuta la segmentación")
            return
        
        file_path = self.segmentation_results.get(result_type)
        if file_path and file_path.exists():
            self.display_image(str(file_path))
            self.status_label.config(text=f"Mostrando: {result_type}")
        else:
            messagebox.showerror("Error", f"Archivo no encontrado: {result_type}")

    def calculate_scale(self):
        """Calcular la relación píxel a centímetro"""
        try:
            pixels = float(self.pixels_entry.get())
            cm = float(self.cm_entry.get())
            
            if pixels <= 0 or cm <= 0:
                messagebox.showerror("Error", "Los valores deben ser positivos")
                return
            
            cm_per_pixel = cm / pixels
            self.pixel_to_cm_ratio.set(cm_per_pixel)
            
            self.scale_info_label.config(text=f"Escala manual: {cm_per_pixel:.4f} cm/píxel")
            self.aruco_status_label.config(text="Escala manual activa")
            
            if self.measurements:
                self.display_results()
                
            self.status_label.config(text=f"Escala manual aplicada: {pixels} píxeles = {cm} cm")
            
        except ValueError:
            messagebox.showerror("Error", "Por favor ingrese valores numéricos válidos")
    
    def select_image(self):
        """Seleccionar una imagen para analizar"""
        file_types = [
            ("Imágenes", "*.png *.jpg *.jpeg *.bmp *.tiff"),
            ("PNG", "*.png"),
            ("JPEG", "*.jpg *.jpeg"),
            ("Todos los archivos", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Seleccionar imagen de pez",
            filetypes=file_types,
            initialdir=os.path.dirname(os.path.abspath(__file__))
        )
        
        if filename:
            self.current_image_path = filename
            self.file_info.config(text=f"Archivo: {os.path.basename(filename)}")
            self.status_label.config(text="Imagen seleccionada. Puede detectar ArUco, generar segmentación o analizar directamente.")
            
            # Habilitar botones
            self.analyze_button.config(state="normal")
            self.detect_aruco_button.config(state="normal")
            
            if self.seg_requirements["all_ready"]:
                self.segment_button.config(state="normal")
            
            self.display_image(filename)
            self.clear_results()
    
    def display_image(self, image_path):
        """Mostrar una imagen en el canvas"""
        try:
            pil_image = Image.open(image_path)
            
            canvas_width = 700
            canvas_height = 500
            
            img_width, img_height = pil_image.size
            
            scale_w = canvas_width / img_width
            scale_h = canvas_height / img_height
            scale = min(scale_w, scale_h, 1.5)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            self.photo = ImageTk.PhotoImage(pil_image)
            
            self.image_canvas.delete("all")
            self.image_canvas.create_image(canvas_width//2, canvas_height//2, 
                                         anchor=tk.CENTER, image=self.photo)
            
            self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all"))
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la imagen: {str(e)}")
    
    def analyze_image(self):
        """Analizar la imagen seleccionada"""
        if not self.current_image_path:
            messagebox.showwarning("Advertencia", "Por favor seleccione una imagen primero")
            return
        
        if not self.segmentation_results:
            response = messagebox.askyesno(
                "Segmentación requerida", 
                "Para el análisis morfológico se necesita primero generar la segmentación.\n¿Desea ejecutarla automáticamente?"
            )
            if response:
                self.run_segmentation_and_analyze()
            return
        
        mask_path = self.segmentation_results.get("mask_color")
        if not mask_path or not mask_path.exists():
            messagebox.showerror("Error", "No se encontró la máscara de segmentación")
            return
        
        try:
            self.status_label.config(text="Analizando morfología...")
            self.root.update()
            
            self.measurements, self.annotated_image = measure_morphology(
                str(mask_path), show_visualization=False
            )
            
            if self.measurements:
                self.display_results()
                
                annotated_path = "mediciones_pez.png"
                if os.path.exists(annotated_path):
                    self.display_image(annotated_path)
                
                self.status_label.config(text="Análisis morfológico completado")
                self.save_button.config(state="normal")
            else:
                messagebox.showerror("Error", "No se pudieron obtener mediciones de la imagen")
                self.status_label.config(text="Error en el análisis")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error durante el análisis: {str(e)}")
            self.status_label.config(text="Error en el análisis")

    def run_segmentation_and_analyze(self):
        """Ejecuta segmentación y luego análisis automáticamente"""
        if not self.current_image_path:
            return
        
        self.segment_button.config(state="disabled")
        self.analyze_button.config(state="disabled")
        self.seg_progress_var.set("Ejecutando segmentación...")
        self.seg_progress_bar.start()
        
        thread = threading.Thread(target=self.run_segmentation_and_analyze_thread)
        thread.daemon = True
        thread.start()

    def run_segmentation_and_analyze_thread(self):
        """Ejecuta segmentación y análisis en hilo separado"""
        try:
            device = self.device_var.get()
            result = run_segmentation(self.current_image_path, device=device)
            self.root.after(0, self.segmentation_completed_with_analysis, result)
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            self.root.after(0, self.segmentation_completed, error_result)

    def segmentation_completed_with_analysis(self, result):
        """Callback cuando segmentación se completa, seguido de análisis automático"""
        self.segmentation_completed(result)
        
        if result["success"]:
            self.root.after(1000, self.analyze_image)
    
    def display_results(self):
        """Mostrar los resultados en el treeview"""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        if self.measurements:
            cm_per_pixel = self.pixel_to_cm_ratio.get()
            
            for measurement, value_px in self.measurements.items():
                value_cm = value_px * cm_per_pixel
                self.results_tree.insert("", "end", values=(
                    measurement, 
                    f"{value_px:.1f} px", 
                    f"{value_cm:.2f} cm"
                ))
    
    def clear_results(self):
        """Limpiar los resultados mostrados"""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.save_button.config(state="disabled")
        self.measurements = None
        self.annotated_image = None
        self.segmentation_results = None
        self.aruco_detection = None
        
        # Deshabilitar solo botones de visualización, NO el botón de detectar ArUco
        self.view_mask_button.config(state="disabled")
        self.view_overlay_button.config(state="disabled")
        self.view_ids_button.config(state="disabled")
        self.show_aruco_button.config(state="disabled")
        
        # NO deshabilitar detect_aruco_button aquí si hay una imagen cargada
        if not self.current_image_path:
            self.detect_aruco_button.config(state="disabled")
        
        self.aruco_status_label.config(text="No detectado")
    
    def save_results(self):
        """Guardar los resultados en un archivo de texto"""
        if not self.measurements:
            messagebox.showwarning("Advertencia", "No hay resultados para guardar")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Guardar resultados",
            defaultextension=".txt",
            filetypes=[("Archivo de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        
        if filename:
            try:
                cm_per_pixel = self.pixel_to_cm_ratio.get()
                pixels_ref = float(self.pixels_entry.get())
                cm_ref = float(self.cm_entry.get())
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("Resultados del Análisis Morfológico de Peces\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"Archivo analizado: {os.path.basename(self.current_image_path)}\n")
                    f.write(f"Ruta completa: {self.current_image_path}\n\n")
                    
                    f.write("Configuración de Escala:\n")
                    f.write("-" * 25 + "\n")
                    
                    if self.aruco_detection and self.aruco_detection["detected"]:
                        f.write("Método de escala: Detección automática ArUco\n")
                        f.write(f"Marcador detectado: ID {self.aruco_detection['marker_id']}\n")
                        f.write(f"Tamaño del marcador: {self.aruco_detection['marker_size_mm']} mm\n")
                        f.write(f"Tamaño en píxeles: {self.aruco_detection['marker_size_pixels']:.1f} px\n")
                        f.write(f"Factor de conversión: {cm_per_pixel:.4f} cm/píxel\n\n")
                    else:
                        f.write("Método de escala: Configuración manual\n")
                        f.write(f"Relación de conversión: {pixels_ref} píxeles = {cm_ref} cm\n")
                        f.write(f"Factor de conversión: {cm_per_pixel:.4f} cm/píxel\n\n")
                    
                    f.write("Mediciones:\n")
                    f.write("-" * 15 + "\n")
                    f.write(f"{'Medición':<20} {'Píxeles':<15} {'Centímetros':<15}\n")
                    f.write("-" * 50 + "\n")
                    
                    for measurement, value_px in self.measurements.items():
                        value_cm = value_px * cm_per_pixel
                        f.write(f"{measurement:<20} {value_px:>8.1f} px    {value_cm:>8.2f} cm\n")
                
                messagebox.showinfo("Éxito", f"Resultados guardados en: {filename}")
                self.status_label.config(text="Resultados guardados exitosamente")
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudieron guardar los resultados: {str(e)}")