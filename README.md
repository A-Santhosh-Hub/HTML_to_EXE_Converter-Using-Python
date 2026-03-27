# ⬡ SanStudio HTML → EXE Converter

**Developed by Santhosh A** · [Portfolio](https://a-santhosh-hub.github.io/in/)

Convert any static or dynamic HTML project folder into a standalone Windows `.exe` desktop application — no Python, no Node.js required on the end-user's machine.

---

## 🚀 Quick Start

### 1. Install Dependencies (first time only)
```
Double-click: install_deps.bat
```
Or manually:
```bash
pip install customtkinter pyinstaller pywebview Pillow Jinja2
```

### 2. Launch the Converter
```
Double-click: build.bat
```

### 3. Configure & Build
1. **Project tab** → Select your HTML project folder (must contain `index.html`)
2. **Project tab** → Select an output folder for the `.exe`
3. **Config tab** → Set window size, splash screen, icon, DevTools options
4. **Build tab** → Click **🚀 Start Build**
5. Your `.exe` appears in the output folder!

---

## 📁 Project Structure

```
SanHTMLConverter/
├── builder_app.py          ← Main GUI (CustomTkinter)
├── build_engine.py         ← Build & packaging logic
├── builder_config.json     ← Saved configuration
├── build_history.json      ← Auto-generated build history
├── build.bat               ← Launch script
├── install_deps.bat        ← One-time dependency installer
├── requirements.txt        ← Python dependencies
└── input_project/          ← Sample HTML project (try it!)
    ├── index.html
    └── assets/
        ├── style.css
        └── script.js
```

---

## ⚙️ Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `app_name` | `MyApp` | Window title & EXE filename |
| `version` | `1.0.0` | App version string |
| `width` | `1200` | Initial window width (px) |
| `height` | `800` | Initial window height (px) |
| `fullscreen` | `false` | Launch in fullscreen |
| `resizable` | `true` | Allow window resizing |
| `devtools` | `false` | Enable browser DevTools |
| `splash_enabled` | `true` | Show loading splash screen |
| `splash_duration` | `2500` | Splash duration in ms |
| `icon` | `""` | Path to `.ico` / `.png` / `.jpg` |

---

## 🌐 Runtime Features

The generated `.exe` supports everything a modern browser does:

| Feature | Status |
|---------|--------|
| HTML5 / CSS3 / JavaScript (ES2022+) | ✅ Full support |
| localStorage | ✅ Persistent |
| sessionStorage | ✅ Supported |
| IndexedDB | ✅ Supported |
| Fetch / XMLHttpRequest | ✅ Works online/offline |
| Drag & Drop | ✅ Full support |
| File Upload (`<input type="file">`) | ✅ Full support |
| `<iframe>` (internal & external) | ✅ Full support |
| CSS Animations / Transitions | ✅ Full support |
| Web Fonts | ✅ Full support |
| Video / Audio playback | ✅ Full support |
| Canvas / WebGL | ✅ Full support |
| SVG | ✅ Full support |
| Internet APIs (fetch) | ✅ When connected |
| Offline mode | ✅ Automatic |
| DevTools | ⚙ Enable in Config tab |

---

## 🔧 Runtime Architecture

```
Your HTML Project
    ↓
PyInstaller bundles:
  ├── runtime_main.py  (auto-generated)
  ├── web_project/     (your HTML files)
  └── PyWebView (Edge Chromium renderer)
    ↓
EXE launches:
  1. Local HTTP server (127.0.0.1:random_port)
  2. PyWebView window → http://127.0.0.1:{port}/index.html
  3. Footer injected via JS: "Developed by Santhosh A"
```

**Why a local HTTP server?**  
Serving via `http://` instead of `file://` ensures `localStorage`, `fetch`, CORS, and all modern web APIs work exactly as they do in a real browser.

---

## 📦 Output

After a successful build, your output folder contains:

```
output/
├── YourAppName.exe    ← Standalone executable (~50-100 MB)
└── build_log.txt      ← Detailed build report
```

The `.exe` is completely self-contained. End users need:
- ✅ Windows 10 / 11 (64-bit)
- ✅ Microsoft Edge WebView2 Runtime (pre-installed on Windows 11; auto-installs on Win 10)
- ❌ No Python needed
- ❌ No Node.js needed
- ❌ No internet needed (for offline projects)

---

## 🛠 Technology Stack

| Library | Purpose |
|---------|---------|
| `CustomTkinter` | Modern dark-mode GUI |
| `PyWebView` | HTML rendering (Edge Chromium / WebView2) |
| `PyInstaller` | Bundle Python + assets → `.exe` |
| `http.server` | Local HTTP server inside the `.exe` |
| `Pillow` | Convert PNG/JPG icons → `.ico` |
| `Jinja2` | Available for advanced template use |

---

## 🔄 Rebuilding / Updating

1. Replace files in your HTML project folder
2. Open SanConverter → click **🚀 Start Build** again
3. The old `.exe` is overwritten automatically

---

## 🐛 Troubleshooting

**"index.html not found"** → Make sure your project folder directly contains `index.html` at the root.

**EXE opens blank window** → Enable DevTools in Config tab, rebuild, and check the console for JS errors.

**PyInstaller fails** → Run `install_deps.bat` again to ensure all dependencies are up to date.

**White flash on startup** → Increase the `splash_duration` in Config tab.

**Edge WebView2 not found** → Download from: https://developer.microsoft.com/en-us/microsoft-edge/webview2/

---

## 📝 Build Log

Every build produces a `build_log.txt` in your output folder containing:
- Asset scan report
- PyInstaller output
- Build duration
- Error details (if any)

---

## 👤 Author

**Developed by Santhosh A**  
🌐 https://a-santhosh-hub.github.io/in/

---

*SanStudio HTML → EXE Converter — Production-grade HTML to Desktop App packager*
