import os
import subprocess
import webbrowser
import threading
import time
import sys
import socket
import tkinter as tk
from tkinter import messagebox

def is_port_open(port: int) -> bool:
    """Check if localhost:port is already open (Streamlit running)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0

def show_message(title, text):
    """Show a Windows message box (no console needed)."""
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(title, text)
    root.destroy()

def open_browser_with_retry(url: str, attempts: int = 5, delay: float = 2.0):
    """Try to open the browser several times."""
    for _ in range(attempts):
        if is_port_open(8501):
            webbrowser.open(url)
            return True
        time.sleep(delay)
    return False

if __name__ == "__main__":
    url = "http://localhost:8501"

    # --- Launch Streamlit in background ---
    threading.Thread(
        target=lambda: subprocess.run(
            ["streamlit", "run", "main.py"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        ),
        daemon=True,
    ).start()

    # --- Try to open browser ---
    if open_browser_with_retry(url):
        sys.exit(0)
    else:
        show_message(
            "📚 Boekenbeheer",
            "De applicatie is gestart, maar kon de browser niet automatisch openen.\n"
            "Open alstublieft handmatig:\n\nhttp://localhost:8501",
        )
        sys.exit(0)
