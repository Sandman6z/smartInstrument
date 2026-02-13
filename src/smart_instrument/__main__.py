"""Main entry point for the smart_instrument package"""

from .main import AutoTestTool
import tkinter as tk

def main():
    """Main function for the smart_instrument package"""
    root = tk.Tk()
    app = AutoTestTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()
