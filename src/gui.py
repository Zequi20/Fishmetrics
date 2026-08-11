import os
import tkinter as tk
from tkinter import ttk, filedialog

from app_config import AppConfig
from undistortion import CameraUndistortion

from helpers.segmentation import SegmentationHelper
from helpers.aruco import ArucoHelper
from helpers.image_display import ImageDisplayHelper
from helpers.results import MEASUREMENT_DISPLAY_UNITS, ResultsHelper
from helpers.undistortion import UndistortionHelper
from helpers.morphology import MorphologyHelper
from helpers.scale import ScaleHelper
from helpers.dialogs import show_error


class FishMorphologyGUI:
    def __init__(self, root, config_path=None):
        self.root = root
        self.root.title("FishMetrics - Workbench de análisis")
        self.root.geometry("1440x920")
        self.root.minsize(1180, 760)
        self.root.option_add("*tearOff", False)

        # Preferencias persistentes
        self.config = AppConfig(config_path)

        # Variables de dominio
        self.current_image_path = None
        self.current_display_path = None
        self.measurements = None
        self.annotated_image = None
        self.annotated_overlay_image = None
        self.measurement_view_paths = {}
        self.pixel_to_cm_ratio = tk.DoubleVar(value=1.0)
        self.measurement_unit_var = tk.StringVar(value="cm")
        self.segmentation_results = None
        self.aruco_detection = None

        # Sistema de corrección de distorsión
        self.undistorter = CameraUndistortion()
        self.undistorter.set_default_calibration()
        self.undistortion_enabled = tk.BooleanVar(value=False)
        self.undistortion_alpha = tk.DoubleVar(value=1.0)

        # Estado visual
        saved_theme = self.config.get("appearance", "theme", fallback="light").strip().lower()
        theme_was_invalid = saved_theme not in ("light", "dark")
        self.theme_name = "light" if theme_was_invalid else saved_theme
        self.status_kind = "info"
        self.analysis_running = False
        self.step_widgets = {}
        self.summary_values = {}
        self._toast_after_id = None
        self._resize_after_id = None

        # Inicializar helpers
        self.segmentation_helper = SegmentationHelper(self)
        self.aruco_helper = ArucoHelper(self)
        self.image_display_helper = ImageDisplayHelper(self)
        self.results_helper = ResultsHelper(self)
        self.undistortion_helper = UndistortionHelper(self)
        self.morphology_helper = MorphologyHelper(self)
        self.scale_helper = ScaleHelper(self)

        self.create_widgets()
        self.segmentation_helper.check_segmentation_status()
        self._sync_flow_state()

        if self.config.load_error:
            self.root.after_idle(
                lambda error=self.config.load_error: self._show_config_load_error(error)
            )
        elif self.config.write_error:
            self.root.after_idle(
                lambda error=self.config.write_error: self._show_config_write_error(error)
            )
        elif theme_was_invalid:
            try:
                self.config.set("appearance", "theme", self.theme_name)
            except OSError as error:
                self.root.after_idle(lambda error=error: self._show_config_write_error(error))

    def create_widgets(self):
        self._configure_styles()

        main_frame = ttk.Frame(self.root, style="App.TFrame")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        self._create_top_bar(main_frame)

        workspace = ttk.Frame(main_frame, style="App.TFrame", padding=(18, 0, 18, 0))
        workspace.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        workspace.columnconfigure(0, minsize=330, weight=0)
        workspace.columnconfigure(1, weight=1)
        workspace.columnconfigure(2, minsize=360, weight=0)
        workspace.rowconfigure(0, weight=1)

        sidebar = self._create_sidebar(workspace)
        self._create_main_buttons(sidebar)
        self._create_undistortion_frame(sidebar)
        self._create_scale_frame(sidebar)
        self._create_segmentation_frame(sidebar)
        self._create_analysis_frame(sidebar)

        self._create_image_workspace(workspace)
        self._create_results_panel(workspace)
        self._create_status_frame(main_frame)
        self._draw_empty_canvas()

    def _configure_styles(self):
        """Configura tokens visuales y estilos para modo claro/oscuro."""
        self.palettes = self._build_color_palettes()
        self.colors = self.palettes[self.theme_name]
        self.fonts = {
            "base": ("DejaVu Sans", 10),
            "small": ("DejaVu Sans", 9),
            "small_bold": ("DejaVu Sans", 9, "bold"),
            "section": ("DejaVu Sans", 10, "bold"),
            "title": ("DejaVu Sans", 18, "bold"),
            "hero": ("DejaVu Sans", 14, "bold"),
        }

        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self._apply_styles()

    def _build_color_palettes(self):
        return {
            "light": {
                "bg": "#f4f6f8",
                "panel": "#ffffff",
                "panel_alt": "#f8fafc",
                "surface": "#eef2f6",
                "canvas": "#fbfdff",
                "border": "#d0d7de",
                "soft_border": "#e5e7eb",
                "text": "#111827",
                "muted": "#64748b",
                "primary": "#0f766e",
                "primary_active": "#0d5f59",
                "accent": "#2563eb",
                "secondary": "#e8eef7",
                "secondary_active": "#d9e3f2",
                "secondary_disabled": "#eef2f6",
                "button_disabled": "#a7b0bc",
                "input": "#ffffff",
                "progress_trough": "#e8edf5",
                "table": "#ffffff",
                "table_alt": "#f8fafc",
                "table_heading": "#eef2f7",
                "selection": "#2563eb",
                "selection_fg": "#ffffff",
                "pending_bg": "#f1f5f9",
                "pending_fg": "#64748b",
                "ready_bg": "#dbeafe",
                "ready_fg": "#1d4ed8",
                "active_bg": "#fff7ed",
                "active_fg": "#9a3412",
                "success_bg": "#dcfce7",
                "success_fg": "#15803d",
                "warning_bg": "#fef3c7",
                "warning_fg": "#92400e",
                "danger_bg": "#fee2e2",
                "danger_fg": "#b91c1c",
                "success": "#15803d",
                "warning": "#b45309",
                "danger": "#b91c1c",
            },
            "dark": {
                "bg": "#101114",
                "panel": "#181a1f",
                "panel_alt": "#1f232b",
                "surface": "#151820",
                "canvas": "#111317",
                "border": "#2f3542",
                "soft_border": "#242a34",
                "text": "#f4f7fb",
                "muted": "#a1a7b3",
                "primary": "#14b8a6",
                "primary_active": "#0f9f91",
                "accent": "#60a5fa",
                "secondary": "#242b36",
                "secondary_active": "#303948",
                "secondary_disabled": "#1d222b",
                "button_disabled": "#404754",
                "input": "#12151b",
                "progress_trough": "#242a34",
                "table": "#151820",
                "table_alt": "#1b2029",
                "table_heading": "#222833",
                "selection": "#2563eb",
                "selection_fg": "#ffffff",
                "pending_bg": "#232833",
                "pending_fg": "#a1a7b3",
                "ready_bg": "#132c47",
                "ready_fg": "#93c5fd",
                "active_bg": "#3a2718",
                "active_fg": "#fdba74",
                "success_bg": "#14351f",
                "success_fg": "#86efac",
                "warning_bg": "#3a2f13",
                "warning_fg": "#facc15",
                "danger_bg": "#3a181b",
                "danger_fg": "#fca5a5",
                "success": "#22c55e",
                "warning": "#f59e0b",
                "danger": "#ef4444",
            },
        }

    def _apply_styles(self):
        style = self.style
        self.root.configure(bg=self.colors["bg"])

        style.configure(".", font=self.fonts["base"], background=self.colors["panel"], foreground=self.colors["text"])
        style.configure("App.TFrame", background=self.colors["bg"])
        style.configure("TopBar.TFrame", background=self.colors["panel"])
        style.configure("Panel.TFrame", background=self.colors["panel"], relief="solid", borderwidth=1)
        style.configure("PanelInner.TFrame", background=self.colors["panel"])
        style.configure("Surface.TFrame", background=self.colors["surface"])
        style.configure("Status.TFrame", background=self.colors["panel"])

        style.configure("TLabel", background=self.colors["panel"], foreground=self.colors["text"])
        style.configure("App.TLabel", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("Title.TLabel", background=self.colors["panel"], foreground=self.colors["text"], font=self.fonts["title"])
        style.configure("Subtitle.TLabel", background=self.colors["panel"], foreground=self.colors["muted"], font=self.fonts["small"])
        style.configure("Section.TLabel", background=self.colors["panel"], foreground=self.colors["text"], font=self.fonts["section"])
        style.configure("Muted.TLabel", background=self.colors["panel"], foreground=self.colors["muted"], font=self.fonts["small"])
        style.configure("Value.TLabel", background=self.colors["panel"], foreground=self.colors["text"], font=self.fonts["small_bold"])
        style.configure("Status.TLabel", background=self.colors["panel"], foreground=self.colors["muted"], font=self.fonts["small"])
        style.configure("CanvasTitle.TLabel", background=self.colors["panel"], foreground=self.colors["text"], font=self.fonts["hero"])
        style.configure("SidebarTitle.TLabel", background=self.colors["bg"], foreground=self.colors["muted"], font=self.fonts["small_bold"])

        style.configure(
            "TButton",
            background=self.colors["secondary"],
            foreground=self.colors["text"],
            padding=(10, 7),
            font=self.fonts["base"],
        )
        style.map(
            "TButton",
            background=[("active", self.colors["secondary_active"]), ("disabled", self.colors["secondary_disabled"])],
            foreground=[("disabled", self.colors["muted"])],
        )
        style.configure("Primary.TButton", background=self.colors["primary"], foreground="#ffffff", padding=(12, 9), font=self.fonts["section"])
        style.map(
            "Primary.TButton",
            background=[("active", self.colors["primary_active"]), ("disabled", self.colors["button_disabled"])],
            foreground=[("disabled", "#ffffff")],
        )
        style.configure("Secondary.TButton", background=self.colors["secondary"], foreground=self.colors["text"], padding=(10, 7))
        style.map(
            "Secondary.TButton",
            background=[("active", self.colors["secondary_active"]), ("disabled", self.colors["secondary_disabled"])],
            foreground=[("disabled", self.colors["muted"])],
        )
        style.configure("Compact.TButton", background=self.colors["secondary"], foreground=self.colors["text"], padding=(8, 5), font=self.fonts["small"])

        style.configure("TCheckbutton", background=self.colors["panel"], foreground=self.colors["text"])
        style.map("TCheckbutton", background=[("active", self.colors["panel"])])
        style.configure(
            "TCombobox",
            padding=(6, 4),
            fieldbackground=self.colors["input"],
            background=self.colors["secondary"],
            foreground=self.colors["text"],
            arrowcolor=self.colors["muted"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.colors["input"])],
            selectbackground=[("readonly", self.colors["selection"])],
            selectforeground=[("readonly", self.colors["selection_fg"])],
        )
        style.configure(
            "TEntry",
            padding=(6, 4),
            fieldbackground=self.colors["input"],
            foreground=self.colors["text"],
            insertcolor=self.colors["text"],
        )
        style.configure("Horizontal.TProgressbar", troughcolor=self.colors["progress_trough"], background=self.colors["accent"])

        style.configure(
            "Treeview",
            rowheight=32,
            borderwidth=0,
            background=self.colors["table"],
            fieldbackground=self.colors["table"],
            foreground=self.colors["text"],
        )
        style.configure("Treeview.Heading", font=self.fonts["small_bold"], background=self.colors["table_heading"], foreground=self.colors["text"])
        style.map("Treeview", background=[("selected", self.colors["selection"])], foreground=[("selected", self.colors["selection_fg"])])

    def _create_top_bar(self, parent):
        top_bar = ttk.Frame(parent, style="TopBar.TFrame", padding=(20, 14))
        top_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 14))
        top_bar.columnconfigure(0, weight=1)

        title_block = ttk.Frame(top_bar, style="TopBar.TFrame")
        title_block.grid(row=0, column=0, sticky=tk.W)

        ttk.Label(title_block, text="FishMetrics", style="Title.TLabel").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(
            title_block,
            text="Workbench para medición morfológica, escala, segmentación y corrección óptica",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky=tk.W, pady=(2, 0))

        status_area = ttk.Frame(top_bar, style="TopBar.TFrame")
        status_area.grid(row=0, column=1, sticky=(tk.E, tk.N))

        self.header_state_label = tk.Label(
            status_area,
            text="Sin imagen",
            bg=self.colors["pending_bg"],
            fg=self.colors["pending_fg"],
            padx=10,
            pady=4,
            font=self.fonts["small_bold"],
        )
        self.header_state_label.grid(row=0, column=0, sticky=tk.E, padx=(0, 8))

        self.header_scale_label = tk.Label(
            status_area,
            text="Escala 1.0000 cm/px",
            bg=self.colors["ready_bg"],
            fg=self.colors["ready_fg"],
            padx=10,
            pady=4,
            font=self.fonts["small_bold"],
        )
        self.header_scale_label.grid(row=0, column=1, sticky=tk.E)

        self.theme_toggle_button = ttk.Button(
            status_area,
            text="Modo claro" if self.theme_name == "dark" else "Modo oscuro",
            command=self.toggle_theme,
            style="Compact.TButton",
        )
        self.theme_toggle_button.grid(row=0, column=2, sticky=tk.E, padx=(8, 0))

        self.toast_label = tk.Label(
            status_area,
            text="",
            bg=self.colors["panel"],
            fg=self.colors["panel"],
            padx=12,
            pady=6,
            font=self.fonts["small_bold"],
            wraplength=360,
            justify=tk.LEFT,
        )
        self.toast_label.grid(row=1, column=0, columnspan=3, sticky=tk.E, pady=(8, 0))

    def _create_sidebar(self, parent):
        sidebar_shell = ttk.Frame(parent, style="App.TFrame")
        sidebar_shell.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 14))
        sidebar_shell.columnconfigure(0, weight=1)
        sidebar_shell.rowconfigure(0, weight=1)

        sidebar_canvas = tk.Canvas(sidebar_shell, bg=self.colors["bg"], highlightthickness=0, width=330)
        self.sidebar_canvas = sidebar_canvas
        sidebar_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        sidebar_scrollbar = ttk.Scrollbar(sidebar_shell, orient="vertical", command=sidebar_canvas.yview)
        sidebar_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)

        sidebar = ttk.Frame(sidebar_canvas, style="App.TFrame")
        sidebar_window = sidebar_canvas.create_window((0, 0), window=sidebar, anchor="nw")
        sidebar.columnconfigure(0, weight=1)

        ttk.Label(sidebar, text="FLUJO DE TRABAJO", style="SidebarTitle.TLabel").grid(
            row=0, column=0, sticky=tk.W, pady=(0, 8)
        )

        def update_sidebar_scrollregion(_event):
            sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))

        def update_sidebar_width(event):
            sidebar_canvas.itemconfigure(sidebar_window, width=event.width)

        def scroll_sidebar(event):
            if event.num == 4:
                sidebar_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                sidebar_canvas.yview_scroll(1, "units")
            else:
                sidebar_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        sidebar.bind("<Configure>", update_sidebar_scrollregion)
        sidebar_canvas.bind("<Configure>", update_sidebar_width)
        sidebar_canvas.bind("<Enter>", lambda _event: self._bind_mousewheel(sidebar_canvas, scroll_sidebar))
        sidebar_canvas.bind("<Leave>", lambda _event: self._unbind_mousewheel(sidebar_canvas))

        return sidebar

    def _bind_mousewheel(self, widget, callback):
        widget.bind_all("<MouseWheel>", callback)
        widget.bind_all("<Button-4>", callback)
        widget.bind_all("<Button-5>", callback)

    def _unbind_mousewheel(self, widget):
        widget.unbind_all("<MouseWheel>")
        widget.unbind_all("<Button-4>")
        widget.unbind_all("<Button-5>")

    def toggle_theme(self):
        next_theme = "dark" if self.theme_name == "light" else "light"
        self.set_theme(next_theme)

    def set_theme(self, theme_name):
        if theme_name not in self.palettes:
            return

        self.theme_name = theme_name
        self.colors = self.palettes[theme_name]
        self._apply_styles()
        self._refresh_theme_widgets()
        self._sync_flow_state()
        self._redraw_canvas()

        theme_label = "oscuro" if theme_name == "dark" else "claro"
        self.show_toast(f"Modo {theme_label} aplicado", kind="success")

        try:
            self.config.set("appearance", "theme", theme_name)
        except OSError as error:
            self._show_config_write_error(error)

    def _show_config_load_error(self, error):
        self.show_error(
            "No se pudo leer la configuración",
            "FishMetrics inició con sus preferencias predeterminadas porque config.ini está dañado o no se puede leer. Puedes corregir el archivo o eliminarlo para que se genere nuevamente.",
            details=f"Archivo: {self.config.path}\n{type(error).__name__}: {error}",
        )

    def _show_config_write_error(self, error):
        self.show_error(
            "No se pudo guardar la configuración",
            "La preferencia se aplicó durante esta sesión, pero FishMetrics no podrá recordarla al volver a abrirse. Comprueba los permisos de la carpeta del programa.",
            details=f"Archivo: {self.config.path}\n{type(error).__name__}: {error}",
        )

    def _refresh_theme_widgets(self):
        self.root.configure(bg=self.colors["bg"])

        if hasattr(self, "sidebar_canvas"):
            self.sidebar_canvas.configure(bg=self.colors["bg"])

        if hasattr(self, "image_canvas"):
            self.image_canvas.configure(
                bg=self.colors["canvas"],
                highlightbackground=self.colors["border"],
            )

        if hasattr(self, "results_tree"):
            self.results_tree.tag_configure("odd", background=self.colors["table_alt"], foreground=self.colors["text"])
            self.results_tree.tag_configure("even", background=self.colors["table"], foreground=self.colors["text"])

        if hasattr(self, "theme_toggle_button"):
            label = "Modo claro" if self.theme_name == "dark" else "Modo oscuro"
            self.theme_toggle_button.config(text=label)

        if hasattr(self, "toast_label") and not self.toast_label.cget("text"):
            self.toast_label.config(bg=self.colors["panel"], fg=self.colors["panel"])

        if hasattr(self, "status_dot"):
            self.status_dot.config(bg=self._status_dot_color(self.status_kind))

    def _create_step_card(self, parent, row, key, number, title):
        card = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        card.grid(row=row, column=0, pady=(0, 12), sticky=(tk.W, tk.E))
        card.columnconfigure(0, weight=1)

        header = ttk.Frame(card, style="PanelInner.TFrame")
        header.grid(row=0, column=0, sticky=(tk.W, tk.E))
        header.columnconfigure(1, weight=1)

        badge = tk.Label(
            header,
            text=str(number),
            bg=self.colors["pending_bg"],
            fg=self.colors["pending_fg"],
            width=3,
            padx=2,
            pady=3,
            font=self.fonts["small_bold"],
        )
        badge.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        ttk.Label(header, text=title, style="Section.TLabel").grid(row=0, column=1, sticky=tk.W)

        status = tk.Label(
            header,
            text="Pendiente",
            bg=self.colors["pending_bg"],
            fg=self.colors["pending_fg"],
            padx=8,
            pady=3,
            font=self.fonts["small_bold"],
        )
        status.grid(row=0, column=2, sticky=tk.E)

        content = ttk.Frame(card, style="PanelInner.TFrame")
        content.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(12, 0))
        content.columnconfigure(0, weight=1)

        self.step_widgets[key] = {"badge": badge, "status": status}
        return content

    def _set_step_state(self, key, state, text=None):
        widgets = self.step_widgets.get(key)
        if not widgets:
            return

        states = {
            "pending": ("Pendiente", self.colors["pending_bg"], self.colors["pending_fg"]),
            "ready": ("Listo", self.colors["ready_bg"], self.colors["ready_fg"]),
            "active": ("En curso", self.colors["active_bg"], self.colors["active_fg"]),
            "done": ("Completado", self.colors["success_bg"], self.colors["success_fg"]),
            "warning": ("Atención", self.colors["warning_bg"], self.colors["warning_fg"]),
            "danger": ("Error", self.colors["danger_bg"], self.colors["danger_fg"]),
        }
        label, bg, fg = states.get(state, states["pending"])
        widgets["badge"].config(bg=bg, fg=fg)
        widgets["status"].config(text=text or label, bg=bg, fg=fg)

    def _create_main_buttons(self, parent):
        content = self._create_step_card(parent, 1, "image", 1, "Imagen")

        self.select_button = ttk.Button(content, text="Abrir imagen", command=self.select_image, style="Primary.TButton")
        self.select_button.grid(row=0, column=0, sticky=(tk.W, tk.E))

        self.file_quick_label = ttk.Label(content, text="Ningún archivo seleccionado", style="Muted.TLabel", wraplength=280)
        self.file_quick_label.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(8, 0))

    def _create_undistortion_frame(self, parent):
        content = self._create_step_card(parent, 2, "optics", 2, "Corrección óptica")
        content.columnconfigure(1, weight=1)

        self.undist_check = ttk.Checkbutton(
            content,
            text="Activar corrección",
            variable=self.undistortion_enabled,
            command=self.undistortion_helper.on_undistortion_toggle,
        )
        self.undist_check.grid(row=0, column=0, columnspan=3, sticky=tk.W)

        ttk.Label(content, text="Alpha", style="Muted.TLabel").grid(row=1, column=0, sticky=tk.W, pady=(12, 0))
        self.alpha_scale = ttk.Scale(content, from_=0.0, to=1.0, variable=self.undistortion_alpha, orient=tk.HORIZONTAL)
        self.alpha_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 10), pady=(12, 0))

        self.alpha_label = ttk.Label(content, text="1.00", style="Value.TLabel")
        self.alpha_label.grid(row=1, column=2, sticky=tk.E, pady=(12, 0))

        self.undistortion_alpha.trace("w", self.undistortion_helper.update_alpha_label)
        self.alpha_scale.config(state="disabled")

        button_row = ttk.Frame(content, style="PanelInner.TFrame")
        button_row.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(12, 0))
        button_row.columnconfigure((0, 1), weight=1)

        self.view_undist_button = ttk.Button(
            button_row,
            text="Vista previa",
            command=self.undistortion_helper.show_undistortion_preview,
            state="disabled",
            style="Compact.TButton",
        )
        self.view_undist_button.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 6))

        self.calib_info_button = ttk.Button(
            button_row,
            text="Parámetros",
            command=self.undistortion_helper.show_calibration_info,
            style="Compact.TButton",
        )
        self.calib_info_button.grid(row=0, column=1, sticky=(tk.W, tk.E))

        self.load_calib_button = ttk.Button(
            content,
            text="Cargar calibración",
            command=self.undistortion_helper.load_calibration,
            style="Secondary.TButton",
        )
        self.load_calib_button.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(8, 0))

    def _create_scale_frame(self, parent):
        content = self._create_step_card(parent, 3, "scale", 3, "Escala")
        content.columnconfigure((0, 1), weight=1)

        ttk.Label(content, text="Automática ArUco 4x4", style="Muted.TLabel").grid(
            row=0, column=0, columnspan=2, sticky=tk.W
        )

        marker_size_frame = ttk.Frame(content, style="PanelInner.TFrame")
        marker_size_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(8, 0))
        marker_size_frame.columnconfigure(0, weight=1)

        ttk.Label(marker_size_frame, text="Lado exterior del marcador", style="Muted.TLabel").grid(
            row=0, column=0, columnspan=2, sticky=tk.W
        )

        self.aruco_size_entry = ttk.Entry(marker_size_frame, width=12)
        self.aruco_size_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 6), pady=(6, 0))

        self.aruco_size_unit_var = tk.StringVar(value="mm")
        self.aruco_size_unit_combo = ttk.Combobox(
            marker_size_frame,
            textvariable=self.aruco_size_unit_var,
            values=("mm", "cm"),
            state="readonly",
            width=5,
        )
        self.aruco_size_unit_combo.grid(row=1, column=1, sticky=tk.E, pady=(6, 0))

        ttk.Label(
            marker_size_frame,
            text="Mide un lado del cuadrado, de borde exterior a borde exterior.",
            style="Muted.TLabel",
            wraplength=280,
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        self.detect_aruco_button = ttk.Button(
            content,
            text="Detectar ArUco",
            command=self.aruco_helper.detect_aruco_scale,
            state="disabled",
            style="Compact.TButton",
        )
        self.detect_aruco_button.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=(0, 6), pady=(10, 0))

        self.show_aruco_button = ttk.Button(
            content,
            text="Ver detección",
            command=self.aruco_helper.show_aruco_detection,
            state="disabled",
            style="Compact.TButton",
        )
        self.show_aruco_button.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(10, 0))

        self.aruco_status_label = ttk.Label(content, text="No detectado", style="Muted.TLabel")
        self.aruco_status_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))

        ttk.Separator(content, orient="horizontal").grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(12, 10))

        manual_frame = ttk.Frame(content, style="PanelInner.TFrame")
        manual_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E))
        manual_frame.columnconfigure((0, 2), weight=1)

        ttk.Label(manual_frame, text="Relación manual", style="Muted.TLabel").grid(row=0, column=0, columnspan=4, sticky=tk.W)

        self.pixels_entry = ttk.Entry(manual_frame, width=10)
        self.pixels_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 6), pady=(6, 0))
        self.pixels_entry.insert(0, "100")

        ttk.Label(manual_frame, text="px =", style="Muted.TLabel").grid(row=1, column=1, sticky=tk.W, padx=(0, 6), pady=(6, 0))

        self.cm_entry = ttk.Entry(manual_frame, width=10)
        self.cm_entry.grid(row=1, column=2, sticky=(tk.W, tk.E), padx=(0, 6), pady=(6, 0))
        self.cm_entry.insert(0, "1.0")

        ttk.Label(manual_frame, text="cm", style="Muted.TLabel").grid(row=1, column=3, sticky=tk.W, pady=(6, 0))

        self.calculate_scale_button = ttk.Button(
            content,
            text="Aplicar escala manual",
            command=self.scale_helper.calculate_scale,
            style="Secondary.TButton",
        )
        self.calculate_scale_button.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        self.scale_info_label = ttk.Label(content, text="Escala actual: 1.0000 cm/píxel", style="Muted.TLabel")
        self.scale_info_label.grid(row=7, column=0, columnspan=2, pady=(8, 0), sticky=tk.W)

    def _create_segmentation_frame(self, parent):
        content = self._create_step_card(parent, 4, "segmentation", 4, "Segmentación")
        content.columnconfigure(1, weight=1)

        ttk.Label(content, text="Dispositivo", style="Muted.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        self.device_var = tk.StringVar(value="cpu")
        device_combo = ttk.Combobox(content, textvariable=self.device_var, values=["cpu", "cuda"], state="readonly", width=8)
        device_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))

        self.segment_button = ttk.Button(
            content,
            text="Generar segmentación",
            command=self.segmentation_helper.run_segmentation_async,
            state="disabled",
            style="Secondary.TButton",
        )
        self.segment_button.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        self.seg_progress_var = tk.StringVar(value="Listo")
        self.seg_status_label = ttk.Label(content, textvariable=self.seg_progress_var, style="Muted.TLabel")
        self.seg_status_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))

        self.seg_progress_bar = ttk.Progressbar(content, mode="indeterminate")
        self.seg_progress_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(6, 10))

        preview_row = ttk.Frame(content, style="PanelInner.TFrame")
        preview_row.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E))
        preview_row.columnconfigure((0, 1, 2), weight=1)

        self.view_mask_button = ttk.Button(
            preview_row,
            text="Máscara",
            command=lambda: self.segmentation_helper.show_segmentation_result("mask_color"),
            state="disabled",
            style="Compact.TButton",
        )
        self.view_mask_button.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 6))

        self.view_overlay_button = ttk.Button(
            preview_row,
            text="Overlay",
            command=lambda: self.segmentation_helper.show_segmentation_result("overlay"),
            state="disabled",
            style="Compact.TButton",
        )
        self.view_overlay_button.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 6))

        self.view_ids_button = ttk.Button(
            preview_row,
            text="IDs",
            command=lambda: self.segmentation_helper.show_segmentation_result("mask_vis"),
            state="disabled",
            style="Compact.TButton",
        )
        self.view_ids_button.grid(row=0, column=2, sticky=(tk.W, tk.E))

    def _create_analysis_frame(self, parent):
        content = self._create_step_card(parent, 5, "analysis", 5, "Análisis")
        content.columnconfigure((0, 1), weight=1)

        self.analyze_button = ttk.Button(
            content,
            text="Analizar morfometría",
            command=self.morphology_helper.analyze_image,
            state="disabled",
            style="Primary.TButton",
        )
        self.analyze_button.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))

        self.analysis_hint_label = ttk.Label(content, text="Esperando segmentación", style="Muted.TLabel")
        self.analysis_hint_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))

        self.view_measurements_mask_button = ttk.Button(
            content,
            text="Sobre máscara",
            command=lambda: self.morphology_helper.show_measurement_result("mask"),
            state="disabled",
            style="Compact.TButton",
        )
        self.view_measurements_mask_button.grid(
            row=2, column=0, sticky=(tk.W, tk.E), padx=(0, 4), pady=(10, 0)
        )

        self.view_measurements_overlay_button = ttk.Button(
            content,
            text="Sobre original",
            command=lambda: self.morphology_helper.show_measurement_result("overlay"),
            state="disabled",
            style="Compact.TButton",
        )
        self.view_measurements_overlay_button.grid(
            row=2, column=1, sticky=(tk.W, tk.E), padx=(4, 0), pady=(10, 0)
        )

    def _create_image_workspace(self, parent):
        image_frame = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        image_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 14))
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(1, weight=1)

        header = ttk.Frame(image_frame, style="PanelInner.TFrame")
        header.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Visor", style="CanvasTitle.TLabel").grid(row=0, column=0, sticky=tk.W)

        self.original_image_button = ttk.Button(
            header,
            text="Original",
            command=self.show_original_image,
            state="disabled",
            style="Compact.TButton",
        )
        self.original_image_button.grid(row=0, column=1, sticky=tk.E, padx=(0, 8))

        self.image_state_label = tk.Label(
            header,
            text="Sin imagen",
            bg=self.colors["pending_bg"],
            fg=self.colors["pending_fg"],
            padx=10,
            pady=4,
            font=self.fonts["small_bold"],
        )
        self.image_state_label.grid(row=0, column=2, sticky=tk.E)

        canvas_shell = ttk.Frame(image_frame, style="Surface.TFrame", padding=10)
        canvas_shell.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        canvas_shell.columnconfigure(0, weight=1)
        canvas_shell.rowconfigure(0, weight=1)

        self.image_canvas = tk.Canvas(
            canvas_shell,
            bg=self.colors["canvas"],
            width=760,
            height=560,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            relief="flat",
        )
        self.image_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.image_canvas.bind("<Configure>", self._schedule_canvas_redraw)

        h_scrollbar = ttk.Scrollbar(canvas_shell, orient="horizontal", command=self.image_canvas.xview)
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        v_scrollbar = ttk.Scrollbar(canvas_shell, orient="vertical", command=self.image_canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.image_canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)

    def _create_results_panel(self, parent):
        results_frame = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        results_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(3, weight=1)

        ttk.Label(results_frame, text="Inspector", style="CanvasTitle.TLabel").grid(row=0, column=0, sticky=tk.W)

        self.file_info = ttk.Label(results_frame, text="Ningún archivo seleccionado", style="Muted.TLabel", wraplength=320)
        self.file_info.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(6, 14))

        summary = ttk.Frame(results_frame, style="PanelInner.TFrame")
        summary.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 14))
        summary.columnconfigure(1, weight=1)

        self._create_fact_row(summary, 0, "Escala", "1.0000 cm/px", "scale")
        self._create_fact_row(summary, 1, "Marcador", "No detectado", "marker")
        self._create_fact_row(summary, 2, "Segmentación", "Pendiente", "segmentation")
        self._create_fact_row(summary, 3, "Mediciones", "0", "measurements")

        table_shell = ttk.Frame(results_frame, style="PanelInner.TFrame")
        table_shell.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        table_shell.columnconfigure(0, weight=1)
        table_shell.rowconfigure(2, weight=1)

        ttk.Label(table_shell, text="Resultados", style="Section.TLabel").grid(row=0, column=0, sticky=tk.W, pady=(0, 8))

        unit_row = ttk.Frame(table_shell, style="PanelInner.TFrame")
        unit_row.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
        unit_row.columnconfigure(1, weight=1)
        ttk.Label(unit_row, text="Unidad", style="Muted.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
        self.measurement_unit_combo = ttk.Combobox(
            unit_row,
            textvariable=self.measurement_unit_var,
            values=MEASUREMENT_DISPLAY_UNITS,
            state="readonly",
            width=12,
        )
        self.measurement_unit_combo.grid(row=0, column=1, sticky=tk.E)
        self.measurement_unit_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.results_helper.display_results(),
        )

        columns = ("Medición", "Valor")
        self.results_tree = ttk.Treeview(table_shell, columns=columns, show="headings", height=12)
        self.results_tree.heading("Medición", text="Medición")
        self.results_tree.heading("Valor", text="Valor (cm)")
        self.results_tree.column("Medición", width=185, anchor=tk.W)
        self.results_tree.column("Valor", width=115, anchor=tk.E)
        self.results_tree.tag_configure("odd", background=self.colors["table_alt"], foreground=self.colors["text"])
        self.results_tree.tag_configure("even", background=self.colors["table"], foreground=self.colors["text"])

        self.results_tree.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        tree_scrollbar = ttk.Scrollbar(table_shell, orient="vertical", command=self.results_tree.yview)
        tree_scrollbar.grid(row=2, column=1, sticky=(tk.N, tk.S))
        self.results_tree.configure(yscrollcommand=tree_scrollbar.set)

        self.save_button = ttk.Button(
            results_frame,
            text="Exportar YAML",
            command=self.results_helper.save_results,
            state="disabled",
            style="Primary.TButton",
        )
        self.save_button.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(14, 0))

    def _create_fact_row(self, parent, row, label, value, key):
        ttk.Label(parent, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky=tk.W, pady=3)
        value_label = ttk.Label(parent, text=value, style="Value.TLabel")
        value_label.grid(row=row, column=1, sticky=tk.E, pady=3)
        self.summary_values[key] = value_label

    def _create_status_frame(self, parent):
        status_frame = ttk.Frame(parent, style="Status.TFrame", padding=(20, 10))
        status_frame.grid(row=2, column=0, pady=(14, 0), sticky=(tk.W, tk.E))
        status_frame.columnconfigure(1, weight=1)

        self.status_dot = tk.Label(status_frame, text="", width=2, bg=self._status_dot_color("info"))
        self.status_dot.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        self.status_label = ttk.Label(
            status_frame,
            text="Listo para seleccionar imagen",
            style="Status.TLabel",
            wraplength=820,
        )
        self.status_label.grid(row=0, column=1, sticky=tk.W)

        self.status_context_label = ttk.Label(status_frame, text="FishMetrics", style="Status.TLabel")
        self.status_context_label.grid(row=0, column=2, sticky=tk.E)

    def _schedule_canvas_redraw(self, _event=None):
        if self._resize_after_id:
            self.root.after_cancel(self._resize_after_id)
        self._resize_after_id = self.root.after(120, self._redraw_canvas)

    def _redraw_canvas(self):
        self._resize_after_id = None
        if self.current_display_path:
            self.image_display_helper.display_image(self.current_display_path)
        else:
            self._draw_empty_canvas()

    def _draw_empty_canvas(self):
        if not hasattr(self, "image_canvas"):
            return
        width = max(self.image_canvas.winfo_width(), 760)
        height = max(self.image_canvas.winfo_height(), 560)
        self.image_canvas.delete("all")
        self.image_canvas.configure(scrollregion=(0, 0, width, height))
        self.image_canvas.create_rectangle(0, 0, width, height, fill=self.colors["canvas"], outline="")
        self.image_canvas.create_text(
            width // 2,
            height // 2 - 16,
            text="Sin imagen",
            fill=self.colors["text"],
            font=self.fonts["hero"],
        )
        self.image_canvas.create_text(
            width // 2,
            height // 2 + 14,
            text="Abre una imagen para iniciar el flujo de análisis",
            fill=self.colors["muted"],
            font=self.fonts["small"],
        )

    def set_status(self, text, kind="info", busy=False, toast=False):
        self.status_kind = kind
        if hasattr(self, "status_label"):
            self.status_label.config(text=text)
        self.set_busy(busy)

        if hasattr(self, "status_dot"):
            self.status_dot.config(bg=self._status_dot_color(kind))
        if toast:
            self.show_toast(text, kind)

    def show_error(self, title, message, details=None):
        """Muestra un mensaje claro y mantiene los detalles técnicos contraídos."""
        return show_error(self, title, message, details)

    def set_busy(self, busy):
        self.root.configure(cursor="watch" if busy else "")

    def _status_dot_color(self, kind):
        status_colors = {
            "info": self.colors["ready_fg"],
            "active": self.colors["active_fg"],
            "success": self.colors["success_fg"],
            "warning": self.colors["warning_fg"],
            "danger": self.colors["danger_fg"],
        }
        return status_colors.get(kind, self.colors["ready_fg"])

    def show_toast(self, message, kind="info", duration=2800):
        if not hasattr(self, "toast_label"):
            return

        palette = {
            "info": (self.colors["ready_bg"], self.colors["ready_fg"]),
            "active": (self.colors["active_bg"], self.colors["active_fg"]),
            "success": (self.colors["success_bg"], self.colors["success_fg"]),
            "warning": (self.colors["warning_bg"], self.colors["warning_fg"]),
            "danger": (self.colors["danger_bg"], self.colors["danger_fg"]),
        }
        bg, fg = palette.get(kind, palette["info"])
        self.toast_label.config(text=message, bg=bg, fg=fg)

        if self._toast_after_id:
            self.root.after_cancel(self._toast_after_id)
        self._toast_after_id = self.root.after(duration, self._hide_toast)

    def _hide_toast(self):
        self._toast_after_id = None
        if hasattr(self, "toast_label"):
            self.toast_label.config(text="", bg=self.colors["panel"], fg=self.colors["panel"])

    def _format_scale(self):
        return f"{self.pixel_to_cm_ratio.get():.4f} cm/px"

    def _sync_flow_state(self):
        has_image = bool(self.current_image_path)
        has_segmentation = bool(self.segmentation_results)
        has_measurements = bool(self.measurements)
        has_aruco = bool(self.aruco_detection and self.aruco_detection.get("detected"))
        segmentation_ready = getattr(self.segmentation_helper, "requirements", {}).get("all_ready", False)

        self._set_step_state("image", "done" if has_image else "pending", "Cargada" if has_image else "Pendiente")
        self._set_step_state("optics", "done" if self.undistortion_enabled.get() else "ready", "Activa" if self.undistortion_enabled.get() else "Opcional")
        if has_aruco:
            self._set_step_state("scale", "done", "ArUco")
        elif self.pixel_to_cm_ratio.get() != 1.0:
            self._set_step_state("scale", "done", "Manual")
        else:
            self._set_step_state("scale", "ready", "Lista")

        if has_segmentation:
            self._set_step_state("segmentation", "done", "Completada")
        elif has_image and segmentation_ready:
            self._set_step_state("segmentation", "ready", "Lista")
        elif segmentation_ready:
            self._set_step_state("segmentation", "pending", "Pendiente")
        else:
            self._set_step_state("segmentation", "warning", "Falta modelo")

        if has_measurements:
            self._set_step_state("analysis", "done", "Medido")
        elif has_segmentation:
            self._set_step_state("analysis", "ready", "Listo")
        else:
            self._set_step_state("analysis", "pending", "Pendiente")

        if hasattr(self, "analyze_button"):
            if self.analysis_running:
                self.analyze_button.config(text="Analizando...", state="disabled")
            elif has_measurements:
                self.analyze_button.config(text="Reanalizar morfometría", state="normal")
            elif has_image:
                self.analyze_button.config(text="Analizar morfometría", state="normal")
            else:
                self.analyze_button.config(text="Analizar morfometría", state="disabled")

        if hasattr(self, "header_state_label"):
            if has_measurements:
                self.header_state_label.config(text="Análisis completo", bg=self.colors["success_bg"], fg=self.colors["success_fg"])
            elif has_segmentation:
                self.header_state_label.config(text="Segmentado", bg=self.colors["ready_bg"], fg=self.colors["ready_fg"])
            elif has_image:
                self.header_state_label.config(text="Imagen cargada", bg=self.colors["ready_bg"], fg=self.colors["ready_fg"])
            else:
                self.header_state_label.config(text="Sin imagen", bg=self.colors["pending_bg"], fg=self.colors["pending_fg"])

        if hasattr(self, "header_scale_label"):
            self.header_scale_label.config(text=f"Escala {self._format_scale()}", bg=self.colors["ready_bg"], fg=self.colors["ready_fg"])

        if hasattr(self, "image_state_label"):
            if self.current_display_path:
                display_name = os.path.basename(str(self.current_display_path))
                self.image_state_label.config(text=display_name[:34], bg=self.colors["ready_bg"], fg=self.colors["ready_fg"])
            else:
                self.image_state_label.config(text="Sin imagen", bg=self.colors["pending_bg"], fg=self.colors["pending_fg"])

        if hasattr(self, "analysis_hint_label"):
            if self.analysis_running:
                self.analysis_hint_label.config(text="Calculando nuevamente las medidas")
            elif has_measurements:
                self.analysis_hint_label.config(text="Puedes recalcular usando la segmentación actual")
            elif has_segmentation:
                self.analysis_hint_label.config(text="Segmentación lista para medir")
            elif has_image:
                self.analysis_hint_label.config(text="Genera segmentación para medir")
            else:
                self.analysis_hint_label.config(text="Esperando imagen")

        if self.summary_values:
            self.summary_values["scale"].config(text=self._format_scale())
            self.summary_values["marker"].config(text="Detectado" if has_aruco else "No detectado")
            self.summary_values["segmentation"].config(text="Completada" if has_segmentation else "Pendiente")
            self.summary_values["measurements"].config(text=str(len(self.measurements or {})))

    def show_original_image(self):
        if not self.current_image_path:
            return
        self.display_image(self.current_image_path)
        self.set_status("Mostrando imagen original", kind="info")

    # Métodos principales
    def select_image(self):
        """Seleccionar una imagen para analizar."""
        file_types = [
            ("Imágenes", "*.png *.jpg *.jpeg *.bmp *.tiff"),
            ("PNG", "*.png"),
            ("JPEG", "*.jpg *.jpeg"),
            ("Todos los archivos", "*.*"),
        ]

        filename = filedialog.askopenfilename(
            title="Seleccionar imagen de pez",
            filetypes=file_types,
            initialdir=self._get_initial_image_directory(),
        )

        if filename:
            self._remember_image_directory(filename)
            self.current_image_path = filename
            basename = os.path.basename(filename)

            self.results_helper.clear_results()
            self.file_info.config(text=f"Archivo: {basename}")
            self.file_quick_label.config(text=basename)

            self.analyze_button.config(state="normal")
            self.detect_aruco_button.config(state="normal")
            self.original_image_button.config(state="normal")

            if self.undistortion_enabled.get():
                self.view_undist_button.config(state="normal")

            if self.segmentation_helper.requirements["all_ready"]:
                self.segment_button.config(state="normal")

            self.display_image(filename)
            self.set_status(
                "Imagen seleccionada",
                kind="success",
                toast=True,
            )
            self._sync_flow_state()

    def _get_initial_image_directory(self):
        """Obtiene la última carpeta válida usada para seleccionar imágenes."""
        configured_directory = self.config.get(
            "paths",
            "last_image_directory",
            fallback="",
        ).strip()
        if configured_directory:
            resolved_directory = os.path.abspath(os.path.expanduser(configured_directory))
            if os.path.isdir(resolved_directory):
                return resolved_directory

        return os.path.dirname(os.path.abspath(__file__))

    def _remember_image_directory(self, filename):
        """Persiste la carpeta de la imagen elegida sin interrumpir su carga."""
        image_directory = os.path.dirname(os.path.abspath(filename))
        try:
            self.config.set("paths", "last_image_directory", image_directory)
        except OSError as error:
            self.root.after_idle(
                lambda error=error: self._show_config_write_error(error)
            )

    def get_processed_image_path(self):
        """
        Retorna la ruta de la imagen a usar (original o corregida).
        Si la corrección está habilitada, aplica corrección y retorna la ruta del archivo temporal.
        """
        if not self.undistortion_enabled.get() or not self.current_image_path:
            return self.current_image_path

        try:
            import cv2

            original = cv2.imread(self.current_image_path)
            if original is None:
                return self.current_image_path

            alpha = self.undistortion_alpha.get()
            undistorted = self.undistorter.undistort_image(original, alpha)

            corrected_path = "temp_undistorted.png"
            cv2.imwrite(corrected_path, undistorted)

            return corrected_path

        except Exception as e:
            print(f"Error al aplicar corrección: {e}")
            return self.current_image_path

    def display_image(self, image_path):
        """Mostrar una imagen en el canvas (delegado al helper)."""
        self.current_display_path = str(image_path)
        self.image_display_helper.display_image(str(image_path))
        self._sync_flow_state()
