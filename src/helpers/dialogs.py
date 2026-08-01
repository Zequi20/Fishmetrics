import tkinter as tk
from tkinter import ttk


class ErrorDialog:
    """Diálogo de error con un resumen claro y detalles técnicos desplegables."""

    def __init__(self, parent, title, message, details=None):
        self.parent = getattr(parent, "root", parent)
        self.owner = parent
        self.details = str(details).strip() if details else ""
        self.details_visible = False

        self.window = tk.Toplevel(self.parent)
        self.window.title(title)
        self.window.resizable(True, False)
        self.window.transient(self.parent)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.configure(bg=self._color("panel", "#ffffff"))

        self._build_content(title, message)
        self._center_window()

        self.window.grab_set()
        self.window.focus_force()
        self.window.bind("<Escape>", lambda _event: self.close())
        self.window.bind("<Return>", lambda _event: self.close())

    def _color(self, name, fallback):
        colors = getattr(self.owner, "colors", None)
        if colors is None:
            colors = getattr(getattr(self.owner, "master", None), "colors", {})
        return colors.get(name, fallback) if colors else fallback

    def _font(self, name, fallback):
        fonts = getattr(self.owner, "fonts", None)
        if fonts is None:
            fonts = getattr(getattr(self.owner, "master", None), "fonts", {})
        return fonts.get(name, fallback) if fonts else fallback

    def _build_content(self, title, message):
        panel = self._color("panel", "#ffffff")
        text_color = self._color("text", "#111827")
        muted = self._color("muted", "#64748b")
        danger_bg = self._color("danger_bg", "#fee2e2")
        danger_fg = self._color("danger_fg", "#b91c1c")
        input_bg = self._color("input", "#ffffff")

        container = tk.Frame(self.window, bg=panel, padx=24, pady=22)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(1, weight=1)

        icon = tk.Label(
            container,
            text="!",
            width=3,
            height=1,
            bg=danger_bg,
            fg=danger_fg,
            font=self._font("hero", ("DejaVu Sans", 14, "bold")),
        )
        icon.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 14))

        tk.Label(
            container,
            text=title,
            bg=panel,
            fg=text_color,
            anchor="w",
            font=self._font("section", ("DejaVu Sans", 10, "bold")),
        ).grid(row=0, column=1, sticky="ew")

        tk.Label(
            container,
            text=message,
            bg=panel,
            fg=text_color,
            anchor="w",
            justify="left",
            wraplength=470,
            font=self._font("base", ("DejaVu Sans", 10)),
        ).grid(row=1, column=1, sticky="ew", pady=(8, 0))

        self.details_frame = tk.Frame(container, bg=panel)
        self.details_frame.columnconfigure(0, weight=1)

        tk.Label(
            self.details_frame,
            text="Detalles técnicos",
            bg=panel,
            fg=muted,
            anchor="w",
            font=self._font("small_bold", ("DejaVu Sans", 9, "bold")),
        ).grid(row=0, column=0, sticky="ew", pady=(0, 6))

        details_box = tk.Text(
            self.details_frame,
            height=7,
            width=68,
            wrap="word",
            bg=input_bg,
            fg=text_color,
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
            padx=10,
            pady=8,
            font=("DejaVu Sans Mono", 9),
        )
        details_box.grid(row=1, column=0, sticky="ew")
        details_box.insert("1.0", self.details)
        details_scrollbar = ttk.Scrollbar(
            self.details_frame,
            orient="vertical",
            command=details_box.yview,
        )
        details_scrollbar.grid(row=1, column=1, sticky="ns")
        details_box.configure(yscrollcommand=details_scrollbar.set)
        details_box.config(state="disabled")

        actions = tk.Frame(container, bg=panel)
        actions.grid(row=3, column=0, columnspan=2, sticky="e", pady=(20, 0))

        if self.details:
            self.details_button = ttk.Button(
                actions,
                text="Ver detalles",
                command=self.toggle_details,
                style="Secondary.TButton",
            )
            self.details_button.grid(row=0, column=0, padx=(0, 8))

        ttk.Button(
            actions,
            text="Entendido",
            command=self.close,
            style="Primary.TButton",
        ).grid(row=0, column=1)

    def toggle_details(self):
        if self.details_visible:
            self.details_frame.grid_remove()
            self.details_button.config(text="Ver detalles")
        else:
            self.details_frame.grid(
                row=2,
                column=0,
                columnspan=2,
                sticky="ew",
                pady=(18, 0),
            )
            self.details_button.config(text="Ocultar detalles")

        self.details_visible = not self.details_visible
        self.window.update_idletasks()
        self._center_window()

    def _center_window(self):
        self.window.update_idletasks()
        width = max(self.window.winfo_reqwidth(), 560)
        height = self.window.winfo_reqheight()

        parent = self.window.master
        x = parent.winfo_rootx() + max((parent.winfo_width() - width) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - height) // 2, 0)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def close(self):
        try:
            self.window.grab_release()
        except tk.TclError:
            pass
        self.window.destroy()


def show_error(parent, title, message, details=None):
    """Muestra un error sin exponer información técnica en el resumen."""
    return ErrorDialog(parent, title, message, details)
