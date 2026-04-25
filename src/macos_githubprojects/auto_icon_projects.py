#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = REPO_ROOT.parent

EXCLUDE_NAMES = {".git", "node_modules", ".DS_Store"}


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _is_excluded(name: str) -> bool:
    if not name:
        return True
    if name in EXCLUDE_NAMES:
        return True
    if name.startswith(".") or name.startswith("-"):
        return True
    return False


@dataclass(frozen=True)
class GitInfo:
    is_git: bool
    dirty: bool
    has_remote: bool


def _git_info(project_path: Path) -> GitInfo:
    inside = _run(["git", "-C", str(project_path), "rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0 or inside.stdout.strip().lower() != "true":
        return GitInfo(False, False, False)

    porcelain = _run(["git", "-C", str(project_path), "status", "--porcelain"])
    dirty = bool(porcelain.stdout.strip())

    origin = _run(["git", "-C", str(project_path), "remote", "get-url", "origin"])
    if origin.returncode == 0 and origin.stdout.strip():
        return GitInfo(True, dirty, True)
    remotes = _run(["git", "-C", str(project_path), "remote"])
    has_remote = remotes.returncode == 0 and bool(remotes.stdout.strip())
    return GitInfo(True, dirty, has_remote)


def _status_key(info: GitInfo) -> str:
    if not info.is_git:
        return "no_git"
    if info.dirty:
        return "dirty"
    if not info.has_remote:
        return "no_remote"
    return "clean"


ICONS = {
    "clean": {
        "symbol": "checkmark.circle.fill",
        "color": "#39d98a",
        "label": "git_clean",
    },
    "dirty": {
        "symbol": "exclamationmark.triangle.fill",
        "color": "#ffcc00",
        "label": "git_dirty",
    },
    "no_remote": {
        "symbol": "icloud.slash.fill",
        "color": "#ff7a00",
        "label": "git_no_remote",
    },
    "no_git": {
        "symbol": "questionmark.circle.fill",
        "color": "#8f8f8f",
        "label": "git_no_git",
    },
}


def _swift_generate_png(out_path: Path, *, symbol: str, color_hex: str, size: int) -> None:
    # Renders SF Symbol -> PNG using AppKit.
    code = f"""
import AppKit

func colorFromHex(_ s: String) -> NSColor {{
  var hex = s.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
  if hex.count == 6 {{ hex = "FF" + hex }}
  var v: UInt64 = 0
  Scanner(string: hex).scanHexInt64(&v)
  let a = CGFloat((v & 0xFF000000) >> 24) / 255.0
  let r = CGFloat((v & 0x00FF0000) >> 16) / 255.0
  let g = CGFloat((v & 0x0000FF00) >> 8) / 255.0
  let b = CGFloat(v & 0x000000FF) / 255.0
  return NSColor(calibratedRed: r, green: g, blue: b, alpha: a)
}}

let out = URL(fileURLWithPath: "{str(out_path).replace('"', '\\"')}")
let size = CGFloat({int(size)})
let imgSize = NSSize(width: size, height: size)

guard let sym = NSImage(systemSymbolName: "{symbol}", accessibilityDescription: nil) else {{
  fputs("missing symbol: {symbol}\\n", stderr)
  exit(2)
}}

let c = colorFromHex("{color_hex}")
let cfg = NSImage.SymbolConfiguration(pointSize: size * 0.62, weight: .semibold)
let symCfg = sym.withSymbolConfiguration(cfg) ?? sym

let result = NSImage(size: imgSize)
result.lockFocus()
NSColor.clear.setFill()
NSBezierPath(rect: NSRect(origin: .zero, size: imgSize)).fill()

let tinted = symCfg.copy() as! NSImage
tinted.isTemplate = true
c.set()
let rect = NSRect(x: 0, y: 0, width: size, height: size)
tinted.draw(in: rect.insetBy(dx: size*0.12, dy: size*0.12), from: .zero, operation: .sourceIn, fraction: 1)

result.unlockFocus()

guard let tiff = result.tiffRepresentation,
      let rep = NSBitmapImageRep(data: tiff),
      let png = rep.representation(using: .png, properties: [:]) else {{
  fputs("png encode failed\\n", stderr)
  exit(3)
}}
try png.write(to: out)
"""
    proc = subprocess.run(
        ["swift", "-"],
        input=code,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"swift render failed for {out_path.name}:\n{proc.stderr.strip()}")


def _ensure_icons(out_dir: Path, *, size: int, regen: bool) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for key, spec in ICONS.items():
        p = out_dir / f"{spec['label']}_{size}.png"
        paths[key] = p
        if p.exists() and not regen:
            continue
        _swift_generate_png(p, symbol=spec["symbol"], color_hex=spec["color"], size=size)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description="Apply Git status folder icons to PROJECTS/* (macOS).")
    ap.add_argument("--size", type=int, default=256, help="PNG size (default: 256).")
    ap.add_argument("--regen", action="store_true", help="Regenerate PNG icons.")
    ap.add_argument("--remove", action="store_true", help="Remove custom icons instead of setting them.")
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Actually write changes. Without this flag, the script runs in dry-run mode.",
    )
    ap.add_argument("--dry-run", action="store_true", help="Alias for not using --apply.")
    args = ap.parse_args()

    if not PROJECTS_DIR.exists():
        raise SystemExit(f"Missing: {PROJECTS_DIR}")

    fileicon = shutil.which("fileicon")
    if not fileicon:
        raise SystemExit(
            "Missing dependency `fileicon`.\n"
            "Install: `brew install fileicon`\n"
            "Then rerun."
        )

    icon_dir = REPO_ROOT / "src" / "tools"
    icons = _ensure_icons(icon_dir, size=args.size, regen=args.regen)

    do_apply = bool(args.apply) and not bool(args.dry_run)

    changed = 0
    scanned = 0
    for child in sorted(PROJECTS_DIR.iterdir(), key=lambda p: p.name.lower()):
        if _is_excluded(child.name):
            continue
        if not child.is_dir():
            continue
        scanned += 1

        info = _git_info(child)
        key = _status_key(info)
        icon_path = icons[key]

        if args.remove:
            cmd = [fileicon, "rm", str(child)]
            if not do_apply:
                print("rm:", child)
                continue
            _run(cmd)
            changed += 1
            continue

        cmd = [fileicon, "set", str(child), str(icon_path)]
        if not do_apply:
            print("set:", child.name, "->", icon_path.name)
            continue

        res = _run(cmd)
        if res.returncode != 0:
            print("fail:", child.name, res.stderr.strip())
            continue
        changed += 1

    print(
        "done."
        f" scanned={scanned}"
        f" changed={changed}"
        f" apply={do_apply}"
        f" remove={bool(args.remove)}"
    )


if __name__ == "__main__":
    main()
