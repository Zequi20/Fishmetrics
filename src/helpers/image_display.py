import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox

class ImageDisplayHelper:
    def __init__(self, gui):
        self.gui = gui
    
    def display_image(self, image_path):
        """Mostrar una imagen en el canvas"""
        try:
            pil_image = Image.open(image_path)
            
            canvas_width = max(self.gui.image_canvas.winfo_width(), 760)
            canvas_height = max(self.gui.image_canvas.winfo_height(), 560)
            
            img_width, img_height = pil_image.size
            
            max_width = max(canvas_width - 48, 320)
            max_height = max(canvas_height - 48, 240)
            scale_w = max_width / img_width
            scale_h = max_height / img_height
            scale = min(scale_w, scale_h, 2.0)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            self.gui.photo = ImageTk.PhotoImage(pil_image)
            
            self.gui.image_canvas.delete("all")
            self.gui.image_canvas.create_rectangle(
                0,
                0,
                canvas_width,
                canvas_height,
                fill=self.gui.colors.get("canvas", "#ffffff"),
                outline=""
            )

            x = max((canvas_width - new_width) // 2, 24)
            y = max((canvas_height - new_height) // 2, 24)
            self.gui.image_canvas.create_image(x, y, anchor=tk.NW, image=self.gui.photo)
            
            scroll_width = max(canvas_width, x + new_width + 24)
            scroll_height = max(canvas_height, y + new_height + 24)
            self.gui.image_canvas.configure(scrollregion=(0, 0, scroll_width, scroll_height))
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la imagen: {str(e)}")

    @staticmethod
    def resize_image_for_display(image_path, max_width=700, max_height=500):
        """Redimensiona una imagen para mostrar en la interfaz"""
        try:
            pil_image = Image.open(image_path)
            img_width, img_height = pil_image.size
            
            scale_w = max_width / img_width
            scale_h = max_height / img_height
            scale = min(scale_w, scale_h, 1.5)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            return pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
        except Exception as e:
            raise RuntimeError(f"No se pudo redimensionar la imagen: {str(e)}")
