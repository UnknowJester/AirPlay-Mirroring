import tkinter as tk
from tkinter import messagebox
import subprocess
import socket
import os
import sys
import ctypes
import win32job
import win32api

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

ENGINE_EXE = os.path.join(APP_DIR, "uxplay-windows.exe")
ICON_PATH = os.path.join(APP_DIR, "resources", "icon.ico")
SINGLE_INSTANCE_PORT = 54329

def focus_existing_window():
    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, "AirPlay Receiver - Windows")
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def update_arguments(device_name="AirPlay4979", low_latency=True):
    args = [f"-n {device_name}", "-nh", "-fps 60"]
    if low_latency:
        args.append("-vsync no")
        args.append("-al 0.1")
    content = " ".join(args) + "\n"
    
    paths = [
        os.path.join(APP_DIR, "arguments.txt"),
        os.path.expandvars(r"%APPDATA%\leapbtw\uxplay-windows\arguments.txt"),
        r"C:\ProgramData\uxplay-windows\arguments.txt"
    ]
    for p in paths:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

class AirPlayController:
    def __init__(self, root):
        self.root = root
        self.root.title("AirPlay Receiver - Windows")
        self.root.geometry("490x540")
        self.root.resizable(False, False)
        self.root.configure(bg="#181825")
        
        if os.path.exists(ICON_PATH):
            try:
                self.root.iconbitmap(ICON_PATH)
            except Exception:
                pass
                
        self.device_name = "AirPlay4979"
        self.engine_proc = None
        self.job = None
        self.local_ip = get_local_ip()
        
        # Setup Windows Job Object so child processes die if parent terminates
        try:
            self.job = win32job.CreateJobObject(None, "")
            info = win32job.QueryInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation)
            info['BasicLimitInformation']['LimitFlags'] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation, info)
        except Exception:
            self.job = None
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._build_ui()
        self.start_engine()

    def _build_ui(self):
        # Header
        hdr_frame = tk.Frame(self.root, bg="#1e1e2e", pady=14)
        hdr_frame.pack(fill="x")
        
        title_lbl = tk.Label(hdr_frame, text="AirPlay Mirroring Receiver", font=("Segoe UI", 16, "bold"),
                             fg="#89b4fa", bg="#1e1e2e")
        title_lbl.pack()
        subtitle_lbl = tk.Label(hdr_frame, text="Duplicazione schermo iPhone su Windows - Zero Limiti",
                                font=("Segoe UI", 9), fg="#a6adc8", bg="#1e1e2e")
        subtitle_lbl.pack()

        main_content = tk.Frame(self.root, bg="#181825", padx=20, pady=12)
        main_content.pack(fill="both", expand=True)

        # Status Card
        status_card = tk.Frame(main_content, bg="#1e1e2e", padx=16, pady=12, highlightbackground="#313244", highlightthickness=1)
        status_card.pack(fill="x", pady=(0, 10))
        
        self.status_icon = tk.Label(status_card, text="● STATO: ATTIVO (In attesa)", font=("Segoe UI", 11, "bold"),
                                    fg="#a6e3a1", bg="#1e1e2e")
        self.status_icon.pack(anchor="w")
        
        self.status_desc = tk.Label(status_card, text=f"Nome AirPlay su iPhone: {self.device_name}",
                                    font=("Segoe UI", 10, "bold"), fg="#cdd6f4", bg="#1e1e2e")
        self.status_desc.pack(anchor="w", pady=(3, 0))
        
        ip_lbl = tk.Label(status_card, text=f"IP Scheda Wi-Fi: {self.local_ip}",
                          font=("Consolas", 9), fg="#6c7086", bg="#1e1e2e")
        ip_lbl.pack(anchor="w", pady=(2, 0))

        # Latency / Performance Card
        perf_card = tk.Frame(main_content, bg="#1e1e2e", padx=16, pady=12, highlightbackground="#313244", highlightthickness=1)
        perf_card.pack(fill="x", pady=(0, 10))
        
        perf_title = tk.Label(perf_card, text="⚡ Ottimizzazione Bassa Latenza (Zero-Lag)", font=("Segoe UI", 10, "bold"),
                              fg="#f9e2af", bg="#1e1e2e")
        perf_title.pack(anchor="w")
        
        self.latency_var = tk.BooleanVar(value=True)
        latency_cb = tk.Checkbutton(perf_card, text="Modalità Bassa Latenza Attiva (-vsync no, audio 100ms)",
                                    variable=self.latency_var, font=("Segoe UI", 9, "bold"),
                                    fg="#a6e3a1", bg="#1e1e2e", selectcolor="#181825",
                                    activebackground="#1e1e2e", activeforeground="#a6e3a1",
                                    command=self.toggle_latency)
        latency_cb.pack(anchor="w", pady=(4, 0))
        
        latency_desc = tk.Label(perf_card, text="Disattiva il ritardo del buffer video per una reattività immediata.",
                                font=("Segoe UI", 8), fg="#a6adc8", bg="#1e1e2e")
        latency_desc.pack(anchor="w")

        # Instructions Card
        instr_card = tk.Frame(main_content, bg="#1e1e2e", padx=16, pady=12, highlightbackground="#313244", highlightthickness=1)
        instr_card.pack(fill="x", pady=(0, 10))
        
        instr_title = tk.Label(instr_card, text="Istruzioni rapide:", font=("Segoe UI", 10, "bold"),
                               fg="#89b4fa", bg="#1e1e2e")
        instr_title.pack(anchor="w", pady=(0, 3))
        
        steps = (
            "1. Connetti l'iPhone alla stessa rete Wi-Fi del computer.\n"
            "2. Apri il Centro di Controllo (scorri dall'alto a destra).\n"
            f"3. Tocca 'Duplica schermo' e premi su '{self.device_name}'."
        )
        instr_text = tk.Label(instr_card, text=steps, font=("Segoe UI", 9),
                              fg="#cdd6f4", bg="#1e1e2e", justify="left")
        instr_text.pack(anchor="w")

        # Info Note
        note_lbl = tk.Label(main_content, text="ℹ️ L'app NON si avvia da sola all'avvio del PC.\nChiudendo questa finestra, tutti i processi vengono terminati al 100%.",
                            font=("Segoe UI", 8), fg="#6c7086", bg="#181825", justify="center")
        note_lbl.pack(pady=(2, 6))

        # Bottom Buttons
        btn_frame = tk.Frame(self.root, bg="#181825", padx=20, pady=10)
        btn_frame.pack(fill="x", side="bottom")

        close_btn = tk.Button(btn_frame, text="⏹ Chiudi e Termina Ricevitore", font=("Segoe UI", 10, "bold"),
                              bg="#f38ba8", fg="#11111b", activebackground="#eba0ac",
                              relief="flat", padx=15, pady=8, cursor="hand2",
                              command=self.on_close)
        close_btn.pack(fill="x")

    def start_engine(self):
        self.stop_engine()
        update_arguments(self.device_name, self.latency_var.get())
        
        if os.path.exists(ENGINE_EXE):
            try:
                creation_flags = 0
                if sys.platform == "win32":
                    creation_flags = subprocess.CREATE_NO_WINDOW
                self.engine_proc = subprocess.Popen(
                    [ENGINE_EXE],
                    cwd=APP_DIR,
                    creationflags=creation_flags
                )
                if self.job and self.engine_proc:
                    try:
                        win32job.AssignProcessToJobObject(self.job, int(self.engine_proc._handle))
                    except Exception:
                        pass
            except Exception as e:
                self.status_desc.config(text=f"Errore avvio motore: {e}", fg="#f38ba8")

    def toggle_latency(self):
        self.start_engine()

    def stop_engine(self):
        if self.engine_proc:
            try:
                self.engine_proc.terminate()
            except Exception:
                pass
            self.engine_proc = None
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/IM", "uxplay-windows.exe"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["taskkill", "/F", "/IM", "uxplay-bluetooth-beacon.exe"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def on_close(self):
        self.stop_engine()
        self.root.destroy()
        sys.exit(0)

def main():
    try:
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lock_socket.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        lock_socket.listen(1)
    except socket.error:
        focus_existing_window()
        sys.exit(0)

    root = tk.Tk()
    app = AirPlayController(root)
    root.mainloop()

if __name__ == "__main__":
    main()
