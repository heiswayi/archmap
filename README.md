# archmap

**Generate a single, self-contained interactive architecture-map HTML from any project's source code.**

`archmap` scans a project folder, infers its architectural layers, extracts modules / classes / functions / imports, resolves the dependency graph between files, and renders everything into **one** standalone HTML file — no server, no build step, no external assets.

```bash
archmap <project_folder_path>
```

Open the generated `*-architecture.html` in any browser and explore your codebase through five tabs.

---

## Features

- **📊 Overview** — file/line/class/function counts, language breakdown, and a layer distribution chart.
- **🏗️ Architecture Layers** — every file grouped into inferred layers (Entry Points, Config, Models, API, Services, Data Access, Integrations, UI, Utilities, Tests, Docs, Build/Ops).
- **🔗 Dependencies** — internal import relationships resolved between in-project files, with "depends on" / "used by" edges.
- **📁 File System** — a collapsible tree of everything scanned, each file clickable.
- **🔎 Component Reference** — a searchable table of all components.
- A detail side-panel for any component: layer, language, line count, classes, functions, methods, imports, and dependency links.

Everything is embedded in a single HTML file (data is inlined as JSON), so it is trivial to share, archive, or commit.

## Installation

archmap is pure Python with **zero runtime dependencies**. Pick whichever fits.

### Standalone binary (no Python needed)

Download the executable for your platform from the [latest release](https://github.com/heiswayi/archmap/releases/latest), then run it directly:

| Platform | Asset |
| --- | --- |
| Linux (x86_64) | `archmap-linux-x86_64` |
| macOS (Apple Silicon) | `archmap-macos-arm64` |
| macOS (Intel) | `archmap-macos-x86_64` |
| Windows (x86_64) | `archmap-windows-x86_64.exe` |

```bash
# Linux / macOS
chmod +x archmap-linux-x86_64
./archmap-linux-x86_64 /path/to/project
```

```powershell
# Windows
.\archmap-windows-x86_64.exe C:\path\to\project
```

### pipx (recommended if you have Python 3.8+)

Installs into an isolated environment and puts `archmap` on your PATH:

```bash
pipx install archmap-cli                                   # from PyPI (provides the `archmap` command)
pipx install git+https://github.com/heiswayi/archmap       # from GitHub
```

### pip

```bash
pip install archmap-cli        # from PyPI (provides the `archmap` command)
pip install .                  # from a source checkout
```

Requires Python 3.8+ (except the standalone binaries, which bundle their own runtime).

## Usage

```bash
# Scan the current directory
archmap .

# Scan a specific project and open the result in your browser
archmap /path/to/project --open

# Custom output path and display name
archmap /path/to/project -o report.html --name "My Service"

# Ignore .gitignore rules while scanning
archmap /path/to/project --no-gitignore
```

| Flag | Description |
| --- | --- |
| `path` | Project folder to scan (default: `.`). |
| `-o, --output` | Output HTML path (default: `<project>-architecture.html`). |
| `-n, --name` | Project name shown in the report (default: folder name). |
| `--open` | Open the report in the default browser when done. |
| `--no-gitignore` | Do not honor the project's `.gitignore`. |
| `-q, --quiet` | Suppress progress output. |
| `-V, --version` | Print version. |

The output HTML path is also printed to stdout so it can be piped.

## How it works

1. **Scan** (`scanner.py`) — walks the tree, skipping common noise (`.git`, `node_modules`, build dirs, lockfiles, binaries) and honoring `.gitignore`.
2. **Analyze** (`languages/`) — Python files are parsed with the standard-library `ast`; other languages (JS/TS, Go, Rust, Java, Ruby, C/C++, …) are read with language-aware regex heuristics to pull out classes, functions, and imports.
3. **Classify** (`layers.py`) — each file is routed into an architectural layer using directory- and filename-based scoring.
4. **Link** (`analyzer.py`) — raw imports are resolved against in-project files to build the dependency graph (both dotted module paths and relative file paths).
5. **Render** (`renderer.py`) — the model is serialized to JSON and injected into a single HTML template.

## Supported languages

Python (deep `ast` analysis), JavaScript, TypeScript, Go, Rust, Java, Kotlin, Ruby, PHP, C#, Swift, C/C++, Shell, Vue, Svelte, plus structural files (YAML, TOML, JSON, Markdown, Dockerfile, Terraform, …).

## License

MIT
