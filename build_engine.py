"""
╔═══════════════════════════════════════════════════════╗
║   SanStudio Build Engine v2.1                         ║
║   Developed by Santhosh A                             ║
║   https://a-santhosh-hub.github.io/in/               ║
╚═══════════════════════════════════════════════════════╝

Pipeline:
  1. Validate project structure
  2. Auto-analyze project (detect features, decide patches)
  3. Generate patched runtime_main.py
  4. Run PyInstaller -> .exe
  5. Write build log
"""

import os
import sys
import re
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional

try:
    from PIL import Image as PILImage
    PILLOW_OK = True
except ImportError:
    PILLOW_OK = False

AUTHOR_URL = "https://a-santhosh-hub.github.io/in/"

# =============================================================================
#  ProjectAnalyzer
# =============================================================================

class ProjectAnalyzer:
    """Scans HTML/JS/CSS source and returns a feature + patch map."""

    PATTERNS = [
        ("window_open",       "window.open() popups",
         [r"window\.open\s*\("]),
        ("blob_url",          "Blob / ObjectURL (live preview, PDF, download)",
         [r"URL\.createObjectURL\s*\(", r"\bblob:", r"new\s+Blob\s*\("]),
        ("download_attr",     "HTML download attribute",
         [r'download\s*=', r'\.download\s*=']),
        ("fetch_api",         "fetch() / XHR (online APIs)",
         [r"\bfetch\s*\(", r"XMLHttpRequest"]),
        ("clipboard",         "Clipboard API",
         [r"navigator\.clipboard", r'document\.execCommand\s*\(\s*[\'"]copy']),
        ("local_storage",     "localStorage",
         [r"\blocalStorage\b"]),
        ("session_storage",   "sessionStorage",
         [r"\bsessionStorage\b"]),
        ("indexed_db",        "IndexedDB",
         [r"\bindexedDB\b", r"IDBDatabase"]),
        ("drag_drop",         "Drag and Drop",
         [r"ondrop\s*=", r"addEventListener\s*\(\s*['\"]drop", r"draggable\s*="]),
        ("file_input",        "File upload",
         [r'type\s*=\s*["\']file["\']', r'\.files\b']),
        ("iframe",            "iframe / postMessage",
         [r"<iframe\b", r"contentWindow", r"postMessage\s*\("]),
        ("canvas_webgl",      "Canvas / WebGL",
         [r"<canvas\b", r"getContext\s*\(\s*['\"]2d", r"getContext\s*\(\s*['\"]webgl"]),
        ("media",             "Video / Audio",
         [r"<video\b", r"<audio\b", r"MediaRecorder"]),
        ("notifications",     "Web Notifications",
         [r"Notification\.requestPermission", r"new\s+Notification\s*\("]),
        ("geolocation",       "Geolocation",
         [r"navigator\.geolocation"]),
        ("service_worker",    "Service Worker / PWA",
         [r"serviceWorker\.register", r"self\.skipWaiting"]),
        ("web_worker",        "Web Workers",
         [r"new\s+Worker\s*\(", r"new\s+SharedWorker\s*\("]),
        ("print",             "window.print()",
         [r"window\.print\s*\("]),
        ("context_menu",      "Custom right-click menu",
         [r"contextmenu", r"oncontextmenu"]),
        ("whatsapp_upi",      "WhatsApp / UPI deep links",
         [r"wa\.me/", r"whatsapp://", r"upi://", r"intent://"]),
        ("external_links",    "External HTTP links",
         [r'href\s*=\s*["\']https?://', r'window\.location\s*=\s*["\']https?://']),
        ("chart_lib",         "Chart.js / D3 / Plotly",
         [r"Chart\s*\(", r"\bd3\.", r"Plotly\."]),
        ("pdf_export",        "PDF export (jsPDF / pdfmake)",
         [r"jsPDF", r"pdfmake", r'\.save\s*\(\s*[\'"][^\'"]+\.pdf']),
        ("qr_code",           "QR code generation",
         [r"QRCode", r"qrcode"]),
        ("signature_pad",     "Signature / canvas drawing",
         [r"SignaturePad", r"getImageData", r"toDataURL\s*\("]),
    ]

    def analyze(self, folder: str) -> dict:
        source_files = []
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs
                       if d not in ("node_modules", ".git", "__pycache__", "venv")]
            for fname in files:
                if Path(fname).suffix.lower() in (".html", ".htm", ".js", ".mjs", ".css"):
                    try:
                        with open(os.path.join(root, fname),
                                  encoding="utf-8", errors="ignore") as f:
                            source_files.append((fname, f.read()))
                    except Exception:
                        pass

        combined = "\n".join(s for _, s in source_files)
        features = {}
        for key, label, patterns in self.PATTERNS:
            features[key] = any(re.search(p, combined, re.IGNORECASE) for p in patterns)

        patches  = self._decide_patches(features)
        report   = self._build_report(features, source_files)
        warnings = self._build_warnings(features)
        return {"features": features, "patches": patches,
                "report": report, "warnings": warnings}

    @staticmethod
    def _decide_patches(f: dict) -> list:
        patches = ["core_bridge"]
        if f.get("window_open") or f.get("blob_url"):
            patches.append("popup_and_blob")
        if f.get("download_attr") or f.get("blob_url"):
            patches.append("download_intercept")
        if f.get("clipboard"):
            patches.append("clipboard_bridge")
        if f.get("print"):
            patches.append("print_bridge")
        if f.get("notifications"):
            patches.append("notifications_suppress")
        if f.get("service_worker"):
            patches.append("service_worker_suppress")
        if f.get("whatsapp_upi") or f.get("external_links"):
            patches.append("external_links_bridge")
        if f.get("context_menu"):
            patches.append("context_menu_allow")
        return patches

    @staticmethod
    def _build_report(features: dict, source_files: list) -> str:
        label_map = {k: lbl for k, lbl, _ in ProjectAnalyzer.PATTERNS}
        lines = [f"  Scanned {len(source_files)} source file(s)", ""]
        lines.append("  DETECTED:")
        for k, v in features.items():
            if v:
                lines.append(f"    + {label_map.get(k, k)}")
        lines.append("  NOT DETECTED:")
        for k, v in features.items():
            if not v:
                lines.append(f"    o {label_map.get(k, k)}")
        return "\n".join(lines)

    @staticmethod
    def _build_warnings(features: dict) -> list:
        w = []
        if features.get("service_worker"):
            w.append("WARNING: Service Worker disabled in EXE mode.")
        if features.get("geolocation"):
            w.append("WARNING: Geolocation may require HTTPS on some WebView2 versions.")
        if features.get("notifications"):
            w.append("WARNING: Web Notifications suppressed (replaced with no-op).")
        return w


# =============================================================================
#  JS Patch Library
# =============================================================================

JS_CORE_BRIDGE = r"""
(function(){
  'use strict';
  window.__san = window.__san || {};
  window.__san._origOpen  = window.open;
  window.__san._origAlert = window.alert;
  console.log('[SAN] core bridge ready');
})();
"""

JS_POPUP_AND_BLOB = r"""
(function(){
  'use strict';

  /* Track all blob URLs this page creates */
  var _reg = {};
  var _origCreate = URL.createObjectURL.bind(URL);
  var _origRevoke = URL.revokeObjectURL.bind(URL);

  URL.createObjectURL = function(obj){
    var u = _origCreate(obj);
    if(obj instanceof Blob || obj instanceof File){
      _reg[u] = { blob: obj, mime: obj.type || 'application/octet-stream' };
    }
    return u;
  };
  URL.revokeObjectURL = function(u){ delete _reg[u]; _origRevoke(u); };

  /* Read blob as base64 */
  function blobToB64(blob){
    return new Promise(function(res, rej){
      var r = new FileReader();
      r.onload  = function(){ res(r.result.split(',')[1]); };
      r.onerror = function(){ rej(r.error); };
      r.readAsDataURL(blob);
    });
  }

  /* Decide: is this mime type a "viewable" preview, or should it always be saved? */
  function isViewable(mime){
    return /html|xml|svg|text\/plain/.test(mime);
  }

  /* Save a blob URL to disk via Python bridge */
  function saveBlob(url, filename){
    var entry = _reg[url];
    if(!entry){ console.warn('[SAN] blob not in registry:', url); return; }
    blobToB64(entry.blob).then(function(b64){
      window.pywebview.api.save_blob_file(b64, entry.mime, filename);
    }).catch(function(e){ console.error('[SAN] blob save error', e); });
  }

  /* Save a data: URI to disk via Python bridge */
  function saveDataUri(dataUri, filename){
    var m = dataUri.match(/^data:([^;]+);base64,(.+)$/);
    if(m) window.pywebview.api.save_blob_file(m[2], m[1], filename);
  }

  /* Route window.open() calls */
  function route(url, title){
    title = title || document.title || 'Preview';
    if(!url || url === 'about:blank') return null;

    /* External URL -> system browser */
    if(/^https?:\/\//i.test(url)){
      window.pywebview.api.open_url(url);
      return null;
    }

    /* Blob URL opened via window.open (no download attr) -> preview */
    if(url.startsWith('blob:')){
      var entry = _reg[url];
      if(entry && isViewable(entry.mime)){
        blobToB64(entry.blob).then(function(b64){
          window.pywebview.api.open_blob_window(b64, entry.mime, title);
        }).catch(function(e){ console.error('[SAN] blob preview error', e); });
      } else if(entry){
        /* Non-viewable blob opened via window.open -> save it */
        blobToB64(entry.blob).then(function(b64){
          window.pywebview.api.save_blob_file(b64, entry.mime, title);
        }).catch(function(e){ console.error('[SAN] blob save error', e); });
      }
      return null;
    }

    /* data: URI */
    if(url.startsWith('data:')){
      var m = url.match(/^data:([^;]+);base64,(.+)$/);
      if(m){
        if(isViewable(m[1])){
          window.pywebview.api.open_blob_window(m[2], m[1], title);
        } else {
          window.pywebview.api.save_blob_file(m[2], m[1], title);
        }
      }
      return null;
    }

    /* Relative / local URL -> new popup window */
    window.pywebview.api.open_popup_window(url, title);
    return null;
  }

  /* Override window.open */
  window.open = function(url, target, features){
    if(!url || url === '' || url === 'about:blank'){
      return window.__san._origOpen.call(window, url, target, features);
    }
    if(window.pywebview && window.pywebview.api){
      return route(url, (target && target !== '_blank') ? target : document.title);
    }
    window.addEventListener('pywebviewready', function(){
      route(url, (target && target !== '_blank') ? target : document.title);
    }, { once: true });
    return null;
  };

  /* Intercept <a href="blob:..."> and <a href="data:..."> clicks */
  document.addEventListener('click', function(e){
    var a = e.target.closest('a[href]');
    if(!a) return;
    var href = a.getAttribute('href') || '';
    var dlName = a.getAttribute('download');

    if(href.startsWith('blob:')){
      e.preventDefault(); e.stopPropagation();
      if(!window.pywebview || !window.pywebview.api) return;
      /* Has download attribute -> always SAVE to disk */
      if(dlName !== null){
        var fname = dlName || (document.title + '.bin');
        saveBlob(href, fname);
      } else {
        /* No download attr -> preview if viewable, else save */
        var entry = _reg[href];
        if(entry && isViewable(entry.mime)){
          blobToB64(entry.blob).then(function(b64){
            window.pywebview.api.open_blob_window(b64, entry.mime, document.title);
          });
        } else if(entry){
          saveBlob(href, document.title + '.bin');
        }
      }
    } else if(href.startsWith('data:')){
      e.preventDefault(); e.stopPropagation();
      if(!window.pywebview || !window.pywebview.api) return;
      var fname2 = dlName || (document.title + '.bin');
      if(dlName !== null){
        saveDataUri(href, fname2);
      } else {
        var m2 = href.match(/^data:([^;]+);/);
        if(m2 && isViewable(m2[1])){
          var parts = href.match(/^data:([^;]+);base64,(.+)$/);
          if(parts) window.pywebview.api.open_blob_window(parts[2], parts[1], document.title);
        } else {
          saveDataUri(href, fname2);
        }
      }
    }
  }, true);

  console.log('[SAN] popup+blob patch active (v2.2)');
})();
"""

JS_DOWNLOAD_INTERCEPT = r"""
(function(){
  'use strict';

  /* Intercept <a download> clicks for non-blob, non-data URLs */
  document.addEventListener('click', function(e){
    var a = e.target.closest('a[download]');
    if(!a) return;
    var href = a.getAttribute('href') || '';
    /* blob: and data: are handled by the popup+blob patch above */
    if(href.startsWith('blob:') || href.startsWith('data:')) return;
    if(href && href !== '#'){
      e.preventDefault();
      var fname = a.getAttribute('download') || 'download';
      if(window.pywebview && window.pywebview.api){
        window.pywebview.api.save_file(fname, href);
      }
    }
  }, true);

  /* Intercept programmatic anchor clicks: JS creates <a>, sets .download, .href=blob, calls .click() */
  var _origClick = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function(){
    var a = this;
    var href = a.getAttribute('href') || a.href || '';
    var dl   = a.getAttribute('download');
    if(dl !== null && (href.startsWith('blob:') || href.startsWith('data:'))){
      /* Simulate the click event so popup+blob patch catches it */
      var ev = new MouseEvent('click', { bubbles: true, cancelable: true });
      a.dispatchEvent(ev);
      return;
    }
    return _origClick.call(a);
  };

  console.log('[SAN] download intercept active (v2.2)');
})();
"""

JS_CLIPBOARD_BRIDGE = r"""
(function(){
  'use strict';
  if(navigator.clipboard){
    var _orig = navigator.clipboard.writeText.bind(navigator.clipboard);
    navigator.clipboard.writeText = function(text){
      if(window.pywebview && window.pywebview.api){
        window.pywebview.api.set_clipboard(text);
        return Promise.resolve();
      }
      return _orig(text);
    };
  }
  var _origExec = document.execCommand.bind(document);
  document.execCommand = function(cmd){
    if(cmd === 'copy' && window.pywebview && window.pywebview.api){
      var s = window.getSelection();
      if(s) window.pywebview.api.set_clipboard(s.toString());
      return true;
    }
    return _origExec.apply(document, arguments);
  };
  console.log('[SAN] clipboard bridge active');
})();
"""

JS_PRINT_BRIDGE = r"""
(function(){
  'use strict';
  var _orig = window.print.bind(window);
  window.print = function(){
    try{ _orig(); }
    catch(e){
      if(window.pywebview && window.pywebview.api) window.pywebview.api.show_print_notice();
    }
  };
  console.log('[SAN] print bridge active');
})();
"""

JS_NOTIFICATIONS_SUPPRESS = r"""
(function(){
  'use strict';
  window.Notification = function(){};
  window.Notification.requestPermission = function(){ return Promise.resolve('denied'); };
  window.Notification.permission = 'denied';
  console.log('[SAN] notifications suppressed');
})();
"""

JS_SERVICE_WORKER_SUPPRESS = r"""
(function(){
  'use strict';
  if(navigator.serviceWorker){
    navigator.serviceWorker.register = function(){
      return Promise.reject(new Error('[SAN] SW disabled in EXE mode'));
    };
  }
  console.log('[SAN] service worker disabled');
})();
"""

JS_EXTERNAL_LINKS_BRIDGE = r"""
(function(){
  'use strict';
  document.addEventListener('click', function(e){
    var a = e.target.closest('a[href]');
    if(!a) return;
    var href = a.getAttribute('href') || '';
    if(/^https?:\/\//i.test(href) || /^(whatsapp|upi|intent):/.test(href)){
      e.preventDefault();
      if(window.pywebview && window.pywebview.api) window.pywebview.api.open_url(href);
    }
  }, false);
  console.log('[SAN] external links bridge active');
})();
"""

JS_CONTEXT_MENU_ALLOW = r"""
(function(){
  document.oncontextmenu = null;
  console.log('[SAN] context menu patch active');
})();
"""

JS_FOOTER = r"""
(function(){
  /* ── Toast notification system ── */
  function __sanToast(msg, type){
    var t = document.getElementById('__san_toast');
    if(!t){
      t = document.createElement('div');
      t.id = '__san_toast';
      t.style.cssText = 'position:fixed;bottom:52px;right:20px;z-index:99999;'
        + 'font-family:Segoe UI,sans-serif;font-size:13px;font-weight:500;'
        + 'padding:10px 18px;border-radius:10px;pointer-events:none;'
        + 'transition:opacity .35s,transform .35s;opacity:0;transform:translateY(10px);'
        + 'box-shadow:0 4px 20px rgba(0,0,0,.4);max-width:320px;';
      document.body.appendChild(t);
    }
    var bg  = type === 'error' ? '#EF4444' : type === 'warn' ? '#F59E0B' : '#22C55E';
    t.style.background = bg;
    t.style.color = '#fff';
    t.textContent = msg;
    t.style.opacity = '1';
    t.style.transform = 'translateY(0)';
    clearTimeout(t.__tid);
    t.__tid = setTimeout(function(){
      t.style.opacity = '0'; t.style.transform = 'translateY(10px)';
    }, 3200);
  }
  window.__sanToast = __sanToast;

  /* ── Wrap pywebview API calls to show toasts on download result ── */
  function __wrapApi(){
    if(!window.pywebview || !window.pywebview.api) return;
    var _orig = window.pywebview.api.save_blob_file;
    if(!_orig || _orig.__wrapped) return;
    window.pywebview.api.save_blob_file = function(b64, mime, fname){
      return _orig.call(window.pywebview.api, b64, mime, fname).then(function(res){
        try {
          var r = typeof res === 'string' ? JSON.parse(res) : res;
          if(r && r.ok){
            var short = r.path ? r.path.split(/[\\/]/).pop() : fname;
            __sanToast('✔  Saved: ' + short);
          } else if(r && r.error && r.error !== 'cancelled'){
            __sanToast('✘  Save failed: ' + r.error, 'error');
          }
        } catch(e){}
        return res;
      });
    };
    window.pywebview.api.save_blob_file.__wrapped = true;
  }

  if(window.pywebview){ __wrapApi(); }
  else { window.addEventListener('pywebviewready', __wrapApi, {once:true}); }

  /* ── Footer bar ── */
  if(document.getElementById('__san_footer')) return;
  document.body.style.paddingBottom = '36px';
  var el = document.createElement('div');
  el.id = '__san_footer';
  el.style.cssText = 'position:fixed;bottom:0;left:0;width:100%;height:32px;'
    + 'background:rgba(11,14,23,0.92);'
    + 'display:flex;align-items:center;justify-content:center;'
    + 'font-family:Segoe UI,sans-serif;font-size:11px;color:#6B7A99;'
    + 'letter-spacing:.3px;border-top:1px solid rgba(79,142,247,0.18);'
    + 'box-sizing:border-box;z-index:9999';
  el.innerHTML = '<span style="margin-right:4px">&#x2B21;</span>Developed by '
    + '<a href="javascript:void(0)" '
    + 'onclick="if(window.pywebview&&window.pywebview.api)window.pywebview.api.open_author()" '
    + 'style="color:#4F8EF7;text-decoration:none;margin-left:4px">Santhosh A</a>';
  document.body.appendChild(el);
})();
"""

PATCH_MAP = {
    "core_bridge":             JS_CORE_BRIDGE,
    "popup_and_blob":          JS_POPUP_AND_BLOB,
    "download_intercept":      JS_DOWNLOAD_INTERCEPT,
    "clipboard_bridge":        JS_CLIPBOARD_BRIDGE,
    "print_bridge":            JS_PRINT_BRIDGE,
    "notifications_suppress":  JS_NOTIFICATIONS_SUPPRESS,
    "service_worker_suppress": JS_SERVICE_WORKER_SUPPRESS,
    "external_links_bridge":   JS_EXTERNAL_LINKS_BRIDGE,
    "context_menu_allow":      JS_CONTEXT_MENU_ALLOW,
}

# =============================================================================
#  Runtime template
# =============================================================================

RUNTIME_TEMPLATE = '''"""
SanStudio Runtime -- auto-generated by SanConverter v2.1
App: {{APP_NAME}} v{{APP_VERSION}}
Developed by Santhosh A . https://a-santhosh-hub.github.io/in/
"""
import sys, os, json, socket, threading, http.server, socketserver
import webbrowser, time, tempfile, base64, re, shutil

def _res(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

PROJECT_DIR     = _res("web_project")
APP_NAME        = "{{APP_NAME}}"
APP_VERSION     = "{{APP_VERSION}}"
APP_WIDTH       = {{APP_WIDTH}}
APP_HEIGHT      = {{APP_HEIGHT}}
FULLSCREEN      = {{FULLSCREEN}}
RESIZABLE       = {{RESIZABLE}}
DEVTOOLS        = {{DEVTOOLS}}
SPLASH_ENABLED  = {{SPLASH_ENABLED}}
SPLASH_DURATION = {{SPLASH_DURATION}}
AUTHOR_URL      = "https://a-santhosh-hub.github.io/in/"

# -- HTTP server ---------------------------------------------------------------
def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]

PORT = _free_port()

class _Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=PROJECT_DIR, **kw)
    def log_message(self, *a): pass
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

def _run_server():
    with socketserver.TCPServer(("127.0.0.1", PORT), _Handler) as h: h.serve_forever()

# -- Temp dir ------------------------------------------------------------------
_TMPDIR = tempfile.mkdtemp(prefix="san_rt_")

def _tmp_html(content, name="preview.html"):
    p = os.path.join(_TMPDIR, name)
    with open(p, "w", encoding="utf-8") as f: f.write(content)
    return p

# -- JS/Python bridge ----------------------------------------------------------
class _Api:
    def __init__(self): self._wins = []

    def open_author(self): webbrowser.open(AUTHOR_URL)
    def open_url(self, url): webbrowser.open(url)

    def open_popup_window(self, url, title=""):
        import webview
        title = title or APP_NAME + " -- Preview"
        if not url.startswith("http"):
            url = f"http://127.0.0.1:{PORT}/{url.lstrip('/')}"
        w = webview.create_window(title, url,
                                   width=min(APP_WIDTH,1200),
                                   height=min(APP_HEIGHT,800), resizable=True)
        self._wins.append(w)

    def open_blob_window(self, b64, mime_type, title=""):
        import webview
        title = title or APP_NAME + " -- Preview"
        try: raw = base64.b64decode(b64)
        except Exception as e: print(f"[SAN] b64 decode error: {e}"); return

        if any(x in mime_type for x in ("html","xml","svg","text")) or mime_type == "":
            try: html_str = raw.decode("utf-8", errors="replace")
            except: html_str = raw.decode("latin-1", errors="replace")
            safe = re.sub(r"[^a-zA-Z0-9._-]", "_", title) + ".html"
            path = _tmp_html(html_str, safe)
            w = webview.create_window(title, f"file:///{path}",
                                       width=min(APP_WIDTH,1200),
                                       height=min(APP_HEIGHT,800), resizable=True)
            self._wins.append(w)
        else:
            self._save_blob(b64, mime_type, title)

    def save_file(self, filename, data):
        try:
            dl = os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(dl, exist_ok=True)
            dest = os.path.join(dl, filename)
            m = re.match(r"data:[^;]+;base64,(.+)", data, re.DOTALL)
            if m:
                with open(dest, "wb") as f: f.write(base64.b64decode(m.group(1)))
            else:
                with open(dest, "w", encoding="utf-8") as f: f.write(data)
            os.startfile(dest)
            return json.dumps({"ok": True, "path": dest})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    def save_blob_file(self, b64, mime_type, filename):
        """Called by JS when user clicks a download link with blob: or data: URL."""
        try:
            import tkinter.filedialog as fd
            # Build a sensible default filename and extension
            ext_map = {
                "text/plain": ".txt",
                "text/html": ".html",
                "text/css": ".css",
                "application/javascript": ".js",
                "text/javascript": ".js",
                "application/json": ".json",
                "application/xml": ".xml",
                "text/xml": ".xml",
                "text/csv": ".csv",
                "application/pdf": ".pdf",
                "image/png": ".png",
                "image/jpeg": ".jpg",
                "image/gif": ".gif",
                "image/svg+xml": ".svg",
                "image/webp": ".webp",
                "application/zip": ".zip",
                "application/octet-stream": ".bin",
            }
            safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename or "download").strip("_") or "download"
            # Add extension if missing
            _, cur_ext = os.path.splitext(safe_name)
            if not cur_ext:
                safe_name += ext_map.get(mime_type.split(";")[0].strip(), ".txt")

            # Figure out filetype filter for dialog
            ext = os.path.splitext(safe_name)[1]
            ft = [(f"*{ext} files", f"*{ext}"), ("All files", "*.*")]

            # Default save path
            dl = os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(dl, exist_ok=True)
            default_path = os.path.join(dl, safe_name)

            # Open native Save As dialog
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            dest = fd.asksaveasfilename(
                parent=root,
                title="Save File",
                initialdir=dl,
                initialfile=safe_name,
                defaultextension=ext,
                filetypes=ft,
            )
            root.destroy()

            if not dest:
                return json.dumps({"ok": False, "error": "cancelled"})

            raw = base64.b64decode(b64)
            # Text types: write as UTF-8 text
            if any(t in mime_type for t in ("text/", "javascript", "json", "xml", "svg", "html", "css")):
                try:
                    text = raw.decode("utf-8")
                    with open(dest, "w", encoding="utf-8") as f: f.write(text)
                except UnicodeDecodeError:
                    with open(dest, "wb") as f: f.write(raw)
            else:
                with open(dest, "wb") as f: f.write(raw)

            # Open Explorer and highlight the saved file
            try:
                import subprocess as _sp
                _sp.Popen(["explorer", "/select,", dest])
            except Exception:
                pass

            return json.dumps({"ok": True, "path": dest})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    def _save_blob(self, b64, mime_type, hint):
        try:
            ext = {"application/pdf":".pdf","image/png":".png","image/jpeg":".jpg",
                   "image/gif":".gif","image/svg+xml":".svg","application/zip":".zip"
                   }.get(mime_type, ".bin")
            safe = re.sub(r"[^a-zA-Z0-9._-]", "_", hint) or "download"
            if not safe.endswith(ext): safe += ext
            dl = os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(dl, exist_ok=True)
            dest = os.path.join(dl, safe)
            with open(dest, "wb") as f: f.write(base64.b64decode(b64))
            os.startfile(dest)
        except Exception as e: print(f"[SAN] save_blob error: {e}")

    def set_clipboard(self, text):
        try:
            import tkinter as tk
            r = tk.Tk(); r.withdraw()
            r.clipboard_clear(); r.clipboard_append(text); r.update()
            r.after(100, r.destroy); return True
        except: return False

    def show_print_notice(self):
        import tkinter.messagebox as mb
        mb.showinfo("Print", "Use Ctrl+P for best print results.")

    def get_app_info(self):
        return json.dumps({"name": APP_NAME, "version": APP_VERSION})

# -- Injected JS (patches + footer) -------------------------------------------
INJECT_JS = """__INJECT_JS__"""

# -- Splash HTML --------------------------------------------------------------
SPLASH_HTML = """__SPLASH_HTML__"""

# -- Main ---------------------------------------------------------------------
def main():
    import webview
    threading.Thread(target=_run_server, daemon=True).start()
    time.sleep(0.35)

    api = _Api()
    url = f"http://127.0.0.1:{PORT}/index.html"

    if SPLASH_ENABLED:
        splash_path = _tmp_html(
            SPLASH_HTML.replace("__APP_NAME__", APP_NAME)
                       .replace("__SPLASH_MS__", str(SPLASH_DURATION)))
        sw = webview.create_window(APP_NAME, f"file:///{splash_path}",
                                    width=480, height=300,
                                    frameless=True, resizable=False, on_top=True)
        def _startup():
            time.sleep(SPLASH_DURATION / 1000.0)
            mw = webview.create_window(APP_NAME, url,
                                        width=APP_WIDTH, height=APP_HEIGHT,
                                        fullscreen=FULLSCREEN, resizable=RESIZABLE,
                                        js_api=api, min_size=(400,300))
            try: sw.destroy()
            except: pass
            time.sleep(1.0)
            try: mw.evaluate_js(INJECT_JS)
            except Exception as e: print(f"[SAN] inject: {e}")
        webview.start(_startup, debug=DEVTOOLS)
    else:
        win = webview.create_window(APP_NAME, url,
                                     width=APP_WIDTH, height=APP_HEIGHT,
                                     fullscreen=FULLSCREEN, resizable=RESIZABLE,
                                     js_api=api, min_size=(400,300))
        def _startup():
            time.sleep(1.0)
            try: win.evaluate_js(INJECT_JS)
            except Exception as e: print(f"[SAN] inject: {e}")
        webview.start(_startup, debug=DEVTOOLS)

    try: shutil.rmtree(_TMPDIR, ignore_errors=True)
    except: pass

if __name__ == "__main__":
    main()
'''

SPLASH_HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0B0E17;display:flex;flex-direction:column;
     align-items:center;justify-content:center;height:100vh;
     font-family:'Segoe UI',sans-serif;overflow:hidden}
.hex{font-size:52px;color:#4F8EF7;animation:pulse 1.4s ease-in-out infinite}
.title{color:#E8EDF5;font-size:22px;font-weight:700;margin-top:12px}
.sub{color:#6B7A99;font-size:12px;margin-top:6px}
.bw{width:220px;height:3px;background:#1A2030;border-radius:99px;margin-top:28px;overflow:hidden}
.b{height:100%;background:linear-gradient(90deg,#4F8EF7,#7C3AED);
   border-radius:99px;animation:load __SPLASH_MS__ms linear forwards}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
@keyframes load{from{width:0}to{width:100%}}
</style></head><body>
<div class="hex">&#x2B21;</div>
<div class="title">__APP_NAME__</div>
<div class="sub">Loading&#x2026;</div>
<div class="bw"><div class="b"></div></div>
</body></html>"""


# =============================================================================
#  BuildEngine
# =============================================================================

class BuildEngine:

    def __init__(self):
        self._analyzer      = ProjectAnalyzer()
        self._last_analysis = None

    # ── Tree scan ─────────────────────────────────────────────────────────────

    def scan_project(self, folder: str) -> str:
        lines = [f"FOLDER: {os.path.basename(folder)}/"]
        has_index = os.path.exists(os.path.join(folder, "index.html"))
        stats = {"files": 0, "dirs": 0, "kb": 0.0}

        for root, dirs, files in os.walk(folder):
            dirs.sort()
            dirs[:] = [d for d in dirs
                       if d not in ("node_modules", ".git", "__pycache__")]
            depth  = root.replace(folder, "").count(os.sep)
            indent = "   " * depth
            if depth > 0:
                lines.append(f"{indent}[{os.path.basename(root)}/]")
                stats["dirs"] += 1
            for fn in sorted(files)[:20]:
                fp = os.path.join(root, fn)
                kb = os.path.getsize(fp) / 1024
                stats["files"] += 1; stats["kb"] += kb
                lines.append(f"{indent}   {self._icon(fn)} {fn}  ({kb:.1f} KB)")
            if len(files) > 20:
                lines.append(f"{indent}   ... +{len(files)-20} more")

        lines += ["",
                  f"Total: {stats['files']} files, {stats['dirs']} dirs, "
                  f"{stats['kb']:.1f} KB",
                  "OK: index.html found" if has_index else "ERROR: index.html missing!"]

        try:
            analysis = self._analyzer.analyze(folder)
            self._last_analysis = analysis
            lines += ["", "=== AUTO ANALYSIS ===", analysis["report"], ""]
            for w in analysis["warnings"]: lines.append(w)
            lines += ["",
                      f"Patches to apply ({len(analysis['patches'])}):"]
            for p in analysis["patches"]: lines.append(f"  + {p}")
        except Exception as e:
            lines.append(f"Analysis error: {e}")

        return "\n".join(lines)

    @staticmethod
    def _icon(name: str) -> str:
        return {".html":"[H]",".htm":"[H]",".css":"[C]",".js":"[J]",".mjs":"[J]",
                ".json":"[J]",".png":"[I]",".jpg":"[I]",".jpeg":"[I]",".gif":"[I]",
                ".svg":"[S]",".mp4":"[V]",".mp3":"[A]",".ttf":"[F]",".woff":"[F]",
                ".ico":"[*]",".pdf":"[P]",".zip":"[Z]"
                }.get(Path(name).suffix.lower(), "[?]")

    # ── Validate ──────────────────────────────────────────────────────────────

    def validate(self, folder: str) -> list:
        errs = []
        if not folder or not os.path.isdir(folder):
            errs.append("Input folder does not exist."); return errs
        if not os.path.exists(os.path.join(folder, "index.html")):
            errs.append("index.html not found in input folder.")
        return errs

    # ── Icon conversion ───────────────────────────────────────────────────────

    def _prepare_icon(self, icon_path: str, work_dir: str) -> Optional[str]:
        if not icon_path or not os.path.exists(icon_path): return None
        ico = os.path.join(work_dir, "app_icon.ico")
        if Path(icon_path).suffix.lower() == ".ico":
            shutil.copy2(icon_path, ico); return ico
        if not PILLOW_OK: return None
        try:
            PILImage.open(icon_path).convert("RGBA").save(
                ico, format="ICO",
                sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
            return ico
        except Exception: return None

    # ── Main build ────────────────────────────────────────────────────────────

    def build(self, cfg: dict, progress: Callable[[float, str], None]) -> str:
        log_lines = []
        def log(m): log_lines.append(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")

        progress(0.02, "Validating…")
        errs = self.validate(cfg["input_folder"])
        if errs: raise RuntimeError("\n".join(errs))
        log("Validation OK")

        build_dir = tempfile.mkdtemp(prefix="san_build_")
        log(f"Work dir: {build_dir}")

        try:
            self._do_build(cfg, build_dir, progress, log)
        except Exception:
            self._write_log(cfg["output_folder"], log_lines)
            raise
        finally:
            try: shutil.rmtree(build_dir, ignore_errors=True)
            except: pass

        out = os.path.join(cfg["output_folder"],
                           cfg["app_name"].replace(" ", "_") + ".exe")
        self._write_log(cfg["output_folder"], log_lines)
        return out

    def _do_build(self, cfg, build_dir, progress, log):
        app_name   = cfg["app_name"].replace(" ", "_")
        input_dir  = cfg["input_folder"]
        output_dir = cfg["output_folder"]
        os.makedirs(output_dir, exist_ok=True)

        # 1. Copy assets
        progress(0.10, "Copying project assets…")
        web_dest = os.path.join(build_dir, "web_project")
        shutil.copytree(input_dir, web_dest, dirs_exist_ok=True)
        n = sum(len(f) for _, _, f in os.walk(web_dest))
        log(f"Copied {n} assets")

        # 2. Analyze
        progress(0.16, "Analyzing project features…")
        analysis = self._last_analysis or self._analyzer.analyze(input_dir)
        self._last_analysis = analysis
        patches = analysis["patches"]
        log(f"Detected features: {sum(1 for v in analysis['features'].values() if v)}")
        log(f"Patches: {', '.join(patches)}")
        for w in analysis["warnings"]: log(w)

        # 3. Build JS bundle
        progress(0.22, "Building JS patch bundle…")
        js_parts = [PATCH_MAP[p] for p in patches if p in PATCH_MAP]
        js_parts.append(JS_FOOTER)
        inject_js = "\n\n".join(js_parts)
        log(f"JS bundle: {len(inject_js):,} chars, {len(js_parts)} patches")

        # 4. Generate runtime
        progress(0.26, "Generating runtime engine…")
        code = RUNTIME_TEMPLATE
        # Embed JS and splash
        code = code.replace("__INJECT_JS__",  inject_js)
        code = code.replace("__SPLASH_HTML__", SPLASH_HTML_TEMPLATE)
        # Replace config placeholders
        for k, v in {
            "{{APP_NAME}}":        cfg["app_name"],
            "{{APP_VERSION}}":     cfg.get("version", "1.0.0"),
            "{{APP_WIDTH}}":       str(cfg.get("width", 1200)),
            "{{APP_HEIGHT}}":      str(cfg.get("height", 800)),
            "{{FULLSCREEN}}":      str(cfg.get("fullscreen", False)),
            "{{RESIZABLE}}":       str(cfg.get("resizable", True)),
            "{{DEVTOOLS}}":        str(cfg.get("devtools", False)),
            "{{SPLASH_ENABLED}}":  str(cfg.get("splash_enabled", True)),
            "{{SPLASH_DURATION}}": str(cfg.get("splash_duration", 2500)),
        }.items():
            code = code.replace(k, v)

        runtime_path = os.path.join(build_dir, "runtime_main.py")
        with open(runtime_path, "w", encoding="utf-8") as f: f.write(code)
        log("runtime_main.py generated")

        # 5. Icon
        progress(0.30, "Processing icon…")
        icon_path = self._prepare_icon(cfg.get("icon", ""), build_dir)
        log(f"Icon: {os.path.basename(icon_path) if icon_path else 'default'}")

        # 6. Config JSON
        with open(os.path.join(build_dir, "app_config.json"), "w") as f:
            json.dump({"app_name": cfg["app_name"],
                       "version": cfg.get("version","1.0.0"),
                       "author": "Developed by Santhosh A",
                       "author_url": AUTHOR_URL,
                       "patches": patches}, f, indent=2)

        # 7. PyInstaller
        progress(0.36, "Running PyInstaller… (1-3 min)")
        sep = ";" if sys.platform == "win32" else ":"
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile", "--noconsole", "--clean",
            f"--name={app_name}",
            f"--distpath={output_dir}",
            f"--workpath={os.path.join(build_dir,'pi_work')}",
            f"--specpath={build_dir}",
            f"--add-data={web_dest}{sep}web_project",
            f"--add-data={os.path.join(build_dir,'app_config.json')}{sep}.",
        ]
        if icon_path: cmd.append(f"--icon={icon_path}")
        for h in ["webview", "webview.platforms.winforms", "clr",
                  "tkinter", "tkinter.filedialog", "tkinter.messagebox"]:
            cmd += ["--hidden-import", h]
        cmd.append(runtime_path)

        log(f"CMD: {' '.join(cmd[:6])} ...")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 cwd=build_dir, text=True,
                                 encoding="utf-8", errors="replace")
        pi_p = 0.36
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None: break
            line = line.rstrip()
            if not line: continue
            log(f"[PI] {line}")
            if "Analyzing" in line:  pi_p = min(0.55, pi_p + 0.008)
            elif "Building" in line: pi_p = min(0.80, pi_p + 0.01)
            elif "PKG"      in line: pi_p = min(0.90, pi_p + 0.02)
            elif "EXE"      in line: pi_p = min(0.95, pi_p + 0.02)
            progress(pi_p, line[:70])

        if proc.wait() != 0:
            raise RuntimeError("PyInstaller failed — see build_log.txt")

        progress(0.97, "Verifying output…")
        out_exe = os.path.join(output_dir, f"{app_name}.exe")
        if not os.path.exists(out_exe):
            raise RuntimeError(f".exe not found in {output_dir}")

        mb = os.path.getsize(out_exe) / (1024*1024)
        log(f"Output: {out_exe} ({mb:.1f} MB)")
        progress(1.0, f"Done -- {app_name}.exe ({mb:.1f} MB)")

    # ── Log ───────────────────────────────────────────────────────────────────

    @staticmethod
    def _write_log(output_dir, lines):
        try:
            os.makedirs(output_dir, exist_ok=True)
            with open(os.path.join(output_dir, "build_log.txt"),
                      "w", encoding="utf-8") as f:
                f.write("SanStudio HTML to EXE Converter -- Build Log\n")
                f.write("Developed by Santhosh A\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass
