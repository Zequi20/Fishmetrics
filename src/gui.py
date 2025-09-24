import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
from undistortion import CameraUndistortion

# Importar helpers
from helpers.segmentation import SegmentationHelper
from helpers.aruco import ArucoHelper
from helpers.image_display import ImageDisplayHelper
from helpers.results import ResultsHelper
from helpers.undistortion import UndistortionHelper
from helpers.morphology import MorphologyHelper
from helpers.scale import ScaleHelper

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
        
        # Sistema de corrección de distorsión
        self.undistorter = CameraUndistortion()
        self.undistorter.set_default_calibration()
        self.undistortion_enabled = tk.BooleanVar(value=False)
        self.undistortion_alpha = tk.DoubleVar(value=1.0)
        
        # Inicializar helpers
        self.segmentation_helper = SegmentationHelper(self)
        self.aruco_helper = ArucoHelper(self)
        self.image_display_helper = ImageDisplayHelper(self)
        self.results_helper = ResultsHelper(self)
        self.undistortion_helper = UndistortionHelper(self)
        self.morphology_helper = MorphologyHelper(self)
        self.scale_helper = ScaleHelper(self)
        
        # Crear la interfaz
        self.create_widgets()
        
        # Verificar requisitos iniciales
        self.segmentation_helper.check_segmentation_status()

    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar el grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Título
        title_label = ttk.Label(main_frame, text="Análisis Morfológico de Peces", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 1. BOTONES PRINCIPALES
        self._create_main_buttons(main_frame)
        
        # 2. CORRECCIÓN DE DISTORSIÓN
        self._create_undistortion_frame(main_frame)
        
        # 3. SEGMENTACIÓN
        self._create_segmentation_frame(main_frame)
        
        # 4. CONFIGURACIÓN DE ESCALA
        self._create_scale_frame(main_frame)
        
        # 5. CONTENIDO PRINCIPAL
        self._create_content_frame(main_frame)
        
        # 6. BARRA DE ESTADO
        self._create_status_frame(main_frame)

    def _create_main_buttons(self, parent):
        """Crear frame de botones principales"""
        button_frame = ttk.LabelFrame(parent, text="Controles Principales", padding="10")
        button_frame.grid(row=1, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        
        self.select_button = ttk.Button(button_frame, text="Seleccionar Imagen", 
                                       command=self.select_image)
        self.select_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.analyze_button = ttk.Button(button_frame, text="Analizar Morfología", 
                                        command=self.morphology_helper.analyze_image, state="disabled")
        self.analyze_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.save_button = ttk.Button(button_frame, text="Guardar Resultados", 
                                     command=self.results_helper.save_results, state="disabled")
        self.save_button.pack(side=tk.LEFT)

    def _create_undistortion_frame(self, parent):
        """Crear frame de corrección de distorsión"""
        undist_frame = ttk.LabelFrame(parent, text="Corrección de Distorsión", padding="10")
        undist_frame.grid(row=2, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        
        # Checkbox para habilitar corrección
        self.undist_check = ttk.Checkbutton(undist_frame, text="Aplicar corrección de distorsión", 
                                           variable=self.undistortion_enabled,
                                           command=self.undistortion_helper.on_undistortion_toggle)
        self.undist_check.pack(side=tk.LEFT, padx=(0, 15))
        
        # Control de alpha
        ttk.Label(undist_frame, text="Alpha:").pack(side=tk.LEFT, padx=(0, 5))
        self.alpha_scale = ttk.Scale(undist_frame, from_=0.0, to=1.0, 
                                    variable=self.undistortion_alpha, orient=tk.HORIZONTAL, length=100)
        self.alpha_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.alpha_label = ttk.Label(undist_frame, text="1.0")
        self.alpha_label.pack(side=tk.LEFT, padx=(0, 15))
        
        # Actualizar label de alpha
        self.undistortion_alpha.trace('w', self.undistortion_helper.update_alpha_label)
        
        # Botones de calibración
        self.load_calib_button = ttk.Button(undist_frame, text="Cargar Calibración", 
                                           command=self.undistortion_helper.load_calibration)
        self.load_calib_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.view_undist_button = ttk.Button(undist_frame, text="Ver Corrección", 
                                            command=self.undistortion_helper.show_undistortion_preview, state="disabled")
        self.view_undist_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.calib_info_button = ttk.Button(undist_frame, text="Info Calibración", 
                                           command=self.undistortion_helper.show_calibration_info)
        self.calib_info_button.pack(side=tk.LEFT)

    def _create_segmentation_frame(self, parent):
        """Crear frame de segmentación"""
        seg_frame = ttk.LabelFrame(parent, text="Segmentación", padding="10")
        seg_frame.grid(row=3, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        
        seg_controls_frame = ttk.Frame(seg_frame)
        seg_controls_frame.pack(fill=tk.X)
        
        ttk.Label(seg_controls_frame, text="Dispositivo:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.device_var = tk.StringVar(value="cpu")
        device_combo = ttk.Combobox(seg_controls_frame, textvariable=self.device_var, 
                                   values=["cpu", "cuda"], state="readonly", width=8)
        device_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        self.segment_button = ttk.Button(seg_controls_frame, text="Generar Segmentación", 
                                        command=self.segmentation_helper.run_segmentation_async)
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
                                          command=lambda: self.segmentation_helper.show_segmentation_result("mask_color"),
                                          state="disabled")
        self.view_mask_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.view_overlay_button = ttk.Button(seg_results_frame, text="Ver Overlay", 
                                             command=lambda: self.segmentation_helper.show_segmentation_result("overlay"),
                                             state="disabled")
        self.view_overlay_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.view_ids_button = ttk.Button(seg_results_frame, text="Ver IDs", 
                                         command=lambda: self.segmentation_helper.show_segmentation_result("mask_vis"),
                                         state="disabled")
        self.view_ids_button.pack(side=tk.LEFT)

    def _create_scale_frame(self, parent):
        """Crear frame de configuración de escala"""
        scale_frame = ttk.LabelFrame(parent, text="Configuración de Escala", padding="10")
        scale_frame.grid(row=4, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        scale_frame.columnconfigure(3, weight=1)
        
        # Detección ArUco
        aruco_frame = ttk.Frame(scale_frame)
        aruco_frame.grid(row=0, column=0, columnspan=6, pady=(0, 10), sticky=(tk.W, tk.E))
        
        ttk.Label(aruco_frame, text="ArUco 4x4 (100mm):").pack(side=tk.LEFT, padx=(0, 5))
        
        self.detect_aruco_button = ttk.Button(aruco_frame, text="Detectar ArUco", 
                                             command=self.aruco_helper.detect_aruco_scale, state="disabled")
        self.detect_aruco_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.show_aruco_button = ttk.Button(aruco_frame, text="Ver Detección", 
                                           command=self.aruco_helper.show_aruco_detection, state="disabled")
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
                                               command=self.scale_helper.calculate_scale)
        self.calculate_scale_button.grid(row=2, column=5, padx=(0, 10))
        
        self.scale_info_label = ttk.Label(scale_frame, text="Escala actual: 1.0 cm/píxel", 
                                         font=("Arial", 9, "italic"))
        self.scale_info_label.grid(row=3, column=0, columnspan=6, pady=(5, 0), sticky=(tk.W))

    def _create_content_frame(self, parent):
        """Crear frame de contenido principal"""
        content_frame = ttk.Frame(parent)
        content_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
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

    def _create_status_frame(self, parent):
        """Crear frame de barra de estado"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=6, column=0, columnspan=3, pady=(10, 0), sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(status_frame, text="Listo para seleccionar imagen")
        self.status_label.grid(row=0, column=0, sticky=(tk.W))

    # Métodos principales
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
            
            # Habilitar vista previa de corrección si está habilitada
            if self.undistortion_enabled.get():
                self.view_undist_button.config(state="normal")
            
            if self.segmentation_helper.requirements["all_ready"]:
                self.segment_button.config(state="normal")
            
            self.display_image(filename)
            self.results_helper.clear_results()

    def get_processed_image_path(self):
        """
        Retorna la ruta de la imagen a usar (original o corregida).
        Si la corrección está habilitada, aplica corrección y retorna la ruta del archivo temporal.
        """
        if not self.undistortion_enabled.get() or not self.current_image_path:
            return self.current_image_path

        try:
            import cv2
            # Cargar imagen original
            original = cv2.imread(self.current_image_path)
            if original is None:
                return self.current_image_path

            # Aplicar corrección
            alpha = self.undistortion_alpha.get()
            undistorted = self.undistorter.undistort_image(original, alpha)

            # Guardar imagen corregida temporalmente
            corrected_path = "temp_undistorted.png"
            cv2.imwrite(corrected_path, undistorted)

            return corrected_path

        except Exception as e:
            print(f"Error al aplicar corrección: {e}")
            return self.current_image_path

    def display_image(self, image_path):
        """Mostrar una imagen en el canvas (delegado al helper)"""
        self.image_display_helper.display_image(image_path)