"""
╔═══════════════════════════════════════════════════════╗
║   SanStudio HTML → EXE Converter                      ║
║   Developed by Santhosh A                             ║
║   https://a-santhosh-hub.github.io/in/               ║
╚═══════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
import threading
import webbrowser
import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from build_engine import BuildEngine

# ── Theme constants ──────────────────────────────────────────────────────────
DARK = {
    "bg":        "#0B0E17",
    "surface":   "#141824",
    "card":      "#1A2030",
    "border":    "#252D42",
    "accent":    "#4F8EF7",
    "accent2":   "#7C3AED",
    "success":   "#22C55E",
    "warning":   "#F59E0B",
    "danger":    "#EF4444",
    "text":      "#E8EDF5",
    "muted":     "#6B7A99",
    "label":     "#9BA8C0",
}
LIGHT = {
    "bg":        "#F0F4FA",
    "surface":   "#FFFFFF",
    "card":      "#F8FAFF",
    "border":    "#D1D9EE",
    "accent":    "#3B6FD4",
    "accent2":   "#6D28D9",
    "success":   "#16A34A",
    "warning":   "#D97706",
    "danger":    "#DC2626",
    "text":      "#0D1526",
    "muted":     "#7B8DB0",
    "label":     "#4A5978",
}

AUTHOR_URL = "https://a-santhosh-hub.github.io/in/"
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "builder_config.json")
HISTORY_PATH = os.path.join(os.path.dirname(__file__), "build_history.json")


# ── Utility helpers ──────────────────────────────────────────────────────────

def load_config():
    defaults = {
        "app_name": "MyApp",
        "width": 1200,
        "height": 800,
        "fullscreen": False,
        "resizable": True,
        "devtools": False,
        "splash_enabled": True,
        "splash_duration": 2500,
        "icon": "",
        "input_folder": "",
        "output_folder": "",
        "version": "1.0.0",
        "author": "Developed by Santhosh A",
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    return defaults


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def load_history():
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_history(entry: dict):
    history = load_history()
    history.insert(0, entry)
    history = history[:50]
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
#  Main Application
# ══════════════════════════════════════════════════════════════════════════════

class SanConverterApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self._theme_mode = "dark"
        self._T = DARK
        self._cfg = load_config()
        self._build_running = False
        self._engine = BuildEngine()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("SanStudio · HTML → EXE Converter")
        self.geometry("1120x720")
        self.minsize(900, 600)
        self.configure(fg_color=self._T["bg"])

        # ── DnD stub (tkinterdnd2 optional) ─────────────────────────────────
        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD
        except ImportError:
            pass

        self._build_ui()
        self._refresh_all_widgets()

    # ─────────────────────────────────────────────────────────────────────────
    #  Build UI
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        T = self._T

        # Root grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Sidebar ──────────────────────────────────────────────────────────
        self._sidebar = ctk.CTkFrame(self, width=200, fg_color=self._T["surface"],
                                     corner_radius=0, border_width=0)
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_propagate(False)
        self._sidebar.grid_rowconfigure(10, weight=1)

        # Logo
        logo_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=16, pady=(20, 8), sticky="ew")

        ctk.CTkLabel(logo_frame, text="⬡", font=ctk.CTkFont("Segoe UI", 28, "bold"),
                     text_color=T["accent"]).pack(anchor="w")
        ctk.CTkLabel(logo_frame, text="SanConverter",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=T["text"]).pack(anchor="w")
        ctk.CTkLabel(logo_frame, text="HTML → EXE",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=T["muted"]).pack(anchor="w")

        ctk.CTkFrame(self._sidebar, height=1, fg_color=T["border"]).grid(
            row=1, column=0, sticky="ew", padx=12, pady=8)

        # Nav buttons
        self._nav_buttons = {}
        pages = [
            ("🗂  Project",     "project"),
            ("⚙  Config",      "config"),
            ("🔨  Build",       "build"),
            ("📋  History",     "history"),
            ("ℹ  About",       "about"),
        ]
        for i, (label, key) in enumerate(pages, start=2):
            btn = ctk.CTkButton(
                self._sidebar, text=label, anchor="w",
                font=ctk.CTkFont("Segoe UI", 12),
                height=40, corner_radius=8,
                fg_color="transparent",
                hover_color=T["border"],
                text_color=T["text"],
                command=lambda k=key: self._switch_page(k)
            )
            btn.grid(row=i, column=0, padx=10, pady=2, sticky="ew")
            self._nav_buttons[key] = btn

        # Theme toggle
        ctk.CTkFrame(self._sidebar, height=1, fg_color=T["border"]).grid(
            row=9, column=0, sticky="ew", padx=12, pady=8)

        theme_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        theme_frame.grid(row=10, column=0, padx=12, pady=4, sticky="sew")
        theme_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(theme_frame, text="Theme", font=ctk.CTkFont("Segoe UI", 11),
                     text_color=T["muted"]).grid(row=0, column=0, sticky="w")
        self._theme_switch = ctk.CTkSwitch(
            theme_frame, text="Dark", onvalue="dark", offvalue="light",
            font=ctk.CTkFont("Segoe UI", 11), text_color=T["label"],
            command=self._toggle_theme, progress_color=T["accent"])
        self._theme_switch.grid(row=1, column=0, sticky="w", pady=4)
        self._theme_switch.select()

        # Footer credit
        credit = ctk.CTkLabel(
            self._sidebar,
            text="Developed by Santhosh A",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=T["accent"],
            cursor="hand2"
        )
        credit.grid(row=11, column=0, padx=12, pady=(4, 16), sticky="sew")
        credit.bind("<Button-1>", lambda e: webbrowser.open(AUTHOR_URL))

        # ── Content Area ─────────────────────────────────────────────────────
        self._content = ctk.CTkFrame(self, fg_color=self._T["bg"], corner_radius=0)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        # Build all page frames
        self._pages = {}
        self._pages["project"] = self._build_page_project()
        self._pages["config"]  = self._build_page_config()
        self._pages["build"]   = self._build_page_build()
        self._pages["history"] = self._build_page_history()
        self._pages["about"]   = self._build_page_about()

        self._switch_page("project")

    # ─────────────────────────────────────────────────────────────────────────
    #  Page: Project
    # ─────────────────────────────────────────────────────────────────────────

    def _build_page_project(self):
        T = self._T
        frame = ctk.CTkScrollableFrame(self._content, fg_color=T["bg"], corner_radius=0)
        frame.grid_columnconfigure(0, weight=1)

        self._page_header(frame, "🗂  Project Setup",
                          "Select your HTML project folder and configure output options.")

        # ── App Identity card ────────────────────────────────────────────────
        card = self._card(frame, "Application Identity")

        self._app_name_var = ctk.StringVar(value=self._cfg.get("app_name", "MyApp"))
        self._version_var  = ctk.StringVar(value=self._cfg.get("version", "1.0.0"))

        self._field_row(card, "App Name *", self._app_name_var,
                        "Name shown in window title & taskbar", row=0)
        self._field_row(card, "Version",    self._version_var,
                        "e.g. 1.0.0", row=1)

        # ── Folders card ─────────────────────────────────────────────────────
        fcard = self._card(frame, "Project Folders")

        self._input_var  = ctk.StringVar(value=self._cfg.get("input_folder", ""))
        self._output_var = ctk.StringVar(value=self._cfg.get("output_folder", ""))

        self._folder_row(fcard, "Input Folder *",  self._input_var,
                         "Folder containing index.html", self._browse_input, row=0)
        self._folder_row(fcard, "Output Folder *", self._output_var,
                         "Where to save the .exe file", self._browse_output, row=1)

        # ── Input Structure preview card ─────────────────────────────────────
        pcard = self._card(frame, "Detected Project Structure")
        self._structure_text = ctk.CTkTextbox(pcard, height=140,
                                               font=ctk.CTkFont("Consolas", 11),
                                               fg_color=T["bg"], text_color=T["muted"],
                                               border_width=0)
        self._structure_text.pack(fill="x", padx=0, pady=4)
        self._structure_text.configure(state="disabled")

        btn_scan = ctk.CTkButton(pcard, text="🔍  Scan Project",
                                  font=ctk.CTkFont("Segoe UI", 12),
                                  height=36, corner_radius=8,
                                  fg_color=T["accent"],
                                  hover_color=T["accent2"],
                                  command=self._scan_project)
        btn_scan.pack(anchor="w", pady=(4, 0))

        # ── Icon card ────────────────────────────────────────────────────────
        icard = self._card(frame, "EXE Icon (optional)")
        self._icon_var = ctk.StringVar(value=self._cfg.get("icon", ""))
        self._folder_row(icard, "Icon File (.ico)", self._icon_var,
                         "Leave blank for default", self._browse_icon, row=0)
        ctk.CTkLabel(icard, text="💡  Auto-converts PNG/JPG to .ico using Pillow",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=T["muted"]).pack(anchor="w", pady=(4, 0))

        return frame

    # ─────────────────────────────────────────────────────────────────────────
    #  Page: Config
    # ─────────────────────────────────────────────────────────────────────────

    def _build_page_config(self):
        T = self._T
        frame = ctk.CTkScrollableFrame(self._content, fg_color=T["bg"], corner_radius=0)
        frame.grid_columnconfigure(0, weight=1)

        self._page_header(frame, "⚙  Window Configuration",
                          "Customize how your application window behaves at runtime.")

        # ── Window Dimensions card ────────────────────────────────────────────
        wcard = self._card(frame, "Window Dimensions")
        self._width_var  = ctk.StringVar(value=str(self._cfg.get("width", 1200)))
        self._height_var = ctk.StringVar(value=str(self._cfg.get("height", 800)))
        self._field_row(wcard, "Width (px)",  self._width_var,  "Default: 1200", row=0)
        self._field_row(wcard, "Height (px)", self._height_var, "Default: 800",  row=1)

        # ── Window Behavior card ─────────────────────────────────────────────
        bcard = self._card(frame, "Window Behavior")

        self._fullscreen_var = ctk.BooleanVar(value=self._cfg.get("fullscreen", False))
        self._resizable_var  = ctk.BooleanVar(value=self._cfg.get("resizable", True))
        self._devtools_var   = ctk.BooleanVar(value=self._cfg.get("devtools", False))

        self._toggle_row(bcard, "Fullscreen Mode", self._fullscreen_var,
                         "Launch in full-screen mode", row=0)
        self._toggle_row(bcard, "Resizable Window", self._resizable_var,
                         "Allow user to resize the window", row=1)
        self._toggle_row(bcard, "Enable DevTools", self._devtools_var,
                         "Enable browser DevTools (debug mode only)", row=2)

        # ── Splash Screen card ───────────────────────────────────────────────
        scard = self._card(frame, "Splash Screen")

        self._splash_var = ctk.BooleanVar(value=self._cfg.get("splash_enabled", True))
        self._splash_dur = ctk.StringVar(value=str(self._cfg.get("splash_duration", 2500)))

        self._toggle_row(scard, "Enable Splash Screen", self._splash_var,
                         "Show loading screen before main window", row=0)
        self._field_row(scard, "Duration (ms)", self._splash_dur,
                        "How long splash shows (e.g. 2500 = 2.5s)", row=1)

        # ── JSON Preview card ────────────────────────────────────────────────
        jcard = self._card(frame, "Config Preview (builder_config.json)")
        self._config_preview = ctk.CTkTextbox(jcard, height=200,
                                               font=ctk.CTkFont("Consolas", 11),
                                               fg_color=T["bg"],
                                               text_color=T["success"],
                                               border_width=0)
        self._config_preview.pack(fill="x", pady=4)

        btn_refresh = ctk.CTkButton(jcard, text="🔄  Refresh Preview",
                                     font=ctk.CTkFont("Segoe UI", 12),
                                     height=36, corner_radius=8,
                                     fg_color=T["accent"],
                                     hover_color=T["accent2"],
                                     command=self._refresh_config_preview)
        btn_refresh.pack(anchor="w", pady=(0, 4))

        return frame

    # ─────────────────────────────────────────────────────────────────────────
    #  Page: Build
    # ─────────────────────────────────────────────────────────────────────────

    def _build_page_build(self):
        T = self._T
        frame = ctk.CTkFrame(self._content, fg_color=T["bg"], corner_radius=0)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        self._page_header(frame, "🔨  Build Engine",
                          "Package your HTML project into a standalone Windows .exe")

        # ── Status Banner ────────────────────────────────────────────────────
        self._status_banner = ctk.CTkFrame(frame, height=56,
                                            fg_color=T["card"],
                                            corner_radius=12,
                                            border_width=1,
                                            border_color=T["border"])
        self._status_banner.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="ew")
        self._status_banner.grid_columnconfigure(1, weight=1)
        self._status_banner.grid_propagate(False)

        self._status_dot = ctk.CTkLabel(self._status_banner, text="●",
                                         font=ctk.CTkFont("Segoe UI", 18),
                                         text_color=T["muted"])
        self._status_dot.grid(row=0, column=0, padx=(16, 8), pady=12)

        self._status_label = ctk.CTkLabel(self._status_banner,
                                           text="Ready to build",
                                           font=ctk.CTkFont("Segoe UI", 13),
                                           text_color=T["text"],
                                           anchor="w")
        self._status_label.grid(row=0, column=1, sticky="ew")

        # ── Build area ───────────────────────────────────────────────────────
        build_area = ctk.CTkFrame(frame, fg_color=T["bg"], corner_radius=0)
        build_area.grid(row=2, column=0, padx=20, pady=0, sticky="nsew")
        build_area.grid_columnconfigure(0, weight=1)
        build_area.grid_rowconfigure(1, weight=1)

        # Progress
        prog_frame = ctk.CTkFrame(build_area, fg_color=T["card"],
                                   corner_radius=12, border_width=1,
                                   border_color=T["border"])
        prog_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(prog_frame, text="Build Progress",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=T["label"]).pack(anchor="w", padx=16, pady=(12, 4))

        self._progress = ctk.CTkProgressBar(prog_frame, height=10,
                                             progress_color=T["accent"],
                                             fg_color=T["border"])
        self._progress.pack(fill="x", padx=16, pady=(0, 4))
        self._progress.set(0)

        self._progress_label = ctk.CTkLabel(prog_frame, text="0%",
                                             font=ctk.CTkFont("Consolas", 11),
                                             text_color=T["muted"])
        self._progress_label.pack(anchor="e", padx=16, pady=(0, 10))

        # Log output
        log_frame = ctk.CTkFrame(build_area, fg_color=T["card"],
                                  corner_radius=12, border_width=1,
                                  border_color=T["border"])
        log_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.grid(row=0, column=0, padx=16, pady=(12, 4), sticky="ew")
        log_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(log_header, text="Build Log",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=T["label"]).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(log_header, text="Clear",
                      font=ctk.CTkFont("Segoe UI", 11),
                      height=28, width=60, corner_radius=6,
                      fg_color=T["border"], hover_color=T["danger"],
                      text_color=T["muted"],
                      command=self._clear_log).grid(row=0, column=1)

        self._log_box = ctk.CTkTextbox(log_frame,
                                        font=ctk.CTkFont("Consolas", 11),
                                        fg_color=T["bg"],
                                        text_color=T["success"],
                                        border_width=0,
                                        wrap="word")
        self._log_box.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")

        # ── Build button area ────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=20, pady=(0, 16), sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        self._build_btn = ctk.CTkButton(
            btn_frame,
            text="🚀  Start Build",
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            height=52,
            corner_radius=12,
            fg_color=T["accent"],
            hover_color=T["accent2"],
            command=self._start_build
        )
        self._build_btn.grid(row=0, column=0, sticky="ew")

        return frame

    # ─────────────────────────────────────────────────────────────────────────
    #  Page: History
    # ─────────────────────────────────────────────────────────────────────────

    def _build_page_history(self):
        T = self._T
        frame = ctk.CTkScrollableFrame(self._content, fg_color=T["bg"], corner_radius=0)
        frame.grid_columnconfigure(0, weight=1)

        self._page_header(frame, "📋  Build History",
                          "Record of all previous build operations.")

        self._history_container = ctk.CTkFrame(frame, fg_color="transparent")
        self._history_container.pack(fill="x", padx=20, pady=4)

        self._refresh_history_page()
        return frame

    def _refresh_history_page(self):
        T = self._T
        for w in self._history_container.winfo_children():
            w.destroy()

        history = load_history()
        if not history:
            ctk.CTkLabel(self._history_container,
                         text="No builds yet. Run your first build to see history here.",
                         font=ctk.CTkFont("Segoe UI", 12),
                         text_color=T["muted"]).pack(pady=20)
            return

        for entry in history:
            card = ctk.CTkFrame(self._history_container,
                                 fg_color=T["card"], corner_radius=10,
                                 border_width=1, border_color=T["border"])
            card.pack(fill="x", pady=4)
            card.grid_columnconfigure(1, weight=1)

            status_color = T["success"] if entry.get("success") else T["danger"]
            status_sym   = "✔" if entry.get("success") else "✘"
            ctk.CTkLabel(card, text=status_sym,
                         font=ctk.CTkFont("Segoe UI", 20, "bold"),
                         text_color=status_color,
                         width=48).grid(row=0, column=0, rowspan=2, padx=12, pady=8)

            ctk.CTkLabel(card,
                         text=entry.get("app_name", "Unknown"),
                         font=ctk.CTkFont("Segoe UI", 13, "bold"),
                         text_color=T["text"],
                         anchor="w").grid(row=0, column=1, sticky="ew", padx=4, pady=(10, 0))

            meta = f"  {entry.get('timestamp','?')}  •  {entry.get('duration','?')}  •  {entry.get('output','?')}"
            ctk.CTkLabel(card, text=meta,
                         font=ctk.CTkFont("Segoe UI", 10),
                         text_color=T["muted"],
                         anchor="w").grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 10))

            if entry.get("output") and os.path.exists(entry.get("output", "")):
                ctk.CTkButton(card, text="Open",
                              font=ctk.CTkFont("Segoe UI", 11),
                              height=28, width=72, corner_radius=6,
                              fg_color=T["accent"],
                              hover_color=T["accent2"],
                              command=lambda p=entry["output"]: os.startfile(
                                  os.path.dirname(p))).grid(
                    row=0, column=2, rowspan=2, padx=12)

    # ─────────────────────────────────────────────────────────────────────────
    #  Page: About
    # ─────────────────────────────────────────────────────────────────────────

    def _build_page_about(self):
        T = self._T
        frame = ctk.CTkScrollableFrame(self._content, fg_color=T["bg"], corner_radius=0)
        frame.grid_columnconfigure(0, weight=1)

        self._page_header(frame, "ℹ  About", "SanStudio HTML → EXE Converter")

        card = ctk.CTkFrame(frame, fg_color=T["card"], corner_radius=14,
                             border_width=1, border_color=T["border"])
        card.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(card, text="⬡ SanConverter",
                     font=ctk.CTkFont("Segoe UI", 26, "bold"),
                     text_color=T["accent"]).pack(pady=(20, 4))
        ctk.CTkLabel(card, text="HTML Project Folder → Windows EXE Packager",
                     font=ctk.CTkFont("Segoe UI", 13),
                     text_color=T["text"]).pack()
        ctk.CTkLabel(card, text="Version 2.0 · Python 3.12+ · PyWebView + PyInstaller",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=T["muted"]).pack(pady=(4, 20))

        ctk.CTkFrame(card, height=1, fg_color=T["border"]).pack(fill="x", padx=20)

        info_items = [
            ("Render Engine",    "PyWebView with Edge Chromium backend"),
            ("Packager",         "PyInstaller (onefile, noconsole)"),
            ("GUI Framework",    "CustomTkinter"),
            ("Storage Support",  "localStorage · sessionStorage · IndexedDB"),
            ("OS Target",        "Windows 10 / Windows 11 · 64-bit"),
            ("Internet Mode",    "Auto-detect (online / offline)"),
        ]
        for label, val in info_items:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=2)
            ctk.CTkLabel(row, text=label,
                         font=ctk.CTkFont("Segoe UI", 11, "bold"),
                         text_color=T["label"],
                         width=160, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=val,
                         font=ctk.CTkFont("Segoe UI", 11),
                         text_color=T["text"],
                         anchor="w").pack(side="left")

        ctk.CTkFrame(card, height=1, fg_color=T["border"]).pack(fill="x", padx=20, pady=8)

        author_label = ctk.CTkLabel(card,
                                     text="Developed by Santhosh A",
                                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                                     text_color=T["accent"],
                                     cursor="hand2")
        author_label.pack(pady=(0, 4))
        author_label.bind("<Button-1>", lambda e: webbrowser.open(AUTHOR_URL))

        ctk.CTkLabel(card, text=AUTHOR_URL,
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=T["muted"],
                     cursor="hand2").pack(pady=(0, 20))

        tech_card = self._card(frame, "Technology Stack")
        techs = [
            ("PyWebView",      "Renders HTML/CSS/JS using native WebView2 (Edge)"),
            ("PyInstaller",    "Bundles Python + assets into single .exe"),
            ("CustomTkinter",  "Modern dark-mode GUI framework"),
            ("http.server",    "Local HTTP server for serving project assets"),
            ("Jinja2",         "Template engine for runtime code generation"),
            ("Pillow",         "Auto-converts image formats to .ico for EXE icon"),
        ]
        for tech, desc in techs:
            r = ctk.CTkFrame(tech_card, fg_color=T["bg"], corner_radius=8)
            r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text=tech,
                         font=ctk.CTkFont("Consolas", 11, "bold"),
                         text_color=T["success"],
                         width=140, anchor="w").pack(side="left", padx=10, pady=6)
            ctk.CTkLabel(r, text=desc,
                         font=ctk.CTkFont("Segoe UI", 11),
                         text_color=T["muted"],
                         anchor="w").pack(side="left")

        return frame

    # ─────────────────────────────────────────────────────────────────────────
    #  Reusable widget helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _page_header(self, parent, title: str, subtitle: str):
        T = self._T
        hf = ctk.CTkFrame(parent, fg_color="transparent")
        hf.pack(fill="x", padx=20, pady=(20, 8))
        ctk.CTkLabel(hf, text=title,
                     font=ctk.CTkFont("Segoe UI", 20, "bold"),
                     text_color=T["text"]).pack(anchor="w")
        ctk.CTkLabel(hf, text=subtitle,
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=T["muted"]).pack(anchor="w")
        ctk.CTkFrame(hf, height=1, fg_color=T["border"]).pack(fill="x", pady=(8, 0))

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        T = self._T
        outer = ctk.CTkFrame(parent, fg_color=T["card"], corner_radius=12,
                              border_width=1, border_color=T["border"])
        outer.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(outer, text=title,
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=T["label"]).pack(anchor="w", padx=16, pady=(12, 6))
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=(0, 12))
        return inner

    def _field_row(self, parent, label: str, var: ctk.StringVar,
                   hint: str = "", row: int = 0):
        T = self._T
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        fr.pack(fill="x", pady=3)
        fr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(fr, text=label,
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=T["label"],
                     width=140, anchor="w").grid(row=0, column=0, sticky="w")
        entry = ctk.CTkEntry(fr, textvariable=var,
                              font=ctk.CTkFont("Segoe UI", 11),
                              fg_color=T["bg"],
                              border_color=T["border"],
                              text_color=T["text"],
                              height=34)
        entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        if hint:
            ctk.CTkLabel(fr, text=hint,
                         font=ctk.CTkFont("Segoe UI", 9),
                         text_color=T["muted"]).grid(row=1, column=1, sticky="w",
                                                      padx=(8, 0))

    def _folder_row(self, parent, label: str, var: ctk.StringVar,
                    hint: str, cmd, row: int = 0):
        T = self._T
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        fr.pack(fill="x", pady=3)
        fr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(fr, text=label,
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=T["label"],
                     width=140, anchor="w").grid(row=0, column=0, sticky="w")
        entry = ctk.CTkEntry(fr, textvariable=var,
                              font=ctk.CTkFont("Segoe UI", 11),
                              fg_color=T["bg"],
                              border_color=T["border"],
                              text_color=T["text"],
                              height=34)
        entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ctk.CTkButton(fr, text="Browse",
                       font=ctk.CTkFont("Segoe UI", 11),
                       width=80, height=34, corner_radius=6,
                       fg_color=T["border"],
                       hover_color=T["accent"],
                       text_color=T["text"],
                       command=cmd).grid(row=0, column=2, padx=(6, 0))
        if hint:
            ctk.CTkLabel(fr, text=hint,
                         font=ctk.CTkFont("Segoe UI", 9),
                         text_color=T["muted"]).grid(row=1, column=1, sticky="w",
                                                      padx=(8, 0))

    def _toggle_row(self, parent, label: str, var: ctk.BooleanVar,
                    hint: str = "", row: int = 0):
        T = self._T
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        fr.pack(fill="x", pady=4)
        fr.grid_columnconfigure(0, weight=1)
        sw = ctk.CTkSwitch(fr, text=label, variable=var,
                            font=ctk.CTkFont("Segoe UI", 11),
                            text_color=T["text"],
                            progress_color=T["accent"])
        sw.grid(row=0, column=0, sticky="w")
        if hint:
            ctk.CTkLabel(fr, text=f"   {hint}",
                         font=ctk.CTkFont("Segoe UI", 9),
                         text_color=T["muted"]).grid(row=1, column=0, sticky="w",
                                                      padx=52)

    # ─────────────────────────────────────────────────────────────────────────
    #  Navigation
    # ─────────────────────────────────────────────────────────────────────────

    def _switch_page(self, page_key: str):
        T = self._T
        for key, frame in self._pages.items():
            frame.grid_remove()
        self._pages[page_key].grid(row=0, column=0, sticky="nsew")

        for key, btn in self._nav_buttons.items():
            if key == page_key:
                btn.configure(fg_color=T["accent"],
                               text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent",
                               text_color=T["text"])

    # ─────────────────────────────────────────────────────────────────────────
    #  Theme toggle
    # ─────────────────────────────────────────────────────────────────────────

    def _toggle_theme(self):
        if self._theme_switch.get() == "dark":
            self._theme_mode = "dark"
            self._T = DARK
            ctk.set_appearance_mode("dark")
            self._theme_switch.configure(text="Dark")
        else:
            self._theme_mode = "light"
            self._T = LIGHT
            ctk.set_appearance_mode("light")
            self._theme_switch.configure(text="Light")
        self._refresh_all_widgets()

    def _refresh_all_widgets(self):
        # Minimal color refresh (CustomTkinter handles most theming natively)
        pass

    # ─────────────────────────────────────────────────────────────────────────
    #  Browse handlers
    # ─────────────────────────────────────────────────────────────────────────

    def _browse_input(self):
        path = filedialog.askdirectory(title="Select HTML Project Folder")
        if path:
            self._input_var.set(path)

    def _browse_output(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self._output_var.set(path)

    def _browse_icon(self):
        path = filedialog.askopenfilename(
            title="Select Icon File",
            filetypes=[("Icon files", "*.ico"), ("Image files", "*.png *.jpg *.jpeg"),
                       ("All files", "*.*")]
        )
        if path:
            self._icon_var.set(path)

    # ─────────────────────────────────────────────────────────────────────────
    #  Scan project
    # ─────────────────────────────────────────────────────────────────────────

    def _scan_project(self):
        inp = self._input_var.get().strip()
        if not inp or not os.path.isdir(inp):
            messagebox.showerror("Error", "Please select a valid input folder first.")
            return

        result = self._engine.scan_project(inp)
        self._structure_text.configure(state="normal")
        self._structure_text.delete("1.0", "end")
        self._structure_text.insert("1.0", result)
        self._structure_text.configure(state="disabled")

    # ─────────────────────────────────────────────────────────────────────────
    #  Config preview
    # ─────────────────────────────────────────────────────────────────────────

    def _refresh_config_preview(self):
        cfg = self._collect_config()
        preview = json.dumps(cfg, indent=2)
        self._config_preview.configure(state="normal")
        self._config_preview.delete("1.0", "end")
        self._config_preview.insert("1.0", preview)
        self._config_preview.configure(state="disabled")

    # ─────────────────────────────────────────────────────────────────────────
    #  Collect config from form
    # ─────────────────────────────────────────────────────────────────────────

    def _collect_config(self) -> dict:
        return {
            "app_name":        self._app_name_var.get().strip() or "MyApp",
            "version":         self._version_var.get().strip() or "1.0.0",
            "input_folder":    self._input_var.get().strip(),
            "output_folder":   self._output_var.get().strip(),
            "icon":            self._icon_var.get().strip(),
            "width":           int(self._width_var.get() or 1200),
            "height":          int(self._height_var.get() or 800),
            "fullscreen":      self._fullscreen_var.get(),
            "resizable":       self._resizable_var.get(),
            "devtools":        self._devtools_var.get(),
            "splash_enabled":  self._splash_var.get(),
            "splash_duration": int(self._splash_dur.get() or 2500),
            "author":          "Developed by Santhosh A",
            "author_url":      AUTHOR_URL,
        }

    # ─────────────────────────────────────────────────────────────────────────
    #  Log helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _log(self, msg: str, color: str = None):
        self._log_box.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_box.insert("end", f"[{timestamp}] {msg}\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    def _set_status(self, text: str, color: str = None):
        T = self._T
        self._status_label.configure(text=text)
        self._status_dot.configure(text_color=color or T["muted"])

    def _set_progress(self, value: float, label: str = None):
        self._progress.set(value)
        pct = int(value * 100)
        self._progress_label.configure(text=label or f"{pct}%")

    # ─────────────────────────────────────────────────────────────────────────
    #  Build
    # ─────────────────────────────────────────────────────────────────────────

    def _start_build(self):
        if self._build_running:
            messagebox.showwarning("Build Running", "A build is already in progress.")
            return

        cfg = self._collect_config()

        # Validate
        if not cfg["input_folder"] or not os.path.isdir(cfg["input_folder"]):
            messagebox.showerror("Missing Input", "Please select a valid input project folder.")
            return
        if not os.path.exists(os.path.join(cfg["input_folder"], "index.html")):
            messagebox.showerror("Missing index.html",
                                  "No index.html found in the input folder.")
            return
        if not cfg["output_folder"] or not os.path.isdir(cfg["output_folder"]):
            messagebox.showerror("Missing Output", "Please select a valid output folder.")
            return
        if not cfg["app_name"]:
            messagebox.showerror("Missing Name", "Please enter an application name.")
            return

        save_config(cfg)
        self._switch_page("build")

        self._build_running = True
        self._build_btn.configure(text="⏳  Building...", state="disabled")
        self._clear_log()
        self._set_progress(0)
        self._set_status("Starting build...", self._T["warning"])

        thread = threading.Thread(target=self._build_thread, args=(cfg,), daemon=True)
        thread.start()

    def _build_thread(self, cfg: dict):
        start_time = time.time()
        success = False
        output_path = ""

        try:
            def progress_cb(pct: float, msg: str):
                self.after(0, self._set_progress, pct)
                self.after(0, self._set_status, msg,
                            self._T["warning"] if pct < 1.0 else self._T["success"])
                self.after(0, self._log, msg)

            output_path = self._engine.build(cfg, progress_cb)
            success = True

        except Exception as ex:
            self.after(0, self._log, f"✘ Build failed: {ex}")
            self.after(0, self._set_status, f"Build failed: {ex}", self._T["danger"])
            self.after(0, self._set_progress, 0, "Failed")
        finally:
            elapsed = time.time() - start_time
            duration = f"{elapsed:.1f}s"
            self._build_running = False
            self.after(0, self._build_btn.configure,
                       {"text": "🚀  Start Build", "state": "normal"})

            if success:
                self.after(0, self._log, f"✔ Build complete in {duration}")
                self.after(0, self._log, f"  Output: {output_path}")
                self.after(0, self._set_progress, 1.0, "100% — Done!")
                self.after(0, self._set_status, "✔ Build succeeded!", self._T["success"])
                self.after(0, messagebox.showinfo,
                           "Build Complete",
                           f"EXE created successfully!\n\n{output_path}")
            save_history({
                "app_name":  cfg["app_name"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "duration":  duration,
                "success":   success,
                "output":    output_path,
            })
            self.after(0, self._refresh_history_page)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = SanConverterApp()
    app.mainloop()
