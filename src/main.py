import tkinter as tk
from gui import FishMorphologyGUI   # o from gui.main_window si cambias el nombre

if __name__ == "__main__":
    root = tk.Tk()
    app = FishMorphologyGUI(root)
    root.mainloop()
