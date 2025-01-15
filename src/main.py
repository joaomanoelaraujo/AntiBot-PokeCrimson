import time
import pyautogui
import pytesseract
from PIL import ImageGrab
import win32gui
import tkinter as tk
from tkinter import ttk
import threading
from tkinter import messagebox
import os
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR\tessdata'


class MonitorPanel:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Monitor Anti-bot")
        self.root.geometry("400x300")

        self.monitoring = False
        self.selected_hwnd = None
        self.monitor_thread = None
        self.countdown_window = None
        self.monitor_area = None  # Coordenadas da área selecionada

        self.setup_ui()

    def setup_ui(self):
        style = ttk.Style()
        style.configure('TButton', padding=5)
        style.configure('TLabel', padding=5)

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Janelas Disponíveis:").pack(anchor=tk.W)
        self.window_listbox = tk.Listbox(main_frame, height=10)
        self.window_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)

        self.refresh_button = ttk.Button(button_frame, text="Atualizar Lista", command=self.refresh_windows)
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        self.select_area_button = ttk.Button(button_frame, text="Selecionar Área", command=self.select_area)
        self.select_area_button.pack(side=tk.LEFT, padx=5)

        self.monitor_button = ttk.Button(button_frame, text="Iniciar Monitoramento", command=self.toggle_monitoring)
        self.monitor_button.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(main_frame, text="Status: Aguardando")
        self.status_label.pack(anchor=tk.W, pady=5)

        self.refresh_windows()

    def refresh_windows(self):
        self.window_listbox.delete(0, tk.END)
        self.windows = []

        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        self.windows.append((hwnd, title))
                        self.window_listbox.insert(tk.END, title)
                except:
                    pass
            return True

        win32gui.EnumWindows(callback, None)

    def select_area(self):
        # Janela transparente para seleção
        self.selection_window = tk.Toplevel(self.root)
        self.selection_window.attributes("-fullscreen", True)
        self.selection_window.attributes("-alpha", 0.3)
        self.selection_window.configure(bg="black")

        # Canvas para desenhar o retângulo
        self.canvas = tk.Canvas(self.selection_window, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Eventos de clique e arraste
        self.start_x = self.start_y = 0
        self.rect_id = None
        self.canvas.bind("<ButtonPress-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.update_selection)
        self.canvas.bind("<ButtonRelease-1>", self.end_selection)

    def start_selection(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red")

    def update_selection(self, event):
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def end_selection(self, event):
        end_x, end_y = event.x, event.y
        self.monitor_area = (min(self.start_x, end_x), min(self.start_y, end_y),
                             max(self.start_x, end_x), max(self.start_y, end_y))
        self.selection_window.destroy()
        self.status_label.config(text=f"Área selecionada: {self.monitor_area}")

    def toggle_monitoring(self):
        if not self.monitoring:
            if not self.monitor_area:
                messagebox.showwarning("Aviso", "Por favor, selecione uma área para monitorar!")
                return

            selection = self.window_listbox.curselection()
            if not selection:
                messagebox.showwarning("Aviso", "Por favor, selecione uma janela!")
                return

            self.selected_hwnd = self.windows[selection[0]][0]
            self.monitoring = True
            self.monitor_button.configure(text="Parar Monitoramento")
            self.status_label.configure(text="Status: Monitorando...")

            self.monitor_thread = threading.Thread(target=self.monitor_window, daemon=True)
            self.monitor_thread.start()
        else:
            self.monitoring = False
            self.monitor_button.configure(text="Iniciar Monitoramento")
            self.status_label.configure(text="Status: Aguardando")

    def monitor_window(self):
        last_code = None
        while self.monitoring:
            try:
                if not win32gui.IsWindow(self.selected_hwnd):
                    self.root.after(0, lambda: self.status_label.configure(text="Status: Janela não encontrada!"))
                    self.monitoring = False
                    break

                screenshot = ImageGrab.grab(bbox=self.monitor_area)
                gray_image = screenshot.convert("L")
                text = pytesseract.image_to_string(
                    gray_image,
                    lang='por',
                    config='--psm 6'
                )

                pattern = r'Codigo:\s*(\d-\d-\d-\d-\d)'
                match = re.search(pattern, text)

                if match and "[Antibot]" in text:
                    code = match.group(1)
                    if code != last_code:
                        last_code = code
                        self.root.after(0, lambda: self.status_label.configure(text=f"Status: Código detectado: {code}"))
                        self.root.after(0, lambda: self.show_countdown(code))
                        time.sleep(7)

                time.sleep(0.5)

            except Exception as e:
                self.root.after(0, lambda: self.status_label.configure(text=f"Status: Erro - {str(e)}"))
                time.sleep(2)

    def show_countdown(self, code):
        if self.countdown_window:
            self.countdown_window.destroy()

        self.countdown_window = tk.Toplevel(self.root)
        self.countdown_window.title("Código Detectado!")
        self.countdown_window.geometry("300x150")
        self.countdown_window.lift()
        self.countdown_window.attributes('-topmost', True)

        clean_code = code.replace('-', '')

        message = f"Código detectado: {clean_code}\nPreenchendo em..."
        label = ttk.Label(self.countdown_window, text=message, font=('Arial', 12))
        label.pack(pady=20)

        countdown_label = ttk.Label(self.countdown_window, text="5", font=('Arial', 24))
        countdown_label.pack()

        def countdown(count):
            if count > 0:
                countdown_label.config(text=str(count))
                self.countdown_window.after(1000, countdown, count-1)
            else:
                self.countdown_window.destroy()
                pyautogui.press('enter')
                time.sleep(0.2)
                pyautogui.write(f"!antibot {clean_code}")
                time.sleep(0.1)
                pyautogui.press('enter')

        countdown(5)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    panel = MonitorPanel()
    panel.run()
