"""
╔═══════════════════════════════════════════════════════╗
║   SanStudio — CLI Build Script                        ║
║   Developed by Santhosh A                             ║
║   https://a-santhosh-hub.github.io/in/               ║
╚═══════════════════════════════════════════════════════╝

Headless build: no GUI required.

Usage:
    python build_cli.py [--config builder_config.json]
    python build_cli.py --input ./my_project --output ./dist --name MyApp

Options:
    --config    Path to builder_config.json  (default: ./builder_config.json)
    --input     Input project folder         (overrides config)
    --output    Output folder                (overrides config)
    --name      App name                     (overrides config)
    --width     Window width                 (overrides config)
    --height    Window height                (overrides config)
    --icon      Path to icon file            (overrides config)
    --fullscreen  Enable fullscreen
    --no-splash   Disable splash screen
    --devtools    Enable developer tools
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

from build_engine import BuildEngine

AUTHOR = "Developed by Santhosh A"
AUTHOR_URL = "https://a-santhosh-hub.github.io/in/"


def print_header():
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║   SanStudio HTML → EXE Converter (CLI)      ║")
    print("  ║   Developed by Santhosh A                   ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()


def progress_cb(pct: float, msg: str):
    bar_len = 40
    filled = int(bar_len * pct)
    bar = "█" * filled + "░" * (bar_len - filled)
    pct_str = f"{int(pct*100):3d}%"
    print(f"\r  [{bar}] {pct_str}  {msg[:50]:<50}", end="", flush=True)
    if pct >= 1.0:
        print()


def main():
    print_header()

    parser = argparse.ArgumentParser(
        description="SanStudio HTML → EXE CLI Builder",
        epilog=f"  {AUTHOR}  {AUTHOR_URL}"
    )
    parser.add_argument("--config",      default="builder_config.json")
    parser.add_argument("--input",       default=None)
    parser.add_argument("--output",      default=None)
    parser.add_argument("--name",        default=None)
    parser.add_argument("--width",       type=int, default=None)
    parser.add_argument("--height",      type=int, default=None)
    parser.add_argument("--icon",        default=None)
    parser.add_argument("--version",     default=None)
    parser.add_argument("--fullscreen",  action="store_true", default=None)
    parser.add_argument("--no-splash",   action="store_true")
    parser.add_argument("--devtools",    action="store_true")
    args = parser.parse_args()

    # ── Load base config ──────────────────────────────────────────────────────
    cfg = {
        "app_name":       "MyApp",
        "version":        "1.0.0",
        "width":          1200,
        "height":         800,
        "fullscreen":     False,
        "resizable":      True,
        "devtools":       False,
        "splash_enabled": True,
        "splash_duration":2500,
        "icon":           "",
        "input_folder":   "",
        "output_folder":  "",
    }

    if os.path.exists(args.config):
        with open(args.config) as f:
            cfg.update(json.load(f))
        print(f"  Loaded config: {args.config}")
    else:
        print(f"  Config not found ({args.config}), using defaults")

    # ── CLI overrides ─────────────────────────────────────────────────────────
    if args.input:   cfg["input_folder"]  = args.input
    if args.output:  cfg["output_folder"] = args.output
    if args.name:    cfg["app_name"]      = args.name
    if args.width:   cfg["width"]         = args.width
    if args.height:  cfg["height"]        = args.height
    if args.icon:    cfg["icon"]          = args.icon
    if args.version: cfg["version"]       = args.version
    if args.fullscreen:      cfg["fullscreen"] = True
    if args.no_splash:       cfg["splash_enabled"] = False
    if args.devtools:        cfg["devtools"] = True

    # ── Pre-flight checks ─────────────────────────────────────────────────────
    errors = []
    if not cfg["input_folder"] or not os.path.isdir(cfg["input_folder"]):
        errors.append(f"Input folder not found: {cfg['input_folder']!r}")
    elif not os.path.exists(os.path.join(cfg["input_folder"], "index.html")):
        errors.append("No index.html in input folder")
    if not cfg["output_folder"]:
        errors.append("Output folder not set (use --output)")

    if errors:
        print()
        for e in errors:
            print(f"  ✘ {e}")
        print()
        print("  Use --help for usage information.")
        sys.exit(1)

    os.makedirs(cfg["output_folder"], exist_ok=True)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print(f"  App Name  : {cfg['app_name']} v{cfg['version']}")
    print(f"  Input     : {cfg['input_folder']}")
    print(f"  Output    : {cfg['output_folder']}")
    print(f"  Window    : {cfg['width']}×{cfg['height']}"
          f"  Fullscreen={cfg['fullscreen']}  Resizable={cfg['resizable']}")
    print(f"  Splash    : {'enabled ' + str(cfg['splash_duration']) + 'ms' if cfg['splash_enabled'] else 'disabled'}")
    print(f"  DevTools  : {'enabled' if cfg['devtools'] else 'disabled'}")
    if cfg.get("icon"):
        print(f"  Icon      : {cfg['icon']}")
    print()
    print("  Starting build...")
    print()

    # ── Build ─────────────────────────────────────────────────────────────────
    engine = BuildEngine()
    start  = time.time()

    try:
        out_path = engine.build(cfg, progress_cb)
        elapsed  = time.time() - start
        print()
        print(f"  ✔ Build complete in {elapsed:.1f}s")
        print(f"  Output: {out_path}")
        print()
        print(f"  {AUTHOR}")
        print(f"  {AUTHOR_URL}")
        print()
    except Exception as ex:
        elapsed = time.time() - start
        print()
        print(f"  ✘ Build failed after {elapsed:.1f}s")
        print(f"  Error: {ex}")
        print()
        print("  Check build_log.txt in your output folder for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
