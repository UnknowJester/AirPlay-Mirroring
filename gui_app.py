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
from ctypes import wintypes
from PIL import Image, ImageTk, ImageDraw
import psutil
import win32job
import win32api

# Base directory resolution
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

ENGINE_EXE = os.path.join(APP_DIR, "uxplay-windows.exe")
ICON_PATH = os.path.join(APP_DIR, "resources", "icon.ico")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
GITHUB_REPO_URL = "https://github.com/UnknowJester/AirPlay-Mirroring"
SINGLE_INSTANCE_MUTEX = "AirPlayReceiverWindows_SingleInstanceMutex_v1"

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SetWindowLongPtrW = getattr(user32, 'SetWindowLongPtrW', user32.SetWindowLongW)
SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
SetWindowLongPtrW.restype = ctypes.c_ssize_t

WINEVENTPROC = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.HWND,
    wintypes.LONG,
    wintypes.LONG,
    wintypes.DWORD,
    wintypes.DWORD
)

DEFAULT_CONFIG = {
    "device_name": "Pc-dav",
    "pin_enabled": False,
    "pin_code": "1234",
    "resolution": "1080p",
    "fps": "60",
    "low_latency": True,
    "audio_latency": "0.1",
    "fullscreen_auto": False,
    "always_on_top": False,
    "rotation": "0",
    "enable_audio": True,
    "color_range_srgb": True,
    "theme": "light"
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

def get_network_info():
    """Dynamically detects active network adapter and local IP."""
    ip = "127.0.0.1"
    net_type = "Wi-Fi"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        
        for iface_name, snics in psutil.net_if_addrs().items():
            for snic in snics:
                if snic.address == ip:
                    net_type = iface_name
                    break
    except Exception:
        pass
    return net_type, ip

def focus_existing_window():
    try:
        hwnd = user32.FindWindowW(None, "AirMirroring - AirPlay Receiver")
        if hwnd:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass

def write_uxplay_arguments(config):
    """Generates the command arguments for UxPlay and updates all sync locations."""
    args = []
    
    # Device name (sanitize spaces to '-' and strip invalid chars for mDNS)
    raw_name = str(config.get("device_name", "Pc-dav")).strip()
    clean_name = raw_name.replace(" ", "-").replace('"', '').replace("'", "")
    clean_name = "".join(c for c in clean_name if c.isalnum() or c in ("-", "_")).strip()
    if not clean_name:
        clean_name = "Pc-dav"
    args.append(f"-n {clean_name}")
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
    elif res == "1440p":
        args.append(f"-s 2560x1440@{fps}")
    elif res == "4K":
        args.append(f"-s 3840x2160@{fps}")
        args.append("-h265")
    else:  # 1080p default
        args.append(f"-s 1920x1080@{fps}")
        
    args.append(f"-fps {fps}")
    
    # Low latency optimizations (Zero-Lag)
    if config.get("low_latency", True):
        args.append("-vsync no")
        
    # Audio latency buffer
    alat = config.get("audio_latency", "0.1")
    args.append(f"-al {alat}")
        
    # Color range
    if config.get("color_range_srgb", True):
        args.append("-srgb")
        
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
        
    # Natural audio profile
    args.append("-taper")
    
    # Clean termination flag
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

def find_window_by_pid(pid):
    """Finds visible rendering window belonging to the engine process."""
    hwnds = []
    def enum_cb(hwnd, lparam):
        if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
            w_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(w_pid))
            if w_pid.value == pid:
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w > 80 and h > 80:
                    hwnds.append(hwnd)
        return True
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return hwnds

def get_connected_client(pid):
    """Detects active remote TCP connection to the UxPlay process."""
    if not pid:
        return None
    try:
        for conn in psutil.net_connections(kind='tcp'):
            if conn.pid == pid and conn.status == 'ESTABLISHED':
                if conn.raddr and conn.raddr.ip not in ('127.0.0.1', '::1', '0.0.0.0'):
                    return conn.raddr.ip
    except Exception:
        pass
    return None

class AirMirroringApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AirMirroring - AirPlay Receiver")
        self.root.geometry("980x620")
        self.root.minsize(860, 540)
        self.root.configure(bg="#eef2ff")
        
        if os.path.exists(ICON_PATH):
            try:
                self.root.iconbitmap(ICON_PATH)
            except Exception:
                pass
                
        self.config = load_config()
        self.engine_proc = None
        self.job = None
        self.running = True
        self.connected_client_ip = None
        self.embedded_video_hwnd = None
        self.win_event_hook = None
        self.win_event_proc = None
        self.is_fullscreen = False
        self.dot_phase = 0
        
        self.net_type, self.local_ip = get_network_info()
        
        # Apply always-on-top preference
        if self.config.get("always_on_top", False):
            self.root.attributes("-topmost", True)
            
        # Windows Job Object configuration for 100% kill guarantee on close
        try:
            self.job = win32job.CreateJobObject(None, "")
            info = win32job.QueryInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation)
            info['BasicLimitInformation']['LimitFlags'] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation, info)
        except Exception:
            self.job = None

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.root.bind("<f>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Escape>", lambda e: self.exit_fullscreen())
        
        self._build_top_bar()
        self._build_main_views()
        self._build_footer()
        
        # Start engine
        self.start_engine()
        
        # Start animations and monitor loops
        self._animate_dots_loop()
        self.monitor_thread = threading.Thread(target=self._connection_monitor_loop, daemon=True)
        self.monitor_thread.start()

    def _build_top_bar(self):
        self.top_bar = tk.Frame(self.root, bg="#f1f5f9", height=42, padx=18)
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)
        
        # Left brand title
        brand_frame = tk.Frame(self.top_bar, bg="#f1f5f9")
        brand_frame.pack(side="left", fill="y")
        
        brand_lbl = tk.Label(brand_frame, text="AirMirroring", font=("Segoe UI", 12, "bold"),
                             fg="#1e293b", bg="#f1f5f9")
        brand_lbl.pack(side="left", pady=8)
        
        ver_badge = tk.Label(brand_frame, text="Pro", font=("Segoe UI", 8, "bold"),
                             fg="#3b82f6", bg="#dbeafe", padx=5, pady=1)
        ver_badge.pack(side="left", padx=(6, 0), pady=10)
        
        # Right action buttons
        actions_frame = tk.Frame(self.top_bar, bg="#f1f5f9")
        actions_frame.pack(side="right", fill="y")
        
        self.carplay_btn = tk.Button(
            actions_frame, text="* Wireless CarPlay", font=("Segoe UI", 9),
            bg="#ffffff", fg="#475569", relief="flat", bd=0, padx=12, pady=3,
            cursor="hand2", highlightbackground="#e2e8f0", highlightthickness=1,
            command=self.show_carplay_dialog
        )
        self.carplay_btn.pack(side="left", padx=(0, 8), pady=6)
        
        self.restart_btn = tk.Button(
            actions_frame, text="⟳ Restart", font=("Segoe UI", 9, "bold"),
            bg="#ffffff", fg="#3b82f6", relief="flat", bd=0, padx=12, pady=3,
            cursor="hand2", highlightbackground="#e2e8f0", highlightthickness=1,
            command=self.restart_engine
        )
        self.restart_btn.pack(side="left", pady=6)

    def _build_main_views(self):
        # Master container for central screen
        self.content_container = tk.Frame(self.root, bg="#eef2ff")
        self.content_container.pack(fill="both", expand=True)
        
        # View 1: Standby Frame (replicates uploaded screenshot)
        self.standby_frame = tk.Frame(self.content_container, bg="#eef2ff")
        self.standby_frame.pack(fill="both", expand=True)
        
        # Background gradient canvas
        self.bg_canvas = tk.Canvas(self.standby_frame, bg="#eef2ff", highlightthickness=0)
        self.bg_canvas.pack(fill="both", expand=True)
        self.bg_canvas.bind("<Configure>", self._draw_gradient_background)
        
        # Center two-column layout wrapper inside canvas
        self.center_wrapper = tk.Frame(self.bg_canvas, bg="#ffffff")
        self.canvas_window_id = self.bg_canvas.create_window(0, 0, window=self.center_wrapper, anchor="center")
        self.bg_canvas.bind("<Configure>", self._center_standby_layout, add="+")
        
        self._build_standby_columns()

        # View 2: Video Container (holds embedded UxPlay streaming window)
        self.video_container = tk.Frame(self.content_container, bg="#000000")
        self.video_container.bind("<Configure>", self._on_video_container_resize)
        self.video_container.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())

    def _draw_gradient_background(self, event):
        w = max(event.width, 200)
        h = max(event.height, 200)
        
        # Generate soft pastel gradient image (lavender to soft sky blue)
        try:
            base = Image.new('RGB', (w, h), '#eef2ff')
            top = Image.new('RGB', (w, h), '#ede9fe')
            mask = Image.new('L', (w, h))
            mask_data = []
            for y in range(h):
                row_val = int(255 * (1.0 - (y / h * 0.7)))
                mask_data.extend([row_val] * w)
            mask.putdata(mask_data)
            base.paste(top, (0, 0), mask)
            
            self.gradient_img = ImageTk.PhotoImage(base)
            self.bg_canvas.delete("gradient_bg")
            self.bg_canvas.create_image(0, 0, image=self.gradient_img, anchor="nw", tags="gradient_bg")
            self.bg_canvas.tag_lower("gradient_bg")
        except Exception:
            pass

    def _center_standby_layout(self, event):
        self.bg_canvas.coords(self.canvas_window_id, event.width // 2, event.height // 2)

    def _build_standby_columns(self):
        self.center_wrapper.configure(bg="#ffffff")
        
        # Central modern card (clean, centered, zero clutter)
        card = tk.Frame(self.center_wrapper, bg="#ffffff", padx=46, pady=24,
                        highlightbackground="#cbd5e1", highlightthickness=1)
        card.pack()

        # Monitor Icon Canvas
        self.monitor_canvas = tk.Canvas(card, width=170, height=115, bg="#ffffff", highlightthickness=0)
        self.monitor_canvas.pack(pady=(4, 6))
        self._draw_airplay_monitor(self.monitor_canvas)

        # Device Name Display (e.g. AirMirroring 【Pc-dav】)
        name = self.config.get("device_name", "Pc-dav")
        self.device_title_lbl = tk.Label(
            card,
            text=f"AirMirroring 【{name}】",
            font=("Segoe UI", 17, "bold"),
            fg="#0f172a",
            bg="#ffffff"
        )
        self.device_title_lbl.pack(pady=(2, 4))

        # Security PIN Badge (if active)
        self.pin_display_lbl = tk.Label(card, text="", font=("Segoe UI", 10, "bold"),
                                        fg="#b45309", bg="#fef3c7", padx=12, pady=3)
        self._update_pin_display()

        # Animated 4 Dots
        self.dots_canvas = tk.Canvas(card, width=120, height=30, bg="#ffffff", highlightthickness=0)
        self.dots_canvas.pack(pady=(4, 2))

        self.status_sub_lbl = tk.Label(card, text="In attesa di duplicazione schermo...",
                                       font=("Segoe UI", 10), fg="#64748b", bg="#ffffff")
        self.status_sub_lbl.pack(pady=(0, 14))

        # Quick connection 3-step guide frame (replaces store and QR elements)
        guide_box = tk.Frame(card, bg="#f8fafc", padx=22, pady=12,
                             highlightbackground="#e2e8f0", highlightthickness=1)
        guide_box.pack(fill="x")

        guide_title = tk.Label(guide_box, text="Come connettere il tuo dispositivo:",
                               font=("Segoe UI", 9, "bold"), fg="#334155", bg="#f8fafc")
        guide_title.pack(anchor="w", pady=(0, 6))

        s1_frame = tk.Frame(guide_box, bg="#f8fafc")
        s1_frame.pack(fill="x", pady=2)
        tk.Label(s1_frame, text="📶  Passo 1:", font=("Segoe UI", 9, "bold"), fg="#2563eb", bg="#f8fafc").pack(side="left")
        s1_text = f" Connetti iPhone e PC alla stessa rete Wi-Fi ({self.net_type})"
        tk.Label(s1_frame, text=s1_text, font=("Segoe UI", 9), fg="#475569", bg="#f8fafc").pack(side="left")

        s2_frame = tk.Frame(guide_box, bg="#f8fafc")
        s2_frame.pack(fill="x", pady=2)
        tk.Label(s2_frame, text="👆  Passo 2:", font=("Segoe UI", 9, "bold"), fg="#2563eb", bg="#f8fafc").pack(side="left")
        tk.Label(s2_frame, text=" Apri Centro di Controllo (scorri dall'angolo in alto a destra)",
                 font=("Segoe UI", 9), fg="#475569", bg="#f8fafc").pack(side="left")

        s3_frame = tk.Frame(guide_box, bg="#f8fafc")
        s3_frame.pack(fill="x", pady=2)
        tk.Label(s3_frame, text="📲  Passo 3:", font=("Segoe UI", 9, "bold"), fg="#2563eb", bg="#f8fafc").pack(side="left")
        self.guide_step3_lbl = tk.Label(s3_frame, text=f' Tocca "Duplica schermo" e seleziona "{name}"',
                                        font=("Segoe UI", 9, "bold"), fg="#1e293b", bg="#f8fafc")
        self.guide_step3_lbl.pack(side="left")

    def _draw_airplay_monitor(self, c):
        c.delete("all")
        # Monitor bezel
        c.create_rectangle(20, 15, 150, 95, outline="#1e293b", width=6, fill="#ffffff")
        # Monitor stand base
        c.create_rectangle(65, 95, 105, 106, outline="#1e293b", fill="#1e293b")
        c.create_line(45, 106, 125, 106, fill="#1e293b", width=6)
        # Upward AirPlay triangle inside monitor
        c.create_polygon(65, 85, 105, 85, 85, 45, fill="#1e293b", outline="#1e293b")

    def _update_pin_display(self):
        if self.config.get("pin_enabled", False):
            self.pin_display_lbl.config(text=f"🔒 Codice PIN Richiesto: [ {self.config.get('pin_code', '1234')} ]")
            self.pin_display_lbl.pack(pady=(0, 6))
        else:
            self.pin_display_lbl.pack_forget()

    def _update_device_name_display(self):
        name = self.config.get("device_name", "Pc-dav")
        if hasattr(self, "device_title_lbl"):
            self.device_title_lbl.config(text=f"AirMirroring 【{name}】")
        if hasattr(self, "guide_step3_lbl"):
            self.guide_step3_lbl.config(text=f' Tocca "Duplica schermo" e seleziona "{name}"')

    def _animate_dots_loop(self):
        if not self.running:
            return
        colors = ["#06b6d4", "#3b82f6", "#8b5cf6", "#d946ef"]
        try:
            self.dots_canvas.delete("dots")
            spacing = 24
            start_x = 24
            y = 15
            for i in range(4):
                idx = (i + self.dot_phase) % 4
                c = colors[idx]
                r = 6 if i == self.dot_phase % 4 else 5
                x = start_x + i * spacing
                self.dots_canvas.create_oval(x - r, y - r, x + r, y + r, fill=c, outline=c, tags="dots")
            self.dot_phase = (self.dot_phase + 1) % 4
        except Exception:
            return
            
        if self.running:
            try:
                self.root.after(350, self._animate_dots_loop)
            except Exception:
                pass

    def _build_footer(self):
        self.footer = tk.Frame(self.root, bg="#f1f5f9", height=48, padx=18)
        self.footer.pack(fill="x", side="bottom")
        self.footer.pack_propagate(False)

        # Left links
        left_links = tk.Frame(self.footer, bg="#f1f5f9")
        left_links.pack(side="left", fill="y", pady=6)

        link1 = tk.Label(left_links, text="Can't find this receiver in the screen mirroring list?",
                         font=("Segoe UI", 8, "underline"), fg="#2563eb", bg="#f1f5f9", cursor="hand2")
        link1.pack(anchor="w")
        link1.bind("<Button-1>", lambda e: self.show_troubleshooting_dialog())

        link2 = tk.Label(left_links, text="Failed to connect to this receiver?",
                         font=("Segoe UI", 8, "underline"), fg="#2563eb", bg="#f1f5f9", cursor="hand2")
        link2.pack(anchor="w")
        link2.bind("<Button-1>", lambda e: self.show_network_diagnosis())

        # Center Floating Pill Dock
        center_pill = tk.Frame(self.footer, bg="#ffffff", padx=16, pady=4,
                               highlightbackground="#e2e8f0", highlightthickness=1)
        center_pill.pack(side="left", expand=True)

        pill_icon = tk.Label(center_pill, text="📲", font=("Segoe UI", 11), bg="white")
        pill_icon.pack(side="left", padx=(0, 6))

        self.pill_title = tk.Label(center_pill, text="AirMirroring", font=("Segoe UI", 9, "bold"),
                                   fg="#1e293b", bg="white")
        self.pill_title.pack(side="left")

        # Right status & settings buttons
        right_info = tk.Frame(self.footer, bg="#f1f5f9")
        right_info.pack(side="right", fill="y", pady=8)

        net_text = f"Network:{self.net_type}   IP:{self.local_ip}"
        self.net_lbl = tk.Label(right_info, text=net_text, font=("Consolas", 8),
                                fg="#2563eb", bg="#f1f5f9")
        self.net_lbl.pack(side="left", padx=(0, 14))

        fs_btn = tk.Button(right_info, text="⛶", font=("Segoe UI", 12),
                           bg="#ffffff", fg="#475569", relief="flat", bd=0, padx=8, pady=0,
                           cursor="hand2", highlightbackground="#e2e8f0", highlightthickness=1,
                           command=self.toggle_fullscreen)
        fs_btn.pack(side="left", padx=(0, 6))

        settings_btn = tk.Button(right_info, text="⚙", font=("Segoe UI", 12),
                                 bg="#ffffff", fg="#475569", relief="flat", bd=0, padx=8, pady=0,
                                 cursor="hand2", highlightbackground="#e2e8f0", highlightthickness=1,
                                 command=self.open_settings_dialog)
        settings_btn.pack(side="left")

    def _on_video_container_resize(self, event):
        """Resizes the embedded Direct3D child window when parent container resizes."""
        if self.embedded_video_hwnd and user32.IsWindow(self.embedded_video_hwnd):
            user32.MoveWindow(self.embedded_video_hwnd, 0, 0, event.width, event.height, True)

    def dock_video_window(self, child_hwnd):
        """Immediately docks UxPlay render window into container with zero flicker."""
        try:
            if not user32.IsWindow(child_hwnd):
                return

            self.embedded_video_hwnd = child_hwnd

            # 1. Switch UI views to video container
            self.standby_frame.pack_forget()
            self.video_container.pack(fill="both", expand=True)
            self.root.update_idletasks()

            # 2. Dock child window into video_container
            container_hwnd = self.video_container.winfo_id()
            user32.SetParent(child_hwnd, container_hwnd)

            # 3. Strip window borders, captions and popup styles
            GWL_STYLE = -16
            WS_CAPTION = 0x00C00000
            WS_THICKFRAME = 0x00040000
            WS_BORDER = 0x00800000
            WS_POPUP = 1 << 31
            WS_CHILD = 1 << 30
            WS_VISIBLE = 1 << 28

            style = user32.GetWindowLongW(child_hwnd, GWL_STYLE)
            style = (style & ~(WS_CAPTION | WS_THICKFRAME | WS_BORDER | WS_POPUP)) | WS_CHILD | WS_VISIBLE
            val = ctypes.c_long(style).value
            SetWindowLongPtrW(child_hwnd, GWL_STYLE, val)

            # 4. Position and size to fit container exactly
            w = max(self.video_container.winfo_width(), 100)
            h = max(self.video_container.winfo_height(), 100)
            user32.MoveWindow(child_hwnd, 0, 0, w, h, True)

            # 5. Show inside the container
            user32.ShowWindow(child_hwnd, 5)  # SW_SHOW

            # 6. Update connection status
            client_ip = get_connected_client(self.engine_proc.pid) if self.engine_proc else None
            self.connected_client_ip = client_ip or "iPhone"
            self.pill_title.config(text=f"Streaming: {self.connected_client_ip}", fg="#16a34a")
            self.status_sub_lbl.config(text=f"🟢 iPhone Connesso ({self.connected_client_ip})", fg="#16a34a")

            if self.config.get("fullscreen_auto", False) and not self.is_fullscreen:
                self.toggle_fullscreen()
        except Exception:
            pass

    def switch_to_video_mode(self, client_ip):
        """Switches to video mode (used for compatibility or manual trigger)."""
        self.connected_client_ip = client_ip
        self.standby_frame.pack_forget()
        self.video_container.pack(fill="both", expand=True)
        self.pill_title.config(text=f"Streaming: {client_ip}", fg="#16a34a")
        self.status_sub_lbl.config(text=f"🟢 iPhone Connesso ({client_ip})", fg="#16a34a")
        if self.config.get("fullscreen_auto", False) and not self.is_fullscreen:
            self.toggle_fullscreen()

    def switch_to_standby_mode(self):
        """Switches back to standby screen and resets UI state."""
        try:
            self.embedded_video_hwnd = None
            self.connected_client_ip = None
            self.video_container.pack_forget()
            self.standby_frame.pack(fill="both", expand=True)
            self.pill_title.config(text="AirMirroring", fg="#1e293b")
            self.status_sub_lbl.config(text="In attesa di duplicazione schermo...", fg="#64748b")
            if self.is_fullscreen and self.config.get("fullscreen_auto", False):
                self.exit_fullscreen()
        except Exception:
            pass

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)
        if self.is_fullscreen:
            self.top_bar.pack_forget()
            self.footer.pack_forget()
        else:
            self.top_bar.pack(fill="x", side="top", before=self.content_container)
            self.footer.pack(fill="x", side="bottom")

    def exit_fullscreen(self):
        if self.is_fullscreen:
            self.toggle_fullscreen()

    def _on_win_event(self, hHook, event, hwnd, idObject, idChild, dwThread, dwTime):
        """Zero-flicker native hook callback catching child windows before display."""
        try:
            if idObject != 0 or idChild != 0 or not hwnd:
                return
            if not self.engine_proc or not self.running:
                return

            w_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(w_pid))
            if w_pid.value != self.engine_proc.pid:
                return

            try:
                if hwnd == self.root.winfo_id():
                    return
            except Exception:
                pass

            GWL_STYLE = -16
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            if style & (1 << 30):  # WS_CHILD
                return

            cls_buf = ctypes.create_unicode_buffer(128)
            user32.GetClassNameW(hwnd, cls_buf, 128)
            cls_name = cls_buf.value
            if any(x in cls_name for x in ("Observer", "TrayIcon", "IME", "Message", "Dummy", "Clipboard", "Internal", "Ole")):
                return

            if event == 0x8002:  # EVENT_OBJECT_SHOW
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w > 80 and h > 80:
                    # ZERO FLICKER GUARANTEE: Instantly hide window before desktop paints it
                    user32.ShowWindow(hwnd, 0)
                    if self.embedded_video_hwnd != hwnd:
                        self.dock_video_window(hwnd)

            elif event == 0x8001:  # EVENT_OBJECT_DESTROY
                if self.embedded_video_hwnd == hwnd:
                    self.switch_to_standby_mode()
        except Exception:
            pass

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

                # Install zero-flicker native WinEvent hook
                if sys.platform == "win32" and self.engine_proc and self.engine_proc.pid:
                    self.win_event_proc = WINEVENTPROC(self._on_win_event)
                    # 0x8001 = EVENT_OBJECT_DESTROY, 0x8002 = EVENT_OBJECT_SHOW
                    self.win_event_hook = user32.SetWinEventHook(
                        0x8001, 0x8002, None, self.win_event_proc, self.engine_proc.pid, 0, 0
                    )
                
                time.sleep(0.3)
                if self.engine_proc.poll() is not None:
                    code = self.engine_proc.poll()
                    self.status_sub_lbl.config(text=f"Errore Motore (Codice {code})", fg="#dc2626")
                else:
                    self.status_sub_lbl.config(text="In attesa di duplicazione schermo...", fg="#64748b")
            except Exception as e:
                self.status_sub_lbl.config(text=f"Errore avvio: {e}", fg="#dc2626")
        else:
            self.status_sub_lbl.config(text="uxplay-windows.exe non trovato", fg="#dc2626")

    def restart_engine(self):
        self.start_engine()
        messagebox.showinfo("AirMirroring", "Ricevitore AirPlay riavviato con successo!")

    def stop_engine(self):
        if self.win_event_hook:
            try:
                user32.UnhookWinEvent(self.win_event_hook)
            except Exception:
                pass
            self.win_event_hook = None
            self.win_event_proc = None

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
                               creationflags=creation_flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                subprocess.run(["taskkill", "/F", "/IM", "uxplay-bluetooth-beacon.exe"],
                               creationflags=creation_flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                time.sleep(0.3)
            except Exception:
                pass

    def safe_after(self, func, *args):
        """Thread-safe UI callback scheduling that checks if app is still running."""
        if not self.running:
            return
        try:
            self.root.after(0, func, *args)
        except Exception:
            pass

    def _connection_monitor_loop(self):
        """Monitors network sockets and window states as safety fallback."""
        while self.running:
            time.sleep(1.0)
            if not self.running:
                break
            if self.engine_proc and self.engine_proc.poll() is None:
                client_ip = get_connected_client(self.engine_proc.pid)
                
                # Check for disconnection
                if self.connected_client_ip and not client_ip:
                    self.connected_client_ip = None
                    self.safe_after(self.switch_to_standby_mode)
                elif self.embedded_video_hwnd and not user32.IsWindow(self.embedded_video_hwnd):
                    self.safe_after(self.switch_to_standby_mode)
                # Fallback: if client connected but hook didn't capture window yet
                elif client_ip and not self.embedded_video_hwnd:
                    hwnds = find_window_by_pid(self.engine_proc.pid)
                    if hwnds:
                        video_hwnd = hwnds[0]
                        self.safe_after(lambda h=video_hwnd: self.dock_video_window(h))
                    
            elif self.engine_proc and self.engine_proc.poll() is not None:
                self.safe_after(lambda: self.status_sub_lbl.config(
                    text="Motore arrestato. Clicca Restart.", fg="#dc2626"))

    def open_settings_dialog(self):
        SettingsDialog(self)

    def show_carplay_dialog(self):
        messagebox.showinfo(
            "Wireless CarPlay",
            "La funzionalità Wireless CarPlay su PC Windows richiede un adattatore hardware USB compatibile o Bluetooth LE beacon attivo.\n\n"
            "Il ricevitore Bluetooth integrato sta già trasmettendo il segnale beacon per accelerare il rilevamento dell'iPhone."
        )

    def show_troubleshooting_dialog(self):
        msg = (
            "Se non vedi il ricevitore nel Centro di Controllo dell'iPhone:\n\n"
            "1. Verifica che iPhone e PC siano connessi esattamente alla STESSA rete Wi-Fi (stesso router).\n"
            "2. Assicurati che l'opzione 'Isolamento AP / Client Isolation' sia DISATTIVATA nelle impostazioni del tuo router.\n"
            "3. Controlla che il servizio Apple Bonjour sia attivo (puoi riavviarlo premendo Restart).\n"
            "4. Se usi una VPN sull'iPhone o sul PC, disattivala temporaneamente."
        )
        messagebox.showinfo("Risoluzione Problemi Rilevamento", msg)

    def show_network_diagnosis(self):
        net, ip = get_network_info()
        msg = (
            f"Diagnostica di Rete:\n\n"
            f"• Scheda attiva: {net}\n"
            f"• Indirizzo IP locale: {ip}\n"
            f"• Servizio Bonjour: Rilevato su porta 5353 (mDNS)\n"
            f"• Porta streaming AirPlay: 7000 / Dinamica\n\n"
            "Se il mirroring fallisce al momento della connessione, verifica che Windows Firewall non blocchi uxplay-windows.exe."
        )
        messagebox.showinfo("Stato Rete & Connessione", msg)

    def on_close(self):
        self.running = False
        self.stop_engine()
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)


class SettingsDialog(tk.Toplevel):
    """Modern comprehensive settings dialog matching user requirements."""
    def __init__(self, parent_app):
        super().__init__(parent_app.root)
        self.parent_app = parent_app
        self.title("Impostazioni AirMirroring")
        self.geometry("620x660")
        self.resizable(False, False)
        self.configure(bg="#f8fafc")
        self.transient(parent_app.root)
        self.grab_set()
        
        self.config = dict(parent_app.config)
        
        self._build_ui()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg="#ffffff", padx=20, pady=14,
                       highlightbackground="#e2e8f0", highlightthickness=1)
        hdr.pack(fill="x")
        
        t = tk.Label(hdr, text="⚙️ Impostazioni Mirroring & Funzioni Avanzate",
                     font=("Segoe UI", 13, "bold"), fg="#1e293b", bg="white")
        t.pack(anchor="w")
        sub = tk.Label(hdr, text="Personalizza nome, sicurezza, qualità video, fluidità e audio.",
                       font=("Segoe UI", 9), fg="#64748b", bg="white")
        sub.pack(anchor="w", pady=(2, 0))

        # Main scrollable/card container
        body = tk.Frame(self, bg="#f8fafc", padx=20, pady=12)
        body.pack(fill="both", expand=True)

        # 1. Device Name Card
        c1 = tk.LabelFrame(body, text=" 📱 Nome Ricevitore AirPlay ", font=("Segoe UI", 9, "bold"),
                           bg="#ffffff", fg="#1e293b", padx=14, pady=8, highlightbackground="#e2e8f0")
        c1.pack(fill="x", pady=(0, 8))

        row1 = tk.Frame(c1, bg="white")
        row1.pack(fill="x", pady=2)

        self.name_entry = tk.Entry(row1, font=("Segoe UI", 10), bg="#f8fafc", fg="#1e293b",
                                   relief="solid", bd=1)
        self.name_entry.insert(0, self.config.get("device_name", "Pc-dav"))
        self.name_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=3)

        default_btn = tk.Button(row1, text="Default", font=("Segoe UI", 8), bg="#f1f5f9", fg="#475569",
                                relief="flat", padx=10, pady=2, cursor="hand2",
                                command=lambda: (self.name_entry.delete(0, tk.END), self.name_entry.insert(0, "Pc-dav")))
        default_btn.pack(side="right")

        hint_name = tk.Label(c1, text="💡 Gli spazi sono convertiti automaticamente in '-' (es. Pc-dav) per mDNS Apple.",
                             font=("Segoe UI", 8), fg="#64748b", bg="white")
        hint_name.pack(anchor="w", pady=(3, 0))

        # 2. Security & PIN Card
        c2 = tk.LabelFrame(body, text=" 🔒 Sicurezza & Accesso PIN ", font=("Segoe UI", 9, "bold"),
                           bg="#ffffff", fg="#1e293b", padx=14, pady=8, highlightbackground="#e2e8f0")
        c2.pack(fill="x", pady=(0, 8))

        row2 = tk.Frame(c2, bg="white")
        row2.pack(fill="x", pady=2)

        self.pin_var = tk.BooleanVar(value=self.config.get("pin_enabled", False))
        pin_cb = tk.Checkbutton(row2, text="Richiedi PIN a 4 cifre per autorizzare la connessione",
                                variable=self.pin_var, font=("Segoe UI", 9), fg="#1e293b", bg="white",
                                activebackground="white")
        pin_cb.pack(side="left")

        self.pin_entry = tk.Entry(row2, font=("Segoe UI", 10, "bold"), width=6, bg="#f8fafc", fg="#d97706",
                                  justify="center", relief="solid", bd=1)
        self.pin_entry.insert(0, self.config.get("pin_code", "1234"))
        self.pin_entry.pack(side="left", padx=(10, 8), ipady=2)

        gen_pin_btn = tk.Button(row2, text="🎲 Genera PIN", font=("Segoe UI", 8), bg="#f1f5f9", fg="#475569",
                                relief="flat", padx=8, pady=2, cursor="hand2", command=self.generate_pin)
        gen_pin_btn.pack(side="left")

        # 3. Video Quality & FPS Card
        c3 = tk.LabelFrame(body, text=" ⚡ Risoluzione & Fluidità (FPS) ", font=("Segoe UI", 9, "bold"),
                           bg="#ffffff", fg="#1e293b", padx=14, pady=8, highlightbackground="#e2e8f0")
        c3.pack(fill="x", pady=(0, 8))

        row3 = tk.Frame(c3, bg="white")
        row3.pack(fill="x", pady=2)

        lbl_res = tk.Label(row3, text="Risoluzione Display:", font=("Segoe UI", 9), fg="#475569", bg="white")
        lbl_res.pack(side="left", padx=(0, 8))

        self.res_var = tk.StringVar(value=self.config.get("resolution", "1080p"))
        res_cb = ttk.Combobox(row3, textvariable=self.res_var, state="readonly", width=22,
                              values=["1080p (Full HD - 1920x1080)",
                                      "720p (Max Fluidità - 1280x720)",
                                      "1440p (2K Quad HD - 2560x1440)",
                                      "4K (Ultra HD - 3840x2160 H.265)"])
        cur_res = self.config.get("resolution", "1080p")
        if cur_res == "720p": res_cb.current(1)
        elif cur_res == "1440p": res_cb.current(2)
        elif cur_res == "4K": res_cb.current(3)
        else: res_cb.current(0)
        self.res_combobox = res_cb
        res_cb.pack(side="left", padx=(0, 14))

        lbl_fps = tk.Label(row3, text="Framerate:", font=("Segoe UI", 9), fg="#475569", bg="white")
        lbl_fps.pack(side="left", padx=(0, 6))

        self.fps_var = tk.StringVar(value=self.config.get("fps", "60"))
        fps_cb = ttk.Combobox(row3, textvariable=self.fps_var, state="readonly", width=8,
                              values=["60 FPS", "30 FPS"])
        fps_cb.current(0 if self.config.get("fps") == "60" else 1)
        self.fps_combobox = fps_cb
        fps_cb.pack(side="left")

        # 4. Latency & Audio Card
        c4 = tk.LabelFrame(body, text=" ⚡ Latenza (Zero-Lag) & Gestione Audio ", font=("Segoe UI", 9, "bold"),
                           bg="#ffffff", fg="#1e293b", padx=14, pady=8, highlightbackground="#e2e8f0")
        c4.pack(fill="x", pady=(0, 8))

        self.low_lat_var = tk.BooleanVar(value=self.config.get("low_latency", True))
        lat_cb = tk.Checkbutton(c4, text="Modalità Bassa Latenza (-vsync no, rendering immediato senza buffer)",
                                variable=self.low_lat_var, font=("Segoe UI", 9, "bold"), fg="#16a34a", bg="white",
                                activebackground="white")
        lat_cb.pack(anchor="w")

        row4 = tk.Frame(c4, bg="white")
        row4.pack(fill="x", pady=(4, 2))

        lbl_alat = tk.Label(row4, text="Buffer Audio Reporting:", font=("Segoe UI", 9), fg="#475569", bg="white")
        lbl_alat.pack(side="left", padx=(0, 8))

        self.alat_var = tk.StringVar(value=self.config.get("audio_latency", "0.1"))
        alat_cb = ttk.Combobox(row4, textvariable=self.alat_var, state="readonly", width=22,
                               values=["100ms (Bassa Latenza)", "250ms (Bilanciato standard)", "500ms (Tollerante Wi-Fi)"])
        cur_alat = self.config.get("audio_latency", "0.1")
        if cur_alat == "0.25": alat_cb.current(1)
        elif cur_alat == "0.5": alat_cb.current(2)
        else: alat_cb.current(0)
        self.alat_combobox = alat_cb
        alat_cb.pack(side="left", padx=(0, 14))

        self.audio_en_var = tk.BooleanVar(value=self.config.get("enable_audio", True))
        audio_cb = tk.Checkbutton(row4, text="Abilita Audio PC", variable=self.audio_en_var,
                                  font=("Segoe UI", 9), fg="#1e293b", bg="white", activebackground="white")
        audio_cb.pack(side="left")

        # 5. Display & Rotation Card
        c5 = tk.LabelFrame(body, text=" 📺 Comportamento Schermo & Orientamento ", font=("Segoe UI", 9, "bold"),
                           bg="#ffffff", fg="#1e293b", padx=14, pady=8, highlightbackground="#e2e8f0")
        c5.pack(fill="x", pady=(0, 8))

        row5 = tk.Frame(c5, bg="white")
        row5.pack(fill="x", pady=2)

        self.fs_auto_var = tk.BooleanVar(value=self.config.get("fullscreen_auto", False))
        fs_auto_cb = tk.Checkbutton(row5, text="Schermo intero automatico all'avvio", variable=self.fs_auto_var,
                                    font=("Segoe UI", 9), fg="#1e293b", bg="white", activebackground="white")
        fs_auto_cb.pack(side="left", padx=(0, 14))

        self.ontop_var = tk.BooleanVar(value=self.config.get("always_on_top", False))
        ontop_cb = tk.Checkbutton(row5, text="Finestra sempre in primo piano", variable=self.ontop_var,
                                  font=("Segoe UI", 9), fg="#1e293b", bg="white", activebackground="white")
        ontop_cb.pack(side="left")

        row5b = tk.Frame(c5, bg="white")
        row5b.pack(fill="x", pady=(4, 2))

        lbl_rot = tk.Label(row5b, text="Rotazione Display:", font=("Segoe UI", 9), fg="#475569", bg="white")
        lbl_rot.pack(side="left", padx=(0, 8))

        self.rot_var = tk.StringVar(value=self.config.get("rotation", "0"))
        rot_cb = ttk.Combobox(row5b, textvariable=self.rot_var, state="readonly", width=22,
                              values=["Normale (0°)", "Ruota Destra (90°)", "Ruota Sinistra (90°)", "Capovolto (180°)"])
        cur_rot = self.config.get("rotation", "0")
        if cur_rot == "90R": rot_cb.current(1)
        elif cur_rot == "90L": rot_cb.current(2)
        elif cur_rot == "180": rot_cb.current(3)
        else: rot_cb.current(0)
        self.rot_combobox = rot_cb
        rot_cb.pack(side="left")

        # Bottom Buttons
        btn_box = tk.Frame(self, bg="#f8fafc", padx=20, pady=10)
        btn_box.pack(fill="x", side="bottom")

        save_btn = tk.Button(btn_box, text="💾 Salva Impostazioni & Riavvia Ricevitore",
                             font=("Segoe UI", 10, "bold"), bg="#3b82f6", fg="#ffffff",
                             relief="flat", padx=16, pady=8, cursor="hand2", command=self.save_settings)
        save_btn.pack(side="right", padx=(8, 0))

        cancel_btn = tk.Button(btn_box, text="Annulla", font=("Segoe UI", 9),
                               bg="#e2e8f0", fg="#475569", relief="flat", padx=14, pady=8,
                               cursor="hand2", command=self.destroy)
        cancel_btn.pack(side="right")

    def generate_pin(self):
        pin = f"{random.randint(1000, 9999)}"
        self.pin_entry.delete(0, tk.END)
        self.pin_entry.insert(0, pin)
        self.pin_var.set(True)

    def save_settings(self):
        # 1. Device name (sanitize spaces to '-' for mDNS compatibility)
        raw_name = self.name_entry.get().strip()
        clean_name = raw_name.replace(" ", "-").replace('"', '').replace("'", "")
        clean_name = "".join(c for c in clean_name if c.isalnum() or c in ("-", "_")).strip()
        if not clean_name:
            clean_name = "Pc-dav"
        self.config["device_name"] = clean_name
        
        # 2. PIN
        pin_enabled = self.pin_var.get()
        pin_code = self.pin_entry.get().strip()
        if pin_enabled:
            if not (len(pin_code) == 4 and pin_code.isdigit()):
                messagebox.showerror("PIN non valido", "Il PIN deve essere composto esattamente da 4 cifre numeriche (es. 1234).")
                return
        self.config["pin_enabled"] = pin_enabled
        self.config["pin_code"] = pin_code
        
        # 3. Resolution
        res_sel = self.res_combobox.get()
        if "720p" in res_sel: self.config["resolution"] = "720p"
        elif "1440p" in res_sel: self.config["resolution"] = "1440p"
        elif "4K" in res_sel: self.config["resolution"] = "4K"
        else: self.config["resolution"] = "1080p"
        
        # 4. FPS
        fps_sel = self.fps_combobox.get()
        self.config["fps"] = "30" if "30" in fps_sel else "60"
        
        # 5. Latency & Audio
        self.config["low_latency"] = self.low_lat_var.get()
        alat_sel = self.alat_combobox.get()
        if "250ms" in alat_sel: self.config["audio_latency"] = "0.25"
        elif "500ms" in alat_sel: self.config["audio_latency"] = "0.5"
        else: self.config["audio_latency"] = "0.1"
        
        self.config["enable_audio"] = self.audio_en_var.get()
        
        # 6. Display & Rotation
        self.config["fullscreen_auto"] = self.fs_auto_var.get()
        self.config["always_on_top"] = self.ontop_var.get()
        self.parent_app.root.attributes("-topmost", self.config["always_on_top"])
        
        rot_sel = self.rot_combobox.get()
        if "Destra" in rot_sel: self.config["rotation"] = "90R"
        elif "Sinistra" in rot_sel: self.config["rotation"] = "90L"
        elif "180" in rot_sel: self.config["rotation"] = "180"
        else: self.config["rotation"] = "0"
        
        # Save to disk
        save_config(self.config)
        self.parent_app.config = dict(self.config)
        
        # Update parent UI elements
        self.parent_app._update_device_name_display()
        self.parent_app._update_pin_display()
        
        # Restart engine with new settings
        self.parent_app.start_engine()
        self.destroy()
        messagebox.showinfo("Impostazioni Salvate", "Le nuove impostazioni sono state salvate e il ricevitore è stato riavviato!")


def main():
    ERROR_ALREADY_EXISTS = 183
    mutex = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX)
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        focus_existing_window()
        sys.exit(0)

    root = tk.Tk()
    app = AirMirroringApp(root)
    root.mainloop()

    try:
        kernel32.CloseHandle(mutex)
    except Exception:
        pass

if __name__ == "__main__":
    main()
