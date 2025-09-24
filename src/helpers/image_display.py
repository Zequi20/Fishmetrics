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
            
            canvas_width = 700
            canvas_height = 500
            
            img_width, img_height = pil_image.size
            
            scale_w = canvas_width / img_width
            scale_h = canvas_height / img_height
            scale = min(scale_w, scale_h, 1.5)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            self.gui.photo = ImageTk.PhotoImage(pil_image)
            
            self.gui.image_canvas.delete("all")
            self.gui.image_canvas.create_image(canvas_width//2, canvas_height//2, 
                                         anchor=tk.CENTER, image=self.gui.photo)
            
            self.gui.image_canvas.configure(scrollregion=self.gui.image_canvas.bbox("all"))
            
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