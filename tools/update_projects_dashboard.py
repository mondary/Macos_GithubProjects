#!/usr/bin/env python3
from __future__ import annotations

import dataclasses
import datetime as _dt
import json
import os
import subprocess
from pathlib import Path


# Fix paths based on actual structure
ROOT_HUB = Path(__file__).resolve().parents[3] # /Users/clm/Documents/GitHub
PROJECTS_DIR = ROOT_HUB / "PROJECTS" # /Users/clm/Documents/GitHub/PROJECTS
REPO_ROOT = ROOT_HUB / "PROJECTS" / "Macos_GithubProjects" # /Users/clm/Documents/GitHub/PROJECTS/Macos_GithubProjects
PROJECTS_MD = REPO_ROOT / "projects.md"
DASHBOARD_HTML = REPO_ROOT / "dashboard-projets.html"

EXCLUDE_NAMES = {".git", "node_modules", ".DS_Store"}


def _is_excluded(name: str) -> bool:
    if not name:
        return True
    if name in EXCLUDE_NAMES:
        return True
    if name.startswith("."):
        return True
    if name.startswith("-"):
        return True
    return False


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _readme_description(project_path: Path) -> str | None:
    if project_path.is_file():
        return None

    candidates: list[Path] = []
    for pattern in ("README.md", "readme.md", "README.MD", "README", "readme"):
        p = project_path / pattern
        if p.exists() and p.is_file():
            candidates.append(p)
    if not candidates:
        for p in project_path.glob("README*"):
            if p.is_file():
                candidates.append(p)
                break
    if not candidates:
        return None

    try:
        text = candidates[0].read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and not ln.startswith("```")]
    if not lines:
        return None

    for ln in lines[:60]:
        if ln.startswith("#") or ln.startswith("!") or ln.startswith(">"):
            continue
        return ln[:240]

    first = lines[0].lstrip("#").strip()
    return first[:240] if first else None


def _group_key(name: str) -> str:
    for sep in ("_", "-"):
        if sep in name:
            head = name.split(sep, 1)[0].strip()
            if head:
                return head.upper()
    return "OTHER"


@dataclasses.dataclass(frozen=True)
class GitInfo:
    is_git: bool
    dirty: bool
    has_remote: bool
    remote_url: str | None


def _git_info(project_path: Path) -> GitInfo:
    cwd = project_path if project_path.is_dir() else project_path.parent
    inside = _run(["git", "-C", str(cwd), "rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0 or inside.stdout.strip().lower() != "true":
        return GitInfo(False, False, False, None)

    porcelain = _run(["git", "-C", str(cwd), "status", "--porcelain"])
    dirty = bool(porcelain.stdout.strip())

    remote_url = None
    has_remote = False
    remote = _run(["git", "-C", str(cwd), "remote", "get-url", "origin"])
    if remote.returncode == 0:
        remote_url = remote.stdout.strip() or None
        has_remote = bool(remote_url)
    else:
        remotes = _run(["git", "-C", str(cwd), "remote", "-v"])
        if remotes.returncode == 0 and remotes.stdout.strip():
            first = remotes.stdout.splitlines()[0].strip()
            parts = first.split()
            if len(parts) >= 2:
                remote_url = parts[1]
                has_remote = True

    return GitInfo(True, dirty, has_remote, remote_url)


@dataclasses.dataclass(frozen=True)
class Project:
    name: str
    rel_path: str
    is_dir: bool
    group: str
    description: str | None
    has_icon: bool
    git: GitInfo


def _discover_projects() -> list[Project]:
    if not PROJECTS_DIR.exists():
        raise SystemExit(f"Missing folder: {PROJECTS_DIR}")

    projects: list[Project] = []
    for child in sorted(PROJECTS_DIR.iterdir(), key=lambda p: p.name.lower()):
        if _is_excluded(child.name):
            continue
        rel_path = os.path.relpath(child, REPO_ROOT)
        desc = _readme_description(child)
        icon_path = child / "icon.png" if child.is_dir() else None
        has_icon = bool(icon_path and icon_path.exists() and icon_path.is_file())
        group = _group_key(child.name)
        git = _git_info(child)
        projects.append(
            Project(
                name=child.name,
                rel_path=rel_path,
                is_dir=child.is_dir(),
                group=group,
                description=desc,
                has_icon=has_icon,
                git=git,
            )
        )
    return projects


def _write_projects_md(projects: list[Project]) -> None:
    by_group: dict[str, list[Project]] = {}
    for p in projects:
        by_group.setdefault(p.group, []).append(p)

    groups = sorted(by_group.keys(), key=lambda g: (g == "OTHER", g))
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines: list[str] = []
    lines.append("# 📁 Mes projets")
    lines.append("")
    lines.append(f"> Source: `{PROJECTS_DIR}`")
    lines.append(f"> Généré: **{now}**")
    lines.append("")
    lines.append("## 🧭 Sommaire")
    lines.append("")
    lines.append(" | ".join([f"{g} ({len(by_group[g])})" for g in groups]) or "_(aucun)_")
    lines.append("")
    lines.append(f"> Total: **{len(projects)}** projets détectés.")
    lines.append("")

    for g in groups:
        lines.append(f"## {g}")
        lines.append("")
        for p in by_group[g]:
            warn: list[str] = []
            if not p.description:
                warn.append("⚠️ no desc")
            if p.is_dir and not p.has_icon:
                warn.append("⚠️ no icon.png")
            if not p.git.is_git:
                warn.append("⚠️ no git")
            elif not p.git.has_remote:
                warn.append("⚠️ no remote")
            if p.git.dirty:
                warn.append("✳️ dirty")

            desc = p.description or "Description non disponible."
            suffix = f"`{p.rel_path}`"
            lines.append(f"- **{p.name}** — {desc} ({suffix})" + (f" {' '.join(warn)}" if warn else ""))
        lines.append("")

    PROJECTS_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _html_template(projects: list[Project]) -> str:
    data = [
        {
            "name": p.name,
            "path": p.rel_path,
            "group": p.group,
            "description": p.description or "",
            "iconPath": (f"{p.rel_path}/icon.png" if (p.is_dir and p.has_icon) else None),
            "git": {
                "isGit": p.git.is_git,
                "dirty": p.git.dirty,
                "hasRemote": p.git.has_remote,
                "remoteUrl": p.git.remote_url,
            },
        }
        for p in projects
    ]
    payload = json.dumps(
        {
            "generatedAt": _dt.datetime.now().isoformat(timespec="seconds"),
            "root": str(REPO_ROOT),
            "projects": data,
        },
        ensure_ascii=False,
    )
    payload_safe = (
        payload.replace("</", "<\\/")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )

    # Design base: PROJECTS/Web_SKILLS.shwebsite/index.html
    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>POUARK - Projects</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/geist@1.0.0/dist/mono.min.css">
    <style>
        :root {{
            --background: #000000;
            --foreground: #ededed;
            --ds-gray-100: #1a1a1a;
            --ds-gray-200: #1f1f1f;
            --ds-gray-400: #2e2e2e;
            --ds-gray-500: #454545;
            --ds-gray-600: #878787;
            --ds-gray-700: #8f8f8f;
            --ds-gray-900: #a0a0a0;
            --ds-gray-1000: #ededed;
            --border: var(--ds-gray-200);
            --good: #39d98a;
            --warn: #ffcc00;
            --bad: #ff4d4d;
            --font-mono: "Geist Mono", "Fira Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--background);
            color: var(--foreground);
            font-family: var(--font-mono);
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
            padding: 0 1rem;
        }}

        a {{
            color: inherit;
            text-decoration: none;
            transition: color 0.15s;
        }}

        .container {{
            max-width: 72rem; /* max-w-6xl */
            margin: 0 auto;
        }}

        /* Background: keep pure black */

        /* Header / Nav */
        header.site-nav {{
            position: relative;
            background-color: var(--background);
            height: 3.5rem; /* h-14 */
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border);
            margin-bottom: 2rem;
            width: 100vw;
            margin-left: calc(50% - 50vw);
            margin-right: calc(50% - 50vw);
        }}

        .site-nav-inner {{
            max-width: 72rem;
            margin: 0 auto;
            padding: 0 1rem;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .nav-left {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .nav-right {{
            display: flex;
            align-items: baseline;
            gap: 1rem;
            font-size: 0.875rem; /* text-sm */
            color: var(--ds-gray-600);
        }}

        /* Hero Section */
        .hero {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 2.5rem;
            margin: 1.75rem 0; /* my-7 */
        }}

        @media (min-width: 64rem) {{
            .hero {{
                grid-template-columns: auto 1fr;
                gap: 3.5rem;
            }}
        }}

        .ascii-container {{
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }}

        .ascii-art {{
            font-family: "Fira Mono", var(--font-mono);
            font-size: 12px;
            line-height: 1.25;
            letter-spacing: -1px;
            color: var(--ds-gray-700);
            white-space: pre;
            select: none;
        }}

        @media (min-width: 64rem) {{
            .ascii-art {{
                font-size: 15px;
            }}
        }}

        .hero-title {{
            font-size: 15px;
            letter-spacing: -0.025em; /* tracking-tight */
            font-weight: 500;
            text-transform: uppercase;
            color: var(--foreground);
        }}

        @media (min-width: 64rem) {{
            .hero-title {{
                font-size: 19px;
            }}
        }}

        .hero-description {{
            color: var(--ds-gray-600);
            font-size: 1.25rem; /* text-xl */
            max-width: 100%;
            line-height: 1.25;
            letter-spacing: -0.025em;
        }}

        @media (min-width: 40rem) {{
            .hero-description {{
                font-size: 1.5rem; /* text-2xl */
            }}
        }}

        /* Search Bar */
        .search-container {{
            margin-bottom: 1.5rem;
            position: relative;
        }}

        .search-input {{
            width: 100%;
            background: transparent;
            border: none;
            border-bottom: 1px solid var(--ds-gray-400);
            padding: 0.75rem 0 0.75rem 2rem;
            font-family: var(--font-mono);
            color: var(--ds-gray-600);
            outline: none;
        }}

        .search-icon {{
            position: absolute;
            left: 0;
            top: 50%;
            transform: translateY(-50%);
            color: var(--ds-gray-600);
        }}

        /* Sticky controls (search + filters) */
        .controls-sticky {{
            position: sticky;
            top: 0;
            z-index: 50;
            background: var(--background);
            padding-top: 0.75rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--border);
            margin-bottom: 1.25rem;
            width: 100vw;
            margin-left: calc(50% - 50vw);
            margin-right: calc(50% - 50vw);
        }}

        .controls-inner {{
            max-width: 72rem;
            margin: 0 auto;
            padding: 0 1rem;
        }}

        /* Tabs */
        .tabs {{
            display: flex;
            gap: 1rem;
            margin-bottom: 0;
            font-size: 0.875rem;
            flex-wrap: wrap;
        }}

        .tab {{
            padding-bottom: 0.25rem;
            border-bottom: 2px solid transparent;
            color: var(--ds-gray-600);
            cursor: pointer;
        }}

        .tab.active {{
            border-bottom-color: var(--foreground);
            color: var(--foreground);
        }}

        .filter-row {{
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: center;
            margin-top: 0.75rem;
        }}

        .chips {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: nowrap;
            align-items: center;
            overflow-x: auto;
            overflow-y: hidden;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: thin;
            position: relative;
        }}

        .chip {{
            font-size: 0.75rem;
            color: var(--ds-gray-600);
            border: none;
            padding: 0.15rem 0;
            border-bottom: 2px solid transparent;
            cursor: pointer;
            user-select: none;
            transition: color 0.15s, border-color 0.15s;
            white-space: nowrap;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
        }}

        .chip:hover {{
            color: var(--foreground);
            border-bottom-color: var(--ds-gray-400);
        }}

        .chip.active {{
            color: var(--foreground);
            border-bottom-color: var(--foreground);
        }}

        .chip svg {{
            width: 12px;
            height: 12px;
            display: inline-block;
        }}

        .chip.pin {{
            position: sticky;
            left: 0;
            z-index: 5;
            background: var(--background);
            padding-right: 0.6rem;
            margin-right: 0.2rem;
            box-shadow: 12px 0 0 0 var(--background);
        }}

        /* Table */
        .leaderboard {{
            width: 100%;
            min-height: 400px;
        }}

        .list-header {{
            display: none;
        }}

        @media (min-width: 64rem) {{
            .list-header {{
                display: grid;
                grid-template-columns: repeat(16, minmax(0, 1fr));
                gap: 1rem;
                border-bottom: 1px solid var(--border);
                padding: 0.75rem 0;
                font-size: 0.875rem;
                font-weight: 500;
                text-transform: uppercase;
                color: var(--ds-gray-600);
            }}
        }}

        .list-row {{
            display: grid;
            grid-template-columns: auto 1fr auto;
            gap: 0.75rem;
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border);
            align-items: center;
            transition: background 0.1s;
        }}

        @media (min-width: 64rem) {{
            .list-row {{
                grid-template-columns: repeat(16, minmax(0, 1fr));
                gap: 1rem;
            }}
        }}

        .list-row:hover {{
            background-color: rgba(255, 255, 255, 0.05);
        }}

        .col-rank {{
            color: var(--ds-gray-600);
            font-size: 0.875rem;
        }}

        @media (min-width: 64rem) {{ .col-rank {{ grid-column: span 1; }} }}

        .col-skill {{
            display: flex;
            flex-direction: column;
            min-width: 0;
        }}

        @media (min-width: 64rem) {{
            .col-skill {{
                grid-column: span 13;
                flex-direction: row;
                align-items: baseline;
                gap: 0.5rem;
                min-width: 0;
                flex-wrap: wrap;
            }}
        }}

        .proj-wrap {{
            display: flex;
            align-items: flex-start;
            gap: 0.6rem;
            min-width: 0;
            flex: 0 1 auto;
        }}

        .proj-icon {{
            width: 44px;
            height: 44px;
            border-radius: 10px;
            border: 1px solid var(--border);
            background: var(--ds-gray-100);
            overflow: hidden;
            flex: 0 0 auto;
            display: grid;
            place-items: center;
        }}

        .proj-icon img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }}

        .proj-icon .fallback {{
            width: 18px;
            height: 18px;
            background: var(--ds-gray-600);
            clip-path: polygon(50% 0%, 100% 100%, 0% 100%);
            opacity: 0.9;
        }}

        .proj-text {{
            min-width: 0;
            flex: 1 1 auto;
            display: flex;
            flex-direction: column;
        }}

        .skill-name {{
            font-weight: 600;
            font-size: 1rem;
            min-width: 0;
            white-space: normal;
            overflow: visible;
            text-overflow: clip;
        }}

        .skill-source {{
            color: var(--ds-gray-600);
            font-size: 0.75rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            min-width: 0;
            flex: 1 1 auto;
        }}

        @media (min-width: 64rem) {{
            /* keep title readable; truncate description harder */
            .skill-source {{
                flex-basis: 100%;
                max-width: 100%;
            }}
        }}

        @media (min-width: 64rem) {{ .skill-source {{ font-size: 0.875rem; }} }}

        .col-installs {{
            text-align: right;
            font-size: 0.875rem;
            white-space: nowrap;
        }}

        @media (min-width: 64rem) {{ .col-installs {{ grid-column: span 2; }} }}

        .pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            font-size: 0.75rem;
            color: var(--ds-gray-600);
        }}

        .dot {{
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: var(--ds-gray-600);
        }}

        .pill.good {{ color: var(--good); }}
        .pill.good .dot {{ background: var(--good); }}
        .pill.warn {{ color: var(--warn); }}
        .pill.warn .dot {{ background: var(--warn); }}
        .pill.bad {{ color: var(--bad); }}
        .pill.bad .dot {{ background: var(--bad); }}

        .row-actions {{
            display: inline-flex;
            gap: 0.75rem;
            align-items: center;
            justify-content: flex-start;
            margin-top: 0.35rem;
            color: var(--ds-gray-600);
            font-size: 0.75rem;
            flex-wrap: wrap;
        }}

        .row-actions a {{
            text-decoration: underline;
            text-decoration-color: rgba(255,255,255,0.22);
            text-underline-offset: 3px;
        }}

        .row-actions a:hover {{
            color: var(--foreground);
            text-decoration-color: rgba(255,255,255,0.5);
        }}

        .row-actions button {{
            appearance: none;
            background: transparent;
            border: none;
            padding: 0;
            color: inherit;
            font: inherit;
            cursor: pointer;
            text-decoration: underline;
            text-decoration-color: rgba(255,255,255,0.22);
            text-underline-offset: 3px;
        }}

        .row-actions button:hover {{
            color: var(--foreground);
            text-decoration-color: rgba(255,255,255,0.5);
        }}

        .toast {{
            position: fixed;
            left: 50%;
            bottom: 18px;
            transform: translateX(-50%);
            padding: 10px 12px;
            border: 1px solid var(--border);
            background: rgba(0,0,0,0.88);
            color: var(--foreground);
            border-radius: 12px;
            font-size: 0.875rem;
            z-index: 60;
            display: none;
            white-space: nowrap;
        }}

        .palette {{
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.55);
            z-index: 70;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }}

        .palette-panel {{
            width: min(640px, 100%);
            border: 1px solid var(--border);
            background: #000;
            border-radius: 14px;
            overflow: hidden;
        }}

        .palette-head {{
            padding: 0.75rem 0.85rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 1rem;
            color: var(--ds-gray-600);
            font-size: 0.75rem;
        }}

        .palette-title {{
            color: var(--foreground);
            font-size: 0.875rem;
        }}

        .palette-actions {{
            padding: 0.75rem 0.85rem;
            display: grid;
            gap: 0.5rem;
        }}

        .opt {{
            border: 1px solid var(--border);
            background: transparent;
            color: var(--foreground);
            border-radius: 12px;
            padding: 0.65rem 0.75rem;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            text-align: left;
        }}

        .opt:hover {{
            border-color: var(--ds-gray-400);
        }}

        .opt kbd {{
            border: 1px solid var(--border);
            border-bottom-color: var(--ds-gray-400);
            border-radius: 8px;
            padding: 0.15rem 0.45rem;
            color: var(--ds-gray-600);
            font-size: 0.75rem;
        }}

        /* Icon Placeholder */
        .icon {{
            width: 1.125rem;
            height: 1.125rem;
            background: var(--foreground);
            clip-path: polygon(50% 0%, 100% 100%, 0% 100%);
        }}
    </style>
</head>
<body>

<div class="container">
    <header class="site-nav">
        <div class="site-nav-inner">
            <div class="nav-left">
                <div class="icon"></div>
                <span style="font-weight: 500; font-size: 1.125rem;">Projects dashboard</span>
            </div>
            <nav class="nav-right">
                <span id="meta-count"></span>
                <span id="meta-generated"></span>
            </nav>
        </div>
    </header>

    <main>
        <section class="hero">
            <div class="ascii-container">
                <pre class="ascii-art">
	██████╗ ██████╗  ██████╗      ██╗███████╗ ██████╗████████╗ ███████╗
	██╔══██╗██╔══██╗██╔═══██╗     ██║██╔════╝██╔════╝╚══██╔══╝ ██╔════╝
	██████╔╝██████╔╝██║   ██║     ██║█████╗  ██║        ██║    ███████╗
	██╔═══╝ ██╔══██╗██║   ██║██   ██║██╔══╝  ██║        ██║    ╚════██║
	██║     ██║  ██║╚██████╔╝╚█████╔╝███████╗╚██████╗   ██║    ███████║
	╚═╝     ╚═╝  ╚═╝ ╚═════╝  ╚════╝ ╚══════╝ ╚═════╝   ╚═╝    ╚══════╝</pre>
                <p class="hero-title"></p>
            </div>
            <div>
                <p class="hero-description">
                    Search projects, check git status (clean/dirty), and detect remote (GitHub).
                </p>
            </div>
        </section>

        <div class="controls-sticky">
            <div class="controls-inner">
                <div class="search-container" style="margin-bottom: 0;">
                    <span class="search-icon">
                        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.34-4.34"/></svg>
                    </span>
                <input id="q" type="text" class="search-input" placeholder="Search projects...">
            </div>

                <div class="filter-row">
                    <div class="chips" id="chips"></div>
                </div>
            </div>
        </div>

        <div class="leaderboard">
            <div class="list-header">
                <div style="grid-column: span 1;">#</div>
                <div style="grid-column: span 13;">Project</div>
                <div style="grid-column: span 2; text-align: right;">Status</div>
            </div>
            <div id="rows"></div>
        </div>
    </main>
</div>

<div class="toast" id="toast" role="status" aria-live="polite"></div>
<div class="palette" id="palette" aria-hidden="true">
  <div class="palette-panel" role="dialog" aria-modal="true" aria-label="Options">
    <div class="palette-head">
      <div class="palette-title">Options</div>
      <div>Press <span style="color:var(--foreground);">Esc</span> to close</div>
    </div>
    <div class="palette-actions">
      <button class="opt" id="opt-vscode" type="button">
        <span>Open in VS Code</span>
        <kbd>V</kbd>
      </button>
      <button class="opt" id="opt-cursor" type="button">
        <span>Open in Cursor</span>
        <kbd>U</kbd>
      </button>
      <button class="opt" id="opt-antigravity" type="button">
        <span>Open in Antigravity</span>
        <kbd>A</kbd>
      </button>
      <button class="opt" id="opt-copy-path" type="button">
        <span>Copy path</span>
        <kbd>C</kbd>
      </button>
    </div>
  </div>
</div>

<script id="data" type="application/json">{payload_safe}</script>
<script>
  const data = JSON.parse(document.getElementById("data").textContent);
	  const projects = data.projects || [];
  const rows = document.getElementById("rows");
  const q = document.getElementById("q");
  const chips = document.getElementById("chips");
  const toast = document.getElementById("toast");
  const palette = document.getElementById("palette");
  const optVscode = document.getElementById("opt-vscode");
  const optCursor = document.getElementById("opt-cursor");
  const optAntigravity = document.getElementById("opt-antigravity");
  const optCopyPath = document.getElementById("opt-copy-path");
  const metaCount = document.getElementById("meta-count");
  const metaGenerated = document.getElementById("meta-generated");
  metaGenerated.textContent = "generated: " + data.generatedAt;

  let selectedProject = null;

  let toastTimer = null;
  function showToast(text) {{
    if (!toast) return;
    toast.textContent = text;
    toast.style.display = "block";
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {{ toast.style.display = "none"; }}, 1400);
  }}

  async function copyText(text) {{
    try {{
      await navigator.clipboard.writeText(text);
      showToast("copied");
    }} catch (e) {{
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      showToast("copied");
    }}
  }}

  function absPath(relPath) {{
    const root = (data.root || "").toString().replace(/\\/$/, "");
    const rel = (relPath || "").toString();
    if (!root) return rel;
    return root + "/" + rel;
  }}

  function selectDefaultProject() {{
    return projects[0] || null;
  }}

  function setSelectedProject(p) {{
    selectedProject = p;
  }}

  function openPalette() {{
    if (!palette) return;
    if (!selectedProject) selectedProject = selectDefaultProject();
    palette.style.display = "flex";
    palette.setAttribute("aria-hidden", "false");
  }}

  function closePalette() {{
    if (!palette) return;
    palette.style.display = "none";
    palette.setAttribute("aria-hidden", "true");
  }}

  async function openInVSCode(p) {{
    const abs = absPath(p.path);
    // Try URL scheme; then copy command fallback.
    try {{
      window.location.href = "vscode://file/" + encodeURIComponent(abs);
    }} catch (_) {{}}
    await copyText('code "' + abs.replace(/"/g, '\\"') + '"');
  }}

  async function openInCursor(p) {{
    const abs = absPath(p.path);
    // Best-effort URL scheme; then copy command fallback.
    try {{
      window.location.href = "cursor://file/" + encodeURIComponent(abs);
    }} catch (_) {{}}
    await copyText('open -a "/Applications/Cursor.app" "' + abs.replace(/"/g, '\\"') + '"');
  }}

  async function openInAntigravity(p) {{
    const abs = absPath(p.path);
    const cmd = 'open -a "/Applications/Antigravity.app" "' + abs.replace(/"/g, '\\"') + '"';
    await copyText(cmd);
    const scheme = "antigravity://open?path=" + encodeURIComponent(abs);
    setTimeout(() => {{ window.location.href = scheme; }}, 50);
  }}

  let activeGitFilter = ""; // "" | CLEAN | DIRTY | NOREMOTE | NOGIT
  let activeGroup = "ALL";

	  function matchesGit(p) {{
	    if (!activeGitFilter) return true;
	    const isGit = !!p.git?.isGit;
	    const dirty = !!p.git?.dirty;
	    const hasRemote = !!p.git?.hasRemote;
	    if (activeGitFilter === "CLEAN") return isGit && !dirty;
	    if (activeGitFilter === "DIRTY") return isGit && dirty;
	    if (activeGitFilter === "NOREMOTE") return isGit && !hasRemote;
	    if (activeGitFilter === "NOGIT") return !isGit;
	    return true;
	  }}

  function matchesGroup(p) {{
    if (activeGroup === "ALL") return true;
    return (p.group || "OTHER") === activeGroup;
  }}

  function pillFor(p) {{
    if (!p.git?.isGit) return {{ cls: "bad", text: "no git" }};
    if (p.git?.dirty) return {{ cls: "warn", text: "dirty" }};
    if (!p.git?.hasRemote) return {{ cls: "warn", text: "no remote" }};
    return {{ cls: "good", text: "clean" }};
  }}

  function pathToHref(relPath) {{
    return (relPath || "").toString().split("/").map(encodeURIComponent).join("/");
  }}

	  function groupList(items) {{
	    const s = new Set(items.map(p => p.group || "OTHER"));
	    return Array.from(s).sort((a, b) => {{
	      if (a === "OTHER") return 1;
	      if (b === "OTHER") return -1;
	      return a.localeCompare(b);
	    }});
	  }}

	  function gitIcon() {{
	    return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M16 3 21 8l-8 8a3 3 0 0 1-4 0L3 10l5-5"/><path d="M7 7 17 17"/><circle cx="9" cy="9" r="1.2"/><circle cx="15" cy="15" r="1.2"/></svg>`;
	  }}

	  function renderChips() {{
	    if (!chips) return;
	    const groups = groupList(projects);
	    chips.innerHTML = "";

	    const make = (label, value, kind) => {{
	      const el = document.createElement("div");
	      el.className = "chip";
	      if (kind === "git") {{
	        el.innerHTML = gitIcon() + label;
	        el.classList.toggle("active", value === activeGitFilter);
	      }} else {{
	        el.textContent = label;
	        el.classList.toggle("active", value === activeGroup);
	      }}
	      el.addEventListener("click", () => {{
	        if (kind === "git") {{
	          activeGitFilter = value;
	        }} else {{
	          activeGroup = value;
	        }}
	        renderChips();
	        render();
	      }});
	      return el;
	    }};

	    // Groups (plain text)
	    const allChip = make("ALL", "ALL", "group");
	    allChip.classList.add("pin");
	    chips.appendChild(allChip);
	    for (const g of groups) chips.appendChild(make(g, g, "group"));

	    // Git filters (same chip format, git icon)
	    chips.appendChild(make("Clean", "CLEAN", "git"));
	    chips.appendChild(make("Dirty", "DIRTY", "git"));
	    chips.appendChild(make("No remote", "NOREMOTE", "git"));
	    chips.appendChild(make("No git", "NOGIT", "git"));
	  }}

	  function render() {{
	    const query = (q.value || "").trim().toLowerCase();
	    const filtered = projects.filter(p => {{
	      if (!matchesGit(p)) return false;
	      if (!matchesGroup(p)) return false;
	      if (!query) return true;
	      const hay = [p.name, p.description, p.group, p.path, p.git?.remoteUrl || ""].join(" ").toLowerCase();
	      return hay.includes(query);
	    }});

    metaCount.textContent = "items: " + filtered.length;
    if (!q.value) {{
      q.placeholder = "Search projects... (" + filtered.length + " items)";
    }}
    rows.innerHTML = "";

      filtered.forEach((p, idx) => {{
      const row = document.createElement("div");
      row.className = "list-row";

      const rank = document.createElement("div");
      rank.className = "col-rank";
      rank.textContent = String(idx + 1);

      const col = document.createElement("div");
      col.className = "col-skill";

      const wrap = document.createElement("div");
      wrap.className = "proj-wrap";

      const icon = document.createElement("div");
      icon.className = "proj-icon";
      if (p.iconPath) {{
        const img = document.createElement("img");
        img.alt = "";
        img.loading = "lazy";
        img.src = absPath(p.iconPath);
        icon.appendChild(img);
      }} else {{
        const fb = document.createElement("div");
        fb.className = "fallback";
        icon.appendChild(fb);
      }}

      const text = document.createElement("div");
      text.className = "proj-text";

      const name = document.createElement("span");
      name.className = "skill-name";
      name.textContent = p.name;

      const src = document.createElement("span");
      src.className = "skill-source";
      const parts = [];
      parts.push(p.path);
      if (p.git?.remoteUrl) parts.push(p.git.remoteUrl);
      const desc = p.description ? (" — " + p.description) : "";
      src.textContent = parts.join(" • ") + desc;

      text.appendChild(name);
      text.appendChild(src);

      wrap.appendChild(icon);
      wrap.appendChild(text);

      col.appendChild(wrap);

      const status = document.createElement("div");
      status.className = "col-installs";
      const pill = pillFor(p);
      status.innerHTML = '<span class="pill ' + pill.cls + '"><span class="dot"></span>' + pill.text + '</span>';

      const actions = document.createElement("span");
      actions.className = "row-actions";

      const aLocal = document.createElement("a");
      aLocal.href = pathToHref(p.path);
      aLocal.textContent = "local";
      aLocal.addEventListener("click", (e) => e.stopPropagation());
      actions.appendChild(aLocal);

      const aGh = document.createElement("a");
      aGh.textContent = "github";
      if (p.git?.remoteUrl) {{
        aGh.href = p.git.remoteUrl;
        aGh.target = "_blank";
        aGh.rel = "noreferrer";
      }} else {{
        aGh.href = "#";
        aGh.style.opacity = "0.45";
        aGh.style.pointerEvents = "none";
      }}
      aGh.addEventListener("click", (e) => e.stopPropagation());
      actions.appendChild(aGh);

      const bFinder = document.createElement("button");
      bFinder.type = "button";
      bFinder.textContent = "finder";
      bFinder.addEventListener("click", (e) => {{
        e.stopPropagation();
        const cmd = 'open -R "' + absPath(p.path).replace(/"/g, '\\"') + '"';
        copyText(cmd);
      }});
      actions.appendChild(bFinder);

      const bOpenWith = document.createElement("button");
      bOpenWith.type = "button";
      bOpenWith.textContent = "edit";
      bOpenWith.addEventListener("click", (e) => {{
        e.stopPropagation();
        const abs = absPath(p.path).replace(/"/g, '\\"');
        const cmd = 'open -a "/Applications/Antigravity.app" "' + abs + '"';
        // Always copy fallback command, then try deep-link scheme.
        copyText(cmd);
        const scheme = "antigravity://open?path=" + encodeURIComponent(absPath(p.path));
        setTimeout(() => {{ window.location.href = scheme; }}, 50);
      }});
      actions.appendChild(bOpenWith);

      text.appendChild(actions);

      row.addEventListener("click", () => {{
        setSelectedProject(p);
        openPalette();
      }});

      row.appendChild(rank);
      row.appendChild(col);
      row.appendChild(status);
      rows.appendChild(row);
    }});
  }}

  q.addEventListener("input", render);
  renderChips();
  render();

	  // Global: type anywhere -> focus search. '/' or '?' opens palette.
	  window.addEventListener("keydown", (e) => {{
	    const t = e.target;
	    const tag = (t && t.tagName) ? t.tagName.toLowerCase() : "";
	    const isEditable = tag === "input" || tag === "textarea" || (t && t.isContentEditable);
	    if (isEditable) return;

	    if (e.key === "/" || e.key === "?") {{
	      e.preventDefault();
	      openPalette();
	      return;
	    }}

	    if (e.key === "Escape") {{
	      if (palette && palette.style.display === "flex") {{
	        closePalette();
	      }} else {{
	        q.value = "";
	        q.blur();
	        render();
	      }}
	      return;
	    }}

	    if (palette && palette.style.display === "flex") {{
	      const k = (e.key || "").toLowerCase();
	      if (k === "v") {{
	        e.preventDefault();
	        if (selectedProject) openInVSCode(selectedProject);
	        closePalette();
	      }}
	      if (k === "u") {{
	        e.preventDefault();
	        if (selectedProject) openInCursor(selectedProject);
	        closePalette();
	      }}
	      if (k === "a") {{
	        e.preventDefault();
	        if (selectedProject) openInAntigravity(selectedProject);
	        closePalette();
	      }}
	      if (k === "c") {{
	        e.preventDefault();
	        if (selectedProject) copyText(absPath(selectedProject.path));
	        closePalette();
	      }}
	      return;
	    }}

	    if (e.metaKey || e.ctrlKey || e.altKey) return;
	    if (e.key === "f") {{
	      q.focus();
	      q.select();
	      e.preventDefault();
	      return;
	    }}
	    if (e.key && e.key.length === 1) {{
	      q.focus();
	      q.value = q.value + e.key;
	      render();
	      e.preventDefault();
	    }}
	  }}, {{ passive: false }});

  palette?.addEventListener("click", (e) => {{
    if (e.target === palette) closePalette();
  }});

  optVscode?.addEventListener("click", async () => {{
    if (selectedProject) await openInVSCode(selectedProject);
    closePalette();
  }});
  optCursor?.addEventListener("click", async () => {{
    if (selectedProject) await openInCursor(selectedProject);
    closePalette();
  }});
  optAntigravity?.addEventListener("click", async () => {{
    if (selectedProject) await openInAntigravity(selectedProject);
    closePalette();
  }});
  optCopyPath?.addEventListener("click", async () => {{
    if (selectedProject) await copyText(absPath(selectedProject.path));
    closePalette();
  }});
</script>
</body>
</html>
"""


def _write_dashboard_html(projects: list[Project]) -> None:
    DASHBOARD_HTML.write_text(_html_template(projects), encoding="utf-8")


def main() -> None:
    projects = _discover_projects()
    _write_projects_md(projects)
    _write_dashboard_html(projects)


if __name__ == "__main__":
    main()
