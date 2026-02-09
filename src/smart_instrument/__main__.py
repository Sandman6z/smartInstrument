"""Main entry point for the smart_instrument package"""

from .main import AutoTestTool
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoTestTool(root)
    root.mainloop()
