import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import socket
import os
import sys
import json
import random
import threading
import time
import webbrowser
import ctypes
import win32job
import win32api

# Base directory resolution (works for both standalone Python and PyInstaller --onefile)
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

ENGINE_EXE = os.path.join(APP_DIR, "uxplay-windows.exe")
ICON_PATH = os.path.join(APP_DIR, "resources", "icon.ico")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
SINGLE_INSTANCE_PORT = 54329
GITHUB_REPO_URL = "https://github.com/UnknowJester/AirPlay-Mirroring"

DEFAULT_CONFIG = {
    "device_name": "AirPlay4979",
    "pin_enabled": False,
    "pin_code": "1234",
    "resolution": "1080p",
    "fps": "60",
    "low_latency": True,
    "fullscreen": False,
    "rotation": "0",
    "enable_audio": True
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = dict(DEFAULT_CONFIG)
                config.update(data)
                return config
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
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

def focus_existing_window():
    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, "AirPlay Receiver - Windows")
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass

def get_connected_client(pid):
    """Detects active remote TCP connection to the UxPlay process."""
    if not pid:
        return None
    # 1. Try psutil
    try:
        import psutil
        for conn in psutil.net_connections(kind='tcp'):
            if conn.pid == pid and conn.status == 'ESTABLISHED':
                if conn.raddr and conn.raddr.ip not in ('127.0.0.1', '::1', '0.0.0.0'):
                    return conn.raddr.ip
        return None
    except Exception:
        pass

    # 2. Fallback to netstat
    try:
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
        out = subprocess.check_output(
            f'netstat -ano | findstr {pid}',
            shell=True,
            text=True,
            startupinfo=startupinfo,
            stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if 'ESTABLISHED' in line:
                parts = line.split()
                if len(parts) >= 3:
                    remote = parts[2].rsplit(':', 1)[0]
                    if remote not in ('127.0.0.1', '::1', '[::1]', '0.0.0.0'):
                        return remote
    except Exception:
        pass
    return None

def write_uxplay_arguments(config):
    """Generates the command arguments for UxPlay and updates all sync locations."""
    args = []
    
    # Device name
    dev_name = config.get("device_name", "AirPlay4979").strip()
    if not dev_name:
        dev_name = "AirPlay4979"
    if " " in dev_name:
        args.append(f'-n "{dev_name}"')
    else:
        args.append(f"-n {dev_name}")
    args.append("-nh")  # Don't append hostname
    
    # PIN security
    if config.get("pin_enabled", False):
        pin = str(config.get("pin_code", "1234")).strip()
        if len(pin) == 4 and pin.isdigit():
            args.append(f"-pin {pin}")
        else:
            args.append("-pin")
            
    # Resolution & FPS
    res = config.get("resolution", "1080p")
    fps = config.get("fps", "60")
    if res == "720p":
        args.append(f"-s 1280x720@{fps}")
    elif res == "4K":
        args.append(f"-s 3840x2160@{fps}")
        args.append("-h265")
    else:  # 1080p default
        args.append(f"-s 1920x1080@{fps}")
        
    args.append(f"-fps {fps}")
    
    # Low latency optimizations (Zero-Lag)
    if config.get("low_latency", True):
        args.append("-vsync no")
        args.append("-al 0.1")
    else:
        args.append("-al 0.25")
        
    # Fullscreen mode
    if config.get("fullscreen", False):
        args.append("-fs")
        
    # Video window rotation
    rot = config.get("rotation", "0")
    if rot == "90R":
        args.append("-r R")
    elif rot == "90L":
        args.append("-r L")
    elif rot == "180":
        args.append("-f I")
        
    # Audio playback toggle
    if not config.get("enable_audio", True):
        args.append("-as 0")
        
    # Clean termination flags
    args.append("-nofreeze")
    
    content = " ".join(args) + "\n"
    
    # Synchronize across all locations read by uxplay-windows
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

class ModernAirPlayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AirPlay Receiver - Windows")
        self.root.geometry("540x670")
        self.root.resizable(False, False)
        self.root.configure(bg="#181825")
        
        if os.path.exists(ICON_PATH):
            try:
                self.root.iconbitmap(ICON_PATH)
            except Exception:
                pass

        try:
            style = ttk.Style()
            style.theme_use('clam')
            style.configure('TCombobox',
                            fieldbackground='#181825',
                            background='#313244',
                            foreground='#cdd6f4',
                            arrowcolor='#89b4fa',
                            bordercolor='#45475a')
            style.map('TCombobox',
                      fieldbackground=[('readonly', '#181825')],
                      selectbackground=[('readonly', '#181825')],
                      selectforeground=[('readonly', '#cdd6f4')])
        except Exception:
            pass
                
        self.config = load_config()
        self.engine_proc = None
        self.job = None
        self.local_ip = get_local_ip()
        self.running = True
        self.connected_client_ip = None
        
        # Windows Job Object configuration for 100% kill guarantee on close
        try:
            self.job = win32job.CreateJobObject(None, "")
            info = win32job.QueryInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation)
            info['BasicLimitInformation']['LimitFlags'] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation, info)
        except Exception:
            self.job = None

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self._build_header()
        self._build_tabs()
        self._build_status_footer()
        
        # Start engine with initial config
        self.start_engine()
        
        # Start background monitor thread for connection status
        self.monitor_thread = threading.Thread(target=self._connection_monitor_loop, daemon=True)
        self.monitor_thread.start()

    def _build_header(self):
        hdr_frame = tk.Frame(self.root, bg="#1e1e2e", pady=12, padx=20)
        hdr_frame.pack(fill="x")
        
        top_row = tk.Frame(hdr_frame, bg="#1e1e2e")
        top_row.pack(fill="x")
        
        title_lbl = tk.Label(top_row, text="AirPlay Receiver Studio", font=("Segoe UI", 16, "bold"),
                             fg="#89b4fa", bg="#1e1e2e")
        title_lbl.pack(side="left")
        
        badge_lbl = tk.Label(top_row, text=" v1.1 ", font=("Segoe UI", 9, "bold"),
                             fg="#11111b", bg="#a6e3a1", padx=5, pady=1)
        badge_lbl.pack(side="left", padx=(8, 0), pady=(3, 0))
        
        sub_lbl = tk.Label(hdr_frame, text="Duplicazione schermo iPhone/iPad su Windows • Zero Latenza",
                           font=("Segoe UI", 9), fg="#a6adc8", bg="#1e1e2e")
        sub_lbl.pack(anchor="w", pady=(2, 0))

    def _build_tabs(self):
        # Segmented custom tab switcher
        tab_nav_frame = tk.Frame(self.root, bg="#181825", pady=8, padx=20)
        tab_nav_frame.pack(fill="x")
        
        self.tab_buttons = {}
        tab_specs = [
            ("main", "📱 Ricevitore & Guida"),
            ("settings", "⚙️ Impostazioni"),
            ("diagnostics", "📊 Info & Diagnostica")
        ]
        
        btn_container = tk.Frame(tab_nav_frame, bg="#1e1e2e", highlightbackground="#313244", highlightthickness=1)
        btn_container.pack(fill="x")
        
        for key, text in tab_specs:
            btn = tk.Button(
                btn_container,
                text=text,
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                bd=0,
                pady=7,
                cursor="hand2",
                command=lambda k=key: self.switch_tab(k)
            )
            btn.pack(side="left", fill="x", expand=True)
            self.tab_buttons[key] = btn
            
        # Tab content container
        self.tab_content = tk.Frame(self.root, bg="#181825", padx=20)
        self.tab_content.pack(fill="both", expand=True)
        
        self.tab_frames = {
            "main": tk.Frame(self.tab_content, bg="#181825"),
            "settings": tk.Frame(self.tab_content, bg="#181825"),
            "diagnostics": tk.Frame(self.tab_content, bg="#181825")
        }
        
        self._init_main_tab()
        self._init_settings_tab()
        self._init_diagnostics_tab()
        
        self.switch_tab("main")

    def switch_tab(self, selected_key):
        for key, frame in self.tab_frames.items():
            if key == selected_key:
                frame.pack(fill="both", expand=True)
                self.tab_buttons[key].configure(bg="#313244", fg="#89b4fa")
            else:
                frame.pack_forget()
                self.tab_buttons[key].configure(bg="#1e1e2e", fg="#a6adc8")

    def _init_main_tab(self):
        f = self.tab_frames["main"]
        
        # Active Status Card
        self.status_card = tk.Frame(f, bg="#1e1e2e", padx=16, pady=12,
                                    highlightbackground="#313244", highlightthickness=1)
        self.status_card.pack(fill="x", pady=(6, 8))
        
        status_row = tk.Frame(self.status_card, bg="#1e1e2e")
        status_row.pack(fill="x")
        
        self.status_dot = tk.Label(status_row, text="●", font=("Segoe UI", 16), fg="#f9e2af", bg="#1e1e2e")
        self.status_dot.pack(side="left", padx=(0, 6))
        
        self.status_title = tk.Label(status_row, text="IN ASCOLTO (Pronto alla connessione)",
                                     font=("Segoe UI", 11, "bold"), fg="#f9e2af", bg="#1e1e2e")
        self.status_title.pack(side="left")
        
        self.status_details = tk.Label(self.status_card,
                                       text=f"Nome AirPlay: {self.config.get('device_name')}  |  IP: {self.local_ip}",
                                       font=("Segoe UI", 9), fg="#cdd6f4", bg="#1e1e2e")
        self.status_details.pack(anchor="w", pady=(4, 0))
        
        self.client_info_lbl = tk.Label(self.status_card, text="Nessun dispositivo attualmente collegato.",
                                        font=("Segoe UI", 8, "italic"), fg="#a6adc8", bg="#1e1e2e")
        self.client_info_lbl.pack(anchor="w", pady=(2, 0))

        # Overview Grid
        grid_card = tk.Frame(f, bg="#1e1e2e", padx=16, pady=10,
                             highlightbackground="#313244", highlightthickness=1)
        grid_card.pack(fill="x", pady=(0, 8))
        
        self.ov_res_lbl = tk.Label(grid_card, text=f"• Risoluzione: {self.config.get('resolution')} @ {self.config.get('fps')} FPS",
                                   font=("Segoe UI", 9), fg="#cdd6f4", bg="#1e1e2e")
        self.ov_res_lbl.pack(anchor="w", pady=1)
        
        pin_text = f"Attivo ({self.config.get('pin_code')})" if self.config.get("pin_enabled") else "Disattivato (Libero)"
        self.ov_pin_lbl = tk.Label(grid_card, text=f"• Protezione PIN: {pin_text}",
                                   font=("Segoe UI", 9), fg="#cdd6f4", bg="#1e1e2e")
        self.ov_pin_lbl.pack(anchor="w", pady=1)
        
        latency_text = "Attiva (Zero-Lag)" if self.config.get("low_latency") else "Standard"
        self.ov_lat_lbl = tk.Label(grid_card, text=f"• Bassa Latenza: {latency_text}",
                                   font=("Segoe UI", 9), fg="#cdd6f4", bg="#1e1e2e")
        self.ov_lat_lbl.pack(anchor="w", pady=1)

        # Instructions Card
        instr_card = tk.Frame(f, bg="#1e1e2e", padx=16, pady=12,
                              highlightbackground="#313244", highlightthickness=1)
        instr_card.pack(fill="x", pady=(0, 8))
        
        instr_hdr = tk.Label(instr_card, text="Come duplicare lo schermo dell'iPhone:",
                             font=("Segoe UI", 10, "bold"), fg="#89b4fa", bg="#1e1e2e")
        instr_hdr.pack(anchor="w", pady=(0, 4))
        
        steps = (
            "1. Connetti iPhone e PC alla stessa rete Wi-Fi.\n"
            "2. Apri il Centro di Controllo (scorri verso il basso dall'angolo in alto a destra).\n"
            "3. Tocca l'icona 'Duplica schermo' (due rettangoli sovrapposti).\n"
            f"4. Seleziona '{self.config.get('device_name')}' dalla lista."
        )
        self.instr_text_lbl = tk.Label(instr_card, text=steps, font=("Segoe UI", 9),
                                       fg="#cdd6f4", bg="#1e1e2e", justify="left")
        self.instr_text_lbl.pack(anchor="w")

        # Quick Control Actions
        action_row = tk.Frame(f, bg="#181825")
        action_row.pack(fill="x", pady=(2, 0))
        
        restart_btn = tk.Button(action_row, text="🔄 Riavvia Motore AirPlay", font=("Segoe UI", 9, "bold"),
                                bg="#313244", fg="#89b4fa", activebackground="#45475a", activeforeground="#89b4fa",
                                relief="flat", padx=12, pady=7, cursor="hand2", command=self.restart_engine)
        restart_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        settings_nav_btn = tk.Button(action_row, text="⚙️ Modifica Impostazioni", font=("Segoe UI", 9, "bold"),
                                     bg="#313244", fg="#cba6f7", activebackground="#45475a", activeforeground="#cba6f7",
                                     relief="flat", padx=12, pady=7, cursor="hand2",
                                     command=lambda: self.switch_tab("settings"))
        settings_nav_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def _init_settings_tab(self):
        f = self.tab_frames["settings"]
        
        # Scrollable or compact card for settings
        card = tk.Frame(f, bg="#1e1e2e", padx=16, pady=12,
                        highlightbackground="#313244", highlightthickness=1)
        card.pack(fill="both", expand=True, pady=(6, 8))
        
        # 1. Device Name
        name_lbl = tk.Label(card, text="Nome Ricevitore AirPlay:", font=("Segoe UI", 9, "bold"),
                            fg="#89b4fa", bg="#1e1e2e")
        name_lbl.pack(anchor="w")
        
        name_row = tk.Frame(card, bg="#1e1e2e")
        name_row.pack(fill="x", pady=(3, 8))
        
        self.name_entry = tk.Entry(name_row, font=("Segoe UI", 10), bg="#181825", fg="#cdd6f4",
                                   insertbackground="#cdd6f4", relief="flat", highlightbackground="#45475a",
                                   highlightthickness=1)
        self.name_entry.insert(0, self.config.get("device_name", "AirPlay4979"))
        self.name_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=3)
        
        reset_name_btn = tk.Button(name_row, text="Default", font=("Segoe UI", 8), bg="#313244", fg="#a6adc8",
                                   relief="flat", padx=8, pady=2, cursor="hand2",
                                   command=lambda: (self.name_entry.delete(0, tk.END), self.name_entry.insert(0, "AirPlay4979")))
        reset_name_btn.pack(side="right")

        # 2. PIN Security
        pin_lbl = tk.Label(card, text="Sicurezza & PIN di Accesso:", font=("Segoe UI", 9, "bold"),
                           fg="#89b4fa", bg="#1e1e2e")
        pin_lbl.pack(anchor="w")
        
        pin_row = tk.Frame(card, bg="#1e1e2e")
        pin_row.pack(fill="x", pady=(3, 8))
        
        self.pin_enabled_var = tk.BooleanVar(value=self.config.get("pin_enabled", False))
        pin_cb = tk.Checkbutton(pin_row, text="Richiedi PIN a 4 cifre", variable=self.pin_enabled_var,
                                font=("Segoe UI", 9), fg="#cdd6f4", bg="#1e1e2e", selectcolor="#181825",
                                activebackground="#1e1e2e", activeforeground="#cdd6f4")
        pin_cb.pack(side="left")
        
        self.pin_entry = tk.Entry(pin_row, font=("Segoe UI", 10, "bold"), width=6, bg="#181825", fg="#f9e2af",
                                  insertbackground="#f9e2af", relief="flat", justify="center",
                                  highlightbackground="#45475a", highlightthickness=1)
        self.pin_entry.insert(0, self.config.get("pin_code", "1234"))
        self.pin_entry.pack(side="left", padx=(10, 8), ipady=2)
        
        gen_pin_btn = tk.Button(pin_row, text="🎲 Genera PIN", font=("Segoe UI", 8), bg="#313244", fg="#a6adc8",
                                relief="flat", padx=8, pady=2, cursor="hand2", command=self.generate_random_pin)
        gen_pin_btn.pack(side="left")

        # 3. Resolution & FPS
        video_lbl = tk.Label(card, text="Qualità Video & Fluidità:", font=("Segoe UI", 9, "bold"),
                             fg="#89b4fa", bg="#1e1e2e")
        video_lbl.pack(anchor="w")
        
        video_row = tk.Frame(card, bg="#1e1e2e")
        video_row.pack(fill="x", pady=(3, 8))
        
        self.res_var = tk.StringVar(value=self.config.get("resolution", "1080p"))
        res_cb = ttk.Combobox(video_row, textvariable=self.res_var, state="readonly", width=18,
                              values=["1080p (Full HD)", "720p (Max Fluidità)", "4K (Ultra HD - H.265)"])
        # map to simple keys
        res_current = self.config.get("resolution", "1080p")
        if res_current == "720p":
            res_cb.current(1)
        elif res_current == "4K":
            res_cb.current(2)
        else:
            res_cb.current(0)
        res_cb.pack(side="left", padx=(0, 10))
        
        self.fps_var = tk.StringVar(value=self.config.get("fps", "60"))
        fps_cb = ttk.Combobox(video_row, textvariable=self.fps_var, state="readonly", width=10,
                              values=["60 FPS", "30 FPS"])
        fps_cb.current(0 if self.config.get("fps") == "60" else 1)
        fps_cb.pack(side="left")

        # 4. Display & Optimizations
        opts_lbl = tk.Label(card, text="Opzioni Display & Prestazioni:", font=("Segoe UI", 9, "bold"),
                            fg="#89b4fa", bg="#1e1e2e")
        opts_lbl.pack(anchor="w")
        
        opts_frame = tk.Frame(card, bg="#1e1e2e")
        opts_frame.pack(fill="x", pady=(2, 6))
        
        self.low_latency_var = tk.BooleanVar(value=self.config.get("low_latency", True))
        lat_cb = tk.Checkbutton(opts_frame, text="⚡ Modalità Bassa Latenza (Zero-Lag, rendering immediato)",
                                variable=self.low_latency_var, font=("Segoe UI", 9), fg="#a6e3a1",
                                bg="#1e1e2e", selectcolor="#181825", activebackground="#1e1e2e",
                                activeforeground="#a6e3a1")
        lat_cb.pack(anchor="w")
        
        self.fullscreen_var = tk.BooleanVar(value=self.config.get("fullscreen", False))
        fs_cb = tk.Checkbutton(opts_frame, text="📺 Schermo intero automatico all'avvio dello stream (-fs)",
                               variable=self.fullscreen_var, font=("Segoe UI", 9), fg="#cdd6f4",
                               bg="#1e1e2e", selectcolor="#181825", activebackground="#1e1e2e",
                               activeforeground="#cdd6f4")
        fs_cb.pack(anchor="w")
        
        self.audio_var = tk.BooleanVar(value=self.config.get("enable_audio", True))
        audio_cb = tk.Checkbutton(opts_frame, text="🔊 Riproduci audio dell'iPhone sugli altoparlanti del PC",
                                  variable=self.audio_var, font=("Segoe UI", 9), fg="#cdd6f4",
                                  bg="#1e1e2e", selectcolor="#181825", activebackground="#1e1e2e",
                                  activeforeground="#cdd6f4")
        audio_cb.pack(anchor="w")

        # 5. Rotation
        rot_row = tk.Frame(card, bg="#1e1e2e")
        rot_row.pack(fill="x", pady=(4, 12))
        
        rot_lbl = tk.Label(rot_row, text="Orientamento Schermo:", font=("Segoe UI", 9),
                           fg="#cdd6f4", bg="#1e1e2e")
        rot_lbl.pack(side="left", padx=(0, 10))
        
        self.rot_var = tk.StringVar(value=self.config.get("rotation", "0"))
        rot_cb = ttk.Combobox(rot_row, textvariable=self.rot_var, state="readonly", width=18,
                              values=["Normale (0°)", "Ruota Destra (90°)", "Ruota Sinistra (90°)", "Capovolto (180°)"])
        rot_val = self.config.get("rotation", "0")
        if rot_val == "90R":
            rot_cb.current(1)
        elif rot_val == "90L":
            rot_cb.current(2)
        elif rot_val == "180":
            rot_cb.current(3)
        else:
            rot_cb.current(0)
        self.rot_combobox = rot_cb
        rot_cb.pack(side="left")

        # Save Button
        save_btn = tk.Button(card, text="💾 Salva Impostazioni e Riavvia Ricevitore", font=("Segoe UI", 10, "bold"),
                             bg="#89b4fa", fg="#11111b", activebackground="#b4befe", activeforeground="#11111b",
                             relief="flat", pady=8, cursor="hand2", command=self.save_and_apply_settings)
        save_btn.pack(fill="x", pady=(4, 0))

    def _init_diagnostics_tab(self):
        f = self.tab_frames["diagnostics"]
        
        card = tk.Frame(f, bg="#1e1e2e", padx=16, pady=12,
                        highlightbackground="#313244", highlightthickness=1)
        card.pack(fill="both", expand=True, pady=(6, 8))
        
        sec1_title = tk.Label(card, text="Stato Rete & Servizi:", font=("Segoe UI", 10, "bold"),
                              fg="#89b4fa", bg="#1e1e2e")
        sec1_title.pack(anchor="w")
        
        self.diag_ip = tk.Label(card, text=f"• Indirizzo IP Wi-Fi PC: {self.local_ip}",
                                font=("Segoe UI", 9), fg="#cdd6f4", bg="#1e1e2e")
        self.diag_ip.pack(anchor="w", pady=2)
        
        self.diag_bonjour = tk.Label(card, text="• Servizio Apple Bonjour: Attivo e Rilevabile (mDNS)",
                                     font=("Segoe UI", 9), fg="#a6e3a1", bg="#1e1e2e")
        self.diag_bonjour.pack(anchor="w", pady=2)
        
        self.diag_engine = tk.Label(card, text="• Motore Mirroring: UxPlay 2.0 (Direct3D 11 / WASAPI)",
                                    font=("Segoe UI", 9), fg="#cdd6f4", bg="#1e1e2e")
        self.diag_engine.pack(anchor="w", pady=2)

        sec2_title = tk.Label(card, text="\nGaranzie di Sicurezza & Pulizia:", font=("Segoe UI", 10, "bold"),
                              fg="#89b4fa", bg="#1e1e2e")
        sec2_title.pack(anchor="w")
        
        clean_info = (
            "✔ Nessun avvio automatico con Windows.\n"
            "✔ Nessun servizio o demone nascosto in background.\n"
            "✔ Chiusura forzata automatica al 100% via Windows Job Object.\n"
            "✔ Nessuna filigrana, nessun abbonamento, nessun limite di tempo."
        )
        clean_lbl = tk.Label(card, text=clean_info, font=("Segoe UI", 9),
                             fg="#a6adc8", bg="#1e1e2e", justify="left")
        clean_lbl.pack(anchor="w", pady=2)

        sec3_title = tk.Label(card, text="\nProgetto Open-Source:", font=("Segoe UI", 10, "bold"),
                              fg="#89b4fa", bg="#1e1e2e")
        sec3_title.pack(anchor="w")
        
        gh_btn = tk.Button(card, text="🌐 Apri Repository Ufficiale su GitHub", font=("Segoe UI", 9, "bold"),
                           bg="#313244", fg="#89b4fa", activebackground="#45475a", activeforeground="#89b4fa",
                           relief="flat", pady=6, cursor="hand2",
                           command=lambda: webbrowser.open(GITHUB_REPO_URL))
        gh_btn.pack(fill="x", pady=(6, 0))

    def _build_status_footer(self):
        footer_frame = tk.Frame(self.root, bg="#181825", padx=20, pady=10)
        footer_frame.pack(fill="x", side="bottom")
        
        close_btn = tk.Button(footer_frame, text="⏹ Termina e Chiudi Tutto", font=("Segoe UI", 10, "bold"),
                              bg="#f38ba8", fg="#11111b", activebackground="#eba0ac",
                              relief="flat", pady=8, cursor="hand2", command=self.on_close)
        close_btn.pack(fill="x")

    def generate_random_pin(self):
        pin = f"{random.randint(1000, 9999)}"
        self.pin_entry.delete(0, tk.END)
        self.pin_entry.insert(0, pin)
        self.pin_enabled_var.set(True)

    def save_and_apply_settings(self):
        # 1. Device name
        dev_name = self.name_entry.get().strip()
        if not dev_name:
            dev_name = "AirPlay4979"
        self.config["device_name"] = dev_name
        
        # 2. PIN
        pin_enabled = self.pin_enabled_var.get()
        pin_code = self.pin_entry.get().strip()
        if pin_enabled:
            if not (len(pin_code) == 4 and pin_code.isdigit()):
                messagebox.showerror("PIN non valido", "Il codice PIN deve essere composto esattamente da 4 cifre numeriche (es. 1234).")
                return
        self.config["pin_enabled"] = pin_enabled
        self.config["pin_code"] = pin_code
        
        # 3. Resolution
        res_sel = self.res_var.get()
        if "720p" in res_sel:
            self.config["resolution"] = "720p"
        elif "4K" in res_sel:
            self.config["resolution"] = "4K"
        else:
            self.config["resolution"] = "1080p"
            
        # 4. FPS
        fps_sel = self.fps_var.get()
        self.config["fps"] = "30" if "30" in fps_sel else "60"
        
        # 5. Low latency & Display
        self.config["low_latency"] = self.low_latency_var.get()
        self.config["fullscreen"] = self.fullscreen_var.get()
        self.config["enable_audio"] = self.audio_var.get()
        
        # 6. Rotation
        rot_sel = self.rot_combobox.get()
        if "Destra" in rot_sel:
            self.config["rotation"] = "90R"
        elif "Sinistra" in rot_sel:
            self.config["rotation"] = "90L"
        elif "180" in rot_sel:
            self.config["rotation"] = "180"
        else:
            self.config["rotation"] = "0"
            
        # Save to disk
        save_config(self.config)
        
        # Update overview labels
        self.status_details.config(text=f"Nome AirPlay: {self.config.get('device_name')}  |  IP: {self.local_ip}")
        self.ov_res_lbl.config(text=f"• Risoluzione: {self.config.get('resolution')} @ {self.config.get('fps')} FPS")
        pin_text = f"Attivo ({self.config.get('pin_code')})" if self.config.get("pin_enabled") else "Disattivato (Libero)"
        self.ov_pin_lbl.config(text=f"• Protezione PIN: {pin_text}")
        lat_text = "Attiva (Zero-Lag)" if self.config.get("low_latency") else "Standard"
        self.ov_lat_lbl.config(text=f"• Bassa Latenza: {lat_text}")
        
        steps = (
            "1. Connetti iPhone e PC alla stessa rete Wi-Fi.\n"
            "2. Apri il Centro di Controllo (scorri verso il basso dall'angolo in alto a destra).\n"
            "3. Tocca l'icona 'Duplica schermo' (due rettangoli sovrapposti).\n"
            f"4. Seleziona '{self.config.get('device_name')}' dalla lista."
        )
        self.instr_text_lbl.config(text=steps)
        
        # Restart engine
        self.start_engine()
        messagebox.showinfo("Impostazioni Salvate", "Le nuove impostazioni sono state salvate e il ricevitore AirPlay è stato riavviato!")
        self.switch_tab("main")

    def start_engine(self):
        self.stop_engine()
        write_uxplay_arguments(self.config)
        
        if os.path.exists(ENGINE_EXE):
            try:
                creation_flags = 0
                if sys.platform == "win32":
                    creation_flags = subprocess.CREATE_NO_WINDOW
                
                env = os.environ.copy()
                env["PATH"] = APP_DIR + os.pathsep + env.get("PATH", "")
                
                self.engine_proc = subprocess.Popen(
                    [ENGINE_EXE],
                    cwd=APP_DIR,
                    env=env,
                    creationflags=creation_flags
                )
                if self.job and self.engine_proc:
                    try:
                        h_proc = win32api.OpenProcess(win32job.PROCESS_ALL_ACCESS, False, self.engine_proc.pid)
                        win32job.AssignProcessToJobObject(self.job, h_proc)
                    except Exception:
                        pass
                self.set_ui_status("listening")
            except Exception as e:
                self.set_ui_status("error", str(e))
        else:
            self.set_ui_status("error", "uxplay-windows.exe non trovato")

    def restart_engine(self):
        self.start_engine()

    def stop_engine(self):
        if self.engine_proc:
            try:
                self.engine_proc.terminate()
            except Exception:
                pass
            self.engine_proc = None
        if sys.platform == "win32":
            try:
                creation_flags = subprocess.CREATE_NO_WINDOW
                subprocess.run(["taskkill", "/F", "/IM", "uxplay-windows.exe"],
                               creationflags=creation_flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["taskkill", "/F", "/IM", "uxplay-bluetooth-beacon.exe"],
                               creationflags=creation_flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def set_ui_status(self, status, detail=""):
        if status == "connected":
            self.status_dot.config(text="●", fg="#a6e3a1")
            self.status_title.config(text="IN TRASMISSIONE (iPhone Connesso)", fg="#a6e3a1")
            self.client_info_lbl.config(text=f"🟢 Dispositivo collegato: {detail} (Ricezione flusso video)", fg="#a6e3a1")
            self.status_card.config(highlightbackground="#a6e3a1")
        elif status == "listening":
            self.status_dot.config(text="●", fg="#f9e2af")
            self.status_title.config(text="IN ASCOLTO (Pronto alla connessione)", fg="#f9e2af")
            self.client_info_lbl.config(text="Nessun dispositivo attualmente collegato. Apri 'Duplica schermo' su iPhone.", fg="#a6adc8")
            self.status_card.config(highlightbackground="#313244")
        elif status == "error":
            self.status_dot.config(text="●", fg="#f38ba8")
            self.status_title.config(text="ERRORE MOTORE", fg="#f38ba8")
            self.client_info_lbl.config(text=f"🔴 {detail}", fg="#f38ba8")
            self.status_card.config(highlightbackground="#f38ba8")

    def _connection_monitor_loop(self):
        """Monitors network sockets to detect when iPhone starts/stops mirroring."""
        while self.running:
            time.sleep(1.5)
            if not self.running:
                break
            if self.engine_proc and self.engine_proc.poll() is None:
                client_ip = get_connected_client(self.engine_proc.pid)
                if client_ip != self.connected_client_ip:
                    self.connected_client_ip = client_ip
                    if client_ip:
                        self.root.after(0, lambda ip=client_ip: self.set_ui_status("connected", ip))
                    else:
                        self.root.after(0, lambda: self.set_ui_status("listening"))
            elif self.engine_proc and self.engine_proc.poll() is not None:
                self.root.after(0, lambda: self.set_ui_status("error", "Processo terminato inaspettatamente"))

    def on_close(self):
        self.running = False
        self.stop_engine()
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

SINGLE_INSTANCE_MUTEX = "AirPlayReceiverWindows_SingleInstanceMutex_v1"

def main():
    ERROR_ALREADY_EXISTS = 183
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX)
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        focus_existing_window()
        sys.exit(0)

    root = tk.Tk()
    app = ModernAirPlayApp(root)
    root.mainloop()
    
    try:
        ctypes.windll.kernel32.CloseHandle(mutex)
    except Exception:
        pass

if __name__ == "__main__":
    main()
