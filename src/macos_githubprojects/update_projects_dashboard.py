#!/usr/bin/env python3
# Ce fichier est gardé pour compatibilité, utilisez plutôt app/scanner.py
from __future__ import annotations

import dataclasses
import datetime as _dt
import json
import os
import subprocess
import urllib.parse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = REPO_ROOT.parent
ROOT_HUB = PROJECTS_DIR.parent
GENERATED_DIR = REPO_ROOT / "generated"
PROJECTS_MD = GENERATED_DIR / "projects.md"
DASHBOARD_HTML = GENERATED_DIR / "dashboard-projets.html"

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

    return GitInfo(True, dirty, has_remote, _sanitize_remote_url(remote_url))


def _sanitize_remote_url(remote_url: str | None) -> str | None:
    if not remote_url:
        return None
    parsed = urllib.parse.urlsplit(remote_url)
    if parsed.scheme and parsed.hostname and parsed.username:
        netloc = parsed.hostname
        if parsed.port:
            netloc += f":{parsed.port}"
        return urllib.parse.urlunsplit(
            (parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)
        )
    return remote_url


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


def _project_path_for_markdown(project: Project, output_dir: Path) -> str:
    project_path = (REPO_ROOT / project.rel_path).resolve()
    return os.path.relpath(project_path, output_dir)


def _render_projects_md(projects: list[Project], output_dir: Path) -> str:
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
            suffix = f"`{_project_path_for_markdown(p, output_dir)}`"
            lines.append(f"- **{p.name}** — {desc} ({suffix})" + (f" {' '.join(warn)}" if warn else ""))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _write_projects_md(projects: list[Project]) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_MD.write_text(_render_projects_md(projects, PROJECTS_MD.parent), encoding="utf-8")


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
    const launcher =
      "http://127.0.0.1:37645/open-vscode?path=" + encodeURIComponent(abs);
    try {{
      const res = await fetch(launcher, {{ method: "GET", mode: "cors" }});
      if (res.ok) return;
    }} catch (_) {{}}

    const fileUrl = "file://" + abs.split("/").map(encodeURIComponent).join("/");
    // Try command URL with newWindow. Copy CLI fallback because vscode://file may reuse a window.
    try {{
      window.location.href =
        "vscode://vscode.open?url=" + encodeURIComponent(fileUrl) + "&newWindow=true";
    }} catch (_) {{}}
    await copyText('code --new-window "' + abs.replace(/"/g, '\\"') + '"');
  }}

  async function openInCursor(p) {{
    const abs = absPath(p.path);
    // Best-effort URL scheme; then copy command fallback.
    try {{
      window.location.href = "cursor://file/" + encodeURIComponent(abs);
    }} catch (_) {{}}
    await copyText('open -a "/Applications/Cursor.app" -n "' + abs.replace(/"/g, '\\"') + '"');
  }}

  async function openInAntigravity(p) {{
    const abs = absPath(p.path);
    const cmd = 'open -a "/Applications/Antigravity.app" "' + abs.replace(/"/g, '\\"') + '"';
    await copyText(cmd);
    const scheme = "antigravity://open?path=" + encodeURIComponent(abs);

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
             bOpenWith.addEventListener("click", async (e) => {{
        e.stopPropagation();
        await openInVSCode(p);
    
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
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_HTML.write_text(_html_template(projects), encoding="utf-8")


def _generate_hub_html(projects: list[Project]) -> None:
    """Generate a standalone hub.html with all projects using the Web_hub template structure."""
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    hub_path = GENERATED_DIR / "hub.html"

    # Ensure assets directory exists
    assets_dir = GENERATED_DIR / "assets" / "images"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Copy background photo if it doesn't exist
    bg_photo_source = REPO_ROOT / "assets" / "images" / "cm_trans.png"
    bg_photo_dest = assets_dir / "cm_trans.png"
    if bg_photo_source.exists() and not bg_photo_dest.exists():
        import shutil
        shutil.copy2(bg_photo_source, bg_photo_dest)

    # Build cards for all projects
    cards_html = []
    for p in projects:
        category = "website"
        category_icon = "globe"

        if p.group.startswith("CHROME"):
            category = "chrome"
            category_icon = "chrome"
        elif p.group.startswith("CLI"):
            category = "cli"
            category_icon = "terminal"
        elif p.group.startswith("MACOS"):
            category = "macos"
            category_icon = "desktop"
        elif p.group.startswith("WEB"):
            category = "web"
            category_icon = "globe"

        # Generate thumbnail - use icon if available, otherwise fallback color
        thumbnail_bg = "#f9fafb"
        if p.has_icon:
            # Use relative path from generated/ directory
            icon_rel = f"../{p.rel_path}/icon.png"
            thumbnail_bg = f"url('{icon_rel}')"

        # Build card HTML
        card_html = f'''        <a class="card" data-category="{category}" href="../{p.rel_path}/" target="_blank" rel="noopener noreferrer">
            <div class="card-img" style="background-image: {thumbnail_bg}; background-size: cover;">
                <div class="category-icon {category}"><i class="fas fa-{category_icon}"></i></div>
            </div>
            <div class="card-content">
                <div class="card-title">{p.name}</div>
            </div>
        </a>'''
        cards_html.append(card_html)

    cards_container = "\n".join(cards_html)

    # Generate complete HTML using Web_hub template structure
    html_content = f'''<!DOCTYPE html>
<html lang="fr">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src https://fonts.gstatic.com https://cdnjs.cloudflare.com; img-src 'self' data: https:; frame-ancestors 'none'; upgrade-insecure-requests;">
    <title>Mes Projets - Portfolio</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="preconnect" href="https://cdnjs.cloudflare.com">
    <link rel="dns-prefetch" href="https://cdnjs.cloudflare.com">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css" integrity="sha512-SnH5WK+bZxgPHs44uWIX+LLJAJ9/2PkPKZ5QiAj6Ta86w+fsb2TkcmfRyVX3pBnMFcV7oQPJkl9QevSCWr3W6A==" crossorigin="anonymous" referrerpolicy="no-referrer" />
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        body {{
            background-color: #ffffff;
            color: #111;
            margin: 0;
            font-family: 'Inter', sans-serif;
            overflow-x: hidden;
            min-height: 150vh;
        }}

        .bg-photo {{
            position: fixed;
            right: -12vw;
            bottom: 0;
            transform: none;
            height: 100vh;
            width: auto;
            max-width: 120vw;
            opacity: 0.08;
            pointer-events: none;
            z-index: 0;
            -webkit-mask-image: linear-gradient(to left, transparent 0%, black 30%, black 60%, transparent 100%);
            mask-image: linear-gradient(to left, transparent 0%, black 30%, black 60%, transparent 100%);
            filter: grayscale(100%);
        }}

        .header-section {{
            padding-top: 80px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
        }}

        .header-title {{
            font-size: 72px;
            font-weight: 700;
            margin-bottom: 24px;
            padding-bottom: 20px;
            letter-spacing: -0.5px;
        }}

        .socials-container {{
            display: flex;
            gap: 12px;
            margin-bottom: 48px;
        }}

        .social-bubble {{
            width: 44px;
            height: 44px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            font-size: 18px;
            font-weight: 600;
            transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            position: relative;
            overflow: hidden;
        }}

        .social-bubble.github {{
            background: #f5f5f5;
            color: #333;
        }}

        .social-bubble.github:hover {{
            background: #333;
            color: #fff;
            transform: translateY(-4px) scale(1.1);
        }}

        .social-bubble i {{
            font-size: 18px;
            color: currentColor;
        }}

        .filters-container {{
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-bottom: 40px;
            flex-wrap: wrap;
            position: sticky;
            top: 0;
            z-index: 20;
            width: 100%;
            box-sizing: border-box;
            background: transparent;
            padding: 12px 16px;
            border-radius: 0;
        }}

        .filters-container.is-stuck {{
            background: rgba(255, 255, 255, 0.92);
            backdrop-filter: blur(6px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.06);
        }}

        .filter-pill {{
            background: #f3f4f6;
            padding: 8px 18px;
            border-radius: 20px;
            font-weight: 500;
            font-size: 13px;
            color: #4b5563;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
            font-family: inherit;
        }}

        .filter-pill.active {{
            background: #111;
            color: #fff;
        }}

        .main-wrapper {{
            position: relative;
            width: 100%;
            max-width: 1280px;
            margin: 0 auto;
            padding: 0 20px;
            min-height: 2000px;
        }}

        .card {{
            position: absolute;
            width: calc(25% - 15px);
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            border: 1px solid #efefef;
            transition:
                transform 1s cubic-bezier(0.25, 1, 0.5, 1),
                left 1s cubic-bezier(0.25, 1, 0.5, 1),
                top 1s cubic-bezier(0.25, 1, 0.5, 1),
                box-shadow 1s cubic-bezier(0.25, 1, 0.5, 1);
            transform-origin: center bottom;
            cursor: pointer;
            will-change: transform, left, top;
            display: block;
            text-decoration: none;
            color: inherit;
        }}

        .card-inner {{
            border-radius: 16px;
            overflow: hidden;
            background: white;
        }}

        .card-img {{
            width: 100%;
            height: 180px;
            background-color: #f9fafb;
            background-size: cover;
            background-position: top center;
            background-repeat: no-repeat;
            position: relative;
        }}

        .card:nth-child(2n) .card-img {{
            height: 240px;
        }}

        .card:nth-child(3n) .card-img {{
            height: 210px;
        }}

        .category-icon {{
            position: absolute;
            top: 10px;
            right: 10px;
            width: 28px;
            height: 28px;
            border-radius: 999px;
            display: grid;
            place-items: center;
            color: #fff;
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.18);
            backdrop-filter: blur(6px);
        }}

        .category-icon i {{
            font-size: 14px;
        }}

        .category-icon.website {{ background: rgba(99, 102, 241, 0.85); }}
        .category-icon.chrome {{ background: rgba(234, 67, 53, 0.85); }}
        .category-icon.cli {{ background: rgba(34, 197, 94, 0.85); }}
        .category-icon.macos {{ background: rgba(102, 51, 153, 0.85); }}
        .category-icon.web {{ background: rgba(16, 185, 129, 0.85); }}

        .card.hidden {{
            opacity: 0;
            transform: scale(0.8) !important;
            pointer-events: none;
        }}

        .card-content {{
            padding: 16px;
            background: white;
            opacity: 1;
        }}

        .card-title {{
            font-size: 15px;
            font-weight: 600;
            line-height: 1.4;
            color: #111;
        }}

        /* STATE: FAN (Default) */
        body:not(.scrolled) .card {{
            left: 50%;
            top: var(--fan-base, 60vh);
            width: clamp(200px, 45vw, 260px);
            box-shadow: 0 20px 40px -5px rgba(0, 0, 0, 0.3);
            z-index: 10;
        }}

        body:not(.scrolled) .card {{
            transform: translate(calc(var(--fan-x, -50%) + var(--fan-dx, 0px)), calc(var(--fan-y, 0px) + var(--fan-dy, 0px))) rotate(var(--fan-rot, 0deg)) scale(var(--fan-scale, 1));
        }}

        body:not(.scrolled) .card:nth-child(n+8) {{
            opacity: 0;
            pointer-events: none;
        }}

        body:not(.scrolled) .card:nth-child(1) {{
            --fan-x: -350%;
            --fan-y: 80px;
            --fan-rot: -26deg;
            --fan-dx: 65px;
            --fan-dy: 100px;
            z-index: 1;
        }}

        body:not(.scrolled) .card:nth-child(2) {{
            --fan-x: -250%;
            --fan-y: 40px;
            --fan-rot: -20deg;
            --fan-dx: 55px;
            --fan-dy: 25px;
            z-index: 2;
        }}

        body:not(.scrolled) .card:nth-child(3) {{
            --fan-x: -150%;
            --fan-y: 15px;
            --fan-rot: -10deg;
            --fan-dx: 10px;
            --fan-dy: -10px;
            z-index: 3;
        }}

        body:not(.scrolled) .card:nth-child(4) {{
            --fan-x: -50%;
            --fan-y: 0px;
            --fan-rot: 0deg;
            --fan-dx: 0px;
            --fan-dy: 0px;
            --fan-scale: 1.1;
            z-index: 4;
        }}

        body:not(.scrolled) .card:nth-child(5) {{
            --fan-x: 50%;
            --fan-y: 15px;
            --fan-rot: 10deg;
            --fan-dx: -5px;
            --fan-dy: -5px;
            z-index: 3;
        }}

        body:not(.scrolled) .card:nth-child(6) {{
            --fan-x: 150%;
            --fan-y: 40px;
            --fan-rot: 20deg;
            --fan-dx: -35px;
            --fan-dy: 35px;
            z-index: 2;
        }}

        body:not(.scrolled) .card:nth-child(7) {{
            --fan-x: 250%;
            --fan-y: 80px;
            --fan-rot: 30deg;
            --fan-dx: -65px;
            --fan-dy: 110px;
            z-index: 1;
        }}

        /* STATE: GRID (Scrolled) */
        body.scrolled .card {{
            transform: rotate(0deg) translate(0, 0) scale(1) !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            opacity: 1;
            pointer-events: auto;
        }}

        body.scrolled .card.hidden {{
            opacity: 0 !important;
            pointer-events: none;
        }}

        body.scrolled .card:hover {{
            transform: translateY(-4px) scale(1.02) !important;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
            z-index: 100;
        }}

        .scroll-hint {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            color: #9ca3af;
            font-size: 13px;
            pointer-events: none;
            transition: opacity 0.3s;
            z-index: 50;
        }}

        body.scrolled .scroll-hint {{
            opacity: 0;
        }}

        @media (max-width: 600px) {{
            .header-section {{
                padding-top: 56px;
            }}

            .header-title {{
                font-size: 56px;
            }}

            .filters-container {{
                gap: 6px;
                margin-bottom: 28px;
            }}

            body:not(.scrolled) .card {{
                width: clamp(170px, 70vw, 240px);
            }}

            .bg-photo {{
                height: 60vh;
                max-width: 140vw;
                right: -20vw;
            }}
        }}
    </style>
</head>

<body>

<img src="assets/images/cm_trans.png" alt="" class="bg-photo">

<div class="header-section">
    <h1 class="header-title">Mes Projets</h1>
    <div class="socials-container">
        <a href="https://github.com/mondary" target="_blank" rel="noopener noreferrer" class="social-bubble github" title="GitHub"><i class="fab fa-github"></i></a>
    </div>
</div>

<div class="filters-container">
    <button type="button" class="filter-pill active" data-filter="all">Tous</button>
    <button type="button" class="filter-pill" data-filter="chrome">Chrome</button>
    <button type="button" class="filter-pill" data-filter="cli">CLI</button>
    <button type="button" class="filter-pill" data-filter="macos">macOS</button>
    <button type="button" class="filter-pill" data-filter="web">Web</button>
</div>

<div class="main-wrapper" id="cards-container">
{cards_container}
</div>

<div class="scroll-hint">Scrollez pour animer</div>

<script>
    (function() {{
        const cards = document.querySelectorAll('.card');
        const pills = document.querySelectorAll('.filter-pill');
        const container = document.getElementById('cards-container');
        const filters = document.querySelector('.filters-container');
        let currentFilter = 'all';

        // Filter counts
        function updateFilterCounts() {{
            const counts = {{}};
            cards.forEach(card => {{
                const category = card.dataset.category;
                counts[category] = (counts[category] || 0) + 1;
            }});
            const total = cards.length;
            pills.forEach(pill => {{
                if (!pill.dataset.label) {{
                    pill.dataset.label = pill.textContent.trim();
                }}
                const label = pill.dataset.label;
                const key = pill.dataset.filter;
                const count = key === 'all' ? total : (counts[key] || 0);
                pill.textContent = `${{label}} (${{count}})`;
            }});
        }}

        // Masonry layout
        function layoutCards() {{
            if (!document.body.classList.contains('scrolled')) return;

            const visibleCards = [...cards].filter(c => !c.classList.contains('hidden'));
            let cols = 4;
            const gap = 20;
            const containerWidth = container.offsetWidth;
            if (containerWidth < 520) cols = 1;
            else if (containerWidth < 820) cols = 2;
            else if (containerWidth < 1100) cols = 3;
            const cardWidth = (containerWidth - gap * (cols - 1)) / cols;
            const colHeights = Array(cols).fill(0);

            visibleCards.forEach((card) => {{
                const shortestCol = colHeights.indexOf(Math.min(...colHeights));
                const left = shortestCol * (cardWidth + gap);
                const top = colHeights[shortestCol];

                card.style.left = left + 'px';
                card.style.top = top + 'px';
                card.style.width = cardWidth + 'px';

                colHeights[shortestCol] += card.offsetHeight + gap;
            }});

            container.style.height = Math.max(...colHeights) + 'px';
        }}

        // Filter
        window.filterCards = function(filter) {{
            currentFilter = filter;
            cards.forEach(card => {{
                const category = card.dataset.category;
                if (filter === 'all' || category === filter || card.dataset.category.includes(filter)) {{
                    card.classList.remove('hidden');
                }} else {{
                    card.classList.add('hidden');
                }}
            }});
            if (!document.body.classList.contains('scrolled')) {{
                document.body.classList.add('scrolled');
            }}
            setTimeout(layoutCards, 50);
        }};

        pills.forEach(pill => {{
            pill.addEventListener('click', (e) => {{
                e.stopPropagation();
                pills.forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                window.filterCards(pill.dataset.filter);
            }});
        }});

        updateFilterCounts();

        // Scroll state
        window.addEventListener('scroll', () => {{
            if (window.scrollY > 40) {{
                if (!document.body.classList.contains('scrolled')) {{
                    document.body.classList.add('scrolled');
                    void document.body.offsetWidth;
                    layoutCards();
                }}
            }} else {{
                if (document.body.classList.contains('scrolled')) {{
                    document.body.classList.remove('scrolled');
                    clearCardStyles();
                }}
            }}
        }});

        window.addEventListener('resize', () => {{
            if (document.body.classList.contains('scrolled')) {{
                layoutCards();
            }}
        }});

        function clearCardStyles() {{
            cards.forEach(card => {{
                card.style.left = '';
                card.style.top = '';
                card.style.width = '';
            }});
            container.style.height = '';
        }}
    }})();
</script>

</body>

</html>'''

    hub_path.write_text(html_content, encoding="utf-8")
    print(f"Generated hub.html with {len(projects)} projects")


def main() -> None:
    projects = _discover_projects()
    _write_projects_md(projects)
    _write_dashboard_html(projects)

    # Generate hub.html with all projects
    _generate_hub_html(projects)


if __name__ == "__main__":
    main()
