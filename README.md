# Oget 🦙

[![PyPI](https://img.shields.io/pypi/v/oget)](https://pypi.org/project/oget/)
[![GitHub](https://img.shields.io/badge/github-fr0stb1rd%2Foget-blue?logo=github)](https://github.com/fr0stb1rd/oget)

**Ollama Model Direct Downloader & Installer**

Get direct download links for Ollama models and install locally downloaded models — no internet required at install time.

## Why?

`ollama pull` can be slow or unreliable in some regions. Oget lets you:
- Get direct CDN download links for any Ollama model
- Download using your own download manager (IDM, aria2, wget, curl...)
- Install the downloaded files into Ollama offline

## Install

### via pip (all platforms)

```bash
pip install oget
```

### via AUR (Arch Linux)

```bash
# Using yay
yay -S oget

# Using paru
paru -S oget

# Manual
git clone https://aur.archlinux.org/oget.git
cd oget
makepkg -si
```

## Usage

### Step 1 — Get download links

```bash
oget get gemma2:2b
# oget get deepseek-r1:7b
# oget get huihui_ai/deepseek-r1-abliterated:8b
```

**Example Output:**

```text
ℹ Fetching direct download link for model: gemma2:2b

Curl command to download the manifest (run in your manifest folder):
curl -L "https://registry.ollama.ai/v2/library/gemma2/manifests/2b" -o "manifest"

Download links for layers:
1 - [1.5 GB] https://registry.ollama.ai/v2/library/gemma2/blobs/sha256:74627347...
2 - [358 B]  https://registry.ollama.ai/v2/library/gemma2/blobs/sha256:e0a42594...
...

Curl command to download all blobs (run in your blobs folder):
curl -L "https://registry.ollama.ai/v2/library/gemma2/blobs/sha256:74627347..." -o "sha256-74627347..."
curl -L "https://registry.ollama.ai/v2/library/gemma2/blobs/sha256:e0a42594..." -o "sha256-e0a42594..."
...
```

### Step 2 — Download the files

Copy the printed `curl` commands and run them in two separate folders:
- One folder for the **manifest**
- One folder for the **blobs**

### Step 3 — Install into Ollama

```bash
# Linux/macOS (requires sudo)
sudo oget install --model gemma2:2b --blobsPath ./downloads

# With explicit models path
sudo oget install --model gemma2:2b --blobsPath ./downloads --modelsPath ~/.ollama/models
```

Then run as usual:

```bash
ollama run gemma2:2b
```

## Models Path

Oget resolves the Ollama models directory in this order:

| Priority | Source |
|----------|--------|
| 1st | `--modelsPath` CLI argument |
| 2nd | `OLLAMA_MODELS` environment variable |
| Error | Helpful instructions are printed |

## Supported Platforms

- Linux
- macOS
- Windows

## Zero Dependencies

Oget uses only Python standard library — no `pip install` requirements beyond Python 3.8+.

## License

MIT
