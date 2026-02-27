#!/usr/bin/env python3
"""
Oget - Ollama Model Direct Downloader & Installer
---------------------------------------------------
Get direct download links for Ollama models and install
locally downloaded model files (manifest + blobs).

  oget get gemma2:2b
  oget install --model gemma2:2b --blobsPath ./downloads
"""

import argparse
import sys
import os
import json
import urllib.request
import urllib.error
import shutil
import hashlib
import platform

# Constants
DEFAULT_REGISTRY = "registry.ollama.ai"
BLOBS_PATTERN = "blobs"

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg):
    print(f"{Colors.OKGREEN}✔ {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}✖ {msg}{Colors.ENDC}", file=sys.stderr)

def get_models_path(explicit_path=None):
    # Priority 1: explicitly passed --modelsPath argument
    if explicit_path:
        expanded = os.path.expanduser(explicit_path)
        print_info(f"Using models path: {expanded}")
        return expanded

    # Priority 2: OLLAMA_MODELS environment variable
    env_path = os.environ.get("OLLAMA_MODELS")
    if env_path:
        print_info(f"Using OLLAMA_MODELS path: {env_path}")
        return env_path

    # Neither set → print help and exit
    print_error("Ollama models path is not set.")
    print()
    print(f"{Colors.BOLD}Set it in one of two ways:{Colors.ENDC}")
    print(f"  {Colors.OKCYAN}1. Environment variable:{Colors.ENDC}")
    print(f"       export OLLAMA_MODELS=/path/to/ollama/models")
    print(f"  {Colors.OKCYAN}2. CLI argument:{Colors.ENDC}")
    print(f"       --modelsPath /path/to/ollama/models")
    print()
    print(f"{Colors.BOLD}Common paths:{Colors.ENDC}")
    print(f"   Linux  : /usr/share/ollama/.ollama/models")
    print(f"   macOS  : ~/.ollama/models")
    print(f"   Windows: C:/Users/<username>/.ollama/models")
    print()
    print_info("Tip: Find your path with: ollama show --modelfile <any-model>")
    sys.exit(1)

def parse_model_name(model_name_input):
    tag = "latest"
    if ":" in model_name_input:
        base, tag = model_name_input.split(":", 1)
    else:
        base = model_name_input
        print_warning("Using default model tag 'latest'.")

    # Handle custom namespaces vs default 'library'
    if "/" in base:
        namespace, model = base.split("/", 1)
    else:
        namespace = "library"
        model = base
        
    return namespace, model, tag

def format_size(size_in_bytes):
    if not isinstance(size_in_bytes, (int, float)):
        return "Unknown size"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            if unit == 'B':
                return f"{int(size_in_bytes)} {unit}"
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.1f} PB"

def cmd_get(args):
    model_name_input = args.model
    namespace, model, tag = parse_model_name(model_name_input)
    
    url = f"https://{DEFAULT_REGISTRY}/v2/{namespace}/{model}/manifests/{tag}"
    print_info(f"Fetching direct download link for model: {Colors.BOLD}{model_name_input}{Colors.ENDC}")
    
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.docker.distribution.manifest.v2+json"
    })
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print_error(f"Registry returned status {response.status}")
                sys.exit(1)
            
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print_error(f"Model '{model_name_input}' not found on the registry.")
        else:
            print_error(f"HTTP Error fetching manifest: {e}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print_error(f"URL Error fetching manifest: {e}")
        sys.exit(1)
        
    layers = data.get("layers", [])
    config = data.get("config")
    if config:
        layers.append(config)
        
    print(f"\n{Colors.BOLD}Manifest:{Colors.ENDC}")
    print(f"📄 {url}")
    print(f"\n{Colors.BOLD}Curl command to download the manifest (run in your manifest folder):{Colors.ENDC}")
    print(f'curl -L "{url}" -o "manifest"\n')
    
    print(f"{Colors.BOLD}Download links for layers:{Colors.ENDC}")
    curl_commands = []
    
    for i, layer in enumerate(layers, 1):
        digest = layer.get("digest")
        size = layer.get("size")
        size_str = format_size(size)
        if digest:
            layer_url = f"https://{DEFAULT_REGISTRY}/v2/{namespace}/{model}/blobs/{digest}"
            out_name = digest.replace(":", "-")  # Replace sha256: with sha256-
            print(f"{i} - [{Colors.OKCYAN}{size_str}{Colors.ENDC}] {layer_url}")
            curl_commands.append(f'curl -L "{layer_url}" -o "{out_name}"')
            
    print(f"\n{Colors.BOLD}Curl command to download all blobs (run in your blobs folder):{Colors.ENDC}")
    for cmd in curl_commands:
        print(cmd)
        
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}Finished successfully!{Colors.ENDC}")

def check_admin():
    system = platform.system().lower()
    if system == "windows":
        import ctypes
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    else:
        return os.geteuid() == 0

def get_file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        # Read in blocks to avoid memory issues with large files
        for chunk in iter(lambda: f.read(4096 * 1024), b""): 
            hasher.update(chunk)
    return f"sha256-{hasher.hexdigest()}"

def cmd_install(args):
    if not check_admin():
        print_error("Please run the command with elevated permissions (Admin / Root / sudo).")
        sys.exit(1)
        
    namespace, model, tag = parse_model_name(args.model)
    blobs_path = args.blobsPath
    
    print_info(f"Installing model: {Colors.BOLD}{args.model}{Colors.ENDC}")
    
    if not os.path.exists(blobs_path):
        print_error(f"blobsPath '{blobs_path}' does not exist.")
        sys.exit(1)
        
    manifest_source = os.path.join(blobs_path, "manifest")
    if not os.path.isfile(manifest_source):
        print_error(f"Missing 'manifest' file in '{blobs_path}'. Make sure it's named exactly 'manifest' without any extension.")
        sys.exit(1)
        
    models_path = get_models_path(getattr(args, 'modelsPath', None))
    
    try:
        os.makedirs(models_path, exist_ok=True)
    except Exception as e:
        print_error(f"Error creating models directory: {e}")
        sys.exit(1)
    
    # Setup Manifest destination
    manifest_dest_dir = os.path.join(models_path, "manifests", DEFAULT_REGISTRY, namespace, model)
    try:
        os.makedirs(manifest_dest_dir, exist_ok=True)
    except Exception as e:
        print_error(f"Error creating manifest directory: {e}")
        sys.exit(1)
        
    manifest_dest = os.path.join(manifest_dest_dir, tag)
    
    if os.path.exists(manifest_dest):
        print_warning("Some model files already exist. Do you wish to override them? This is permanent!")
        choice = input(f"{Colors.WARNING}Type 'Y' to proceed: {Colors.ENDC}")
        if choice.strip().upper() != 'Y':
            print_error("Installation aborted!")
            sys.exit(1)
            
    # Copy manifest
    print_info(f"Copying manifest to {manifest_dest_dir}...")
    try:
        shutil.copy2(manifest_source, manifest_dest)
    except Exception as e:
        print_error(f"Error copying manifest: {e}")
        sys.exit(1)
    
    # Setup Blobs destination
    blobs_dest_dir = os.path.join(models_path, BLOBS_PATTERN)
    try:
        os.makedirs(blobs_dest_dir, exist_ok=True)
    except Exception as e:
        print_error(f"Error creating blobs directory: {e}")
        sys.exit(1)
    
    # Copy blobs
    print_info(f"Copying blobs to {blobs_dest_dir}...")
    print_warning("This may take a while, so don't worry if it seems stuck.")
    
    for filename in os.listdir(blobs_path):
        if filename == "manifest" or os.path.isdir(os.path.join(blobs_path, filename)):
            continue
            
        file_source = os.path.join(blobs_path, filename)
        
        # Calculate destination file name
        if "sha256" not in filename:
            print_info(f"Calculating SHA-256 hash for {filename}...")
            hashed_name = get_file_hash(file_source)
        else:
            if filename.startswith("sha256-"):
                hashed_name = filename
            elif filename.startswith("sha256"):
                hashed_name = filename.replace("sha256", "sha256-", 1)
            else:
                hashed_name = filename
            
        file_dest = os.path.join(blobs_dest_dir, hashed_name)
        
        print_info(f"Copying {filename} -> {hashed_name}...")
        try:
            shutil.copy2(file_source, file_dest)
        except Exception as e:
            print_error(f"Error copying blob '{filename}': {e}")
            sys.exit(1)
        
    print_success("Model installed successfully!")
    print_info(f"You can now run it using: {Colors.BOLD}ollama run {args.model}{Colors.ENDC}")

def print_main_help():
    print(f"""
{Colors.BOLD}{Colors.HEADER}╔══════════════════════════════════════════╗
║         Oget  🦙  v1.0                ║
║   Ollama Model Direct Downloader         ║
╚══════════════════════════════════════════╝{Colors.ENDC}

{Colors.BOLD}USAGE{Colors.ENDC}
  oget <command> [options]

{Colors.BOLD}COMMANDS{Colors.ENDC}
  {Colors.OKGREEN}get <model>{Colors.ENDC}         Fetch direct download links for a model
  {Colors.OKGREEN}install{Colors.ENDC} [options]   Install a locally downloaded model into Ollama

{Colors.BOLD}WORKFLOW{Colors.ENDC}
  {Colors.OKCYAN}Step 1{Colors.ENDC}  Get download links:
            oget get gemma2:2b
  {Colors.OKCYAN}Step 2{Colors.ENDC}  Download files using the printed curl commands
  {Colors.OKCYAN}Step 3{Colors.ENDC}  Install the downloaded model into Ollama:
            sudo oget install --model gemma2:2b --blobsPath ./downloads

{Colors.BOLD}EXAMPLES{Colors.ENDC}
  oget get gemma2:2b
  oget get deepseek-r1:7b
  oget get huihui_ai/deepseek-r1-abliterated:8b
  sudo oget install --model gemma2:2b --blobsPath ./downloads
  sudo oget install --model gemma2:2b --blobsPath ./downloads --modelsPath ~/.ollama/models

{Colors.BOLD}MODEL NAME FORMAT{Colors.ENDC}
  <model>:<tag>                  Official model   → gemma2:2b
  <namespace>/<model>:<tag>      Community model  → huihui_ai/deepseek-r1:8b

{Colors.BOLD}MORE HELP{Colors.ENDC}
  oget get -h
  oget install -h
""")

def main():
    if len(sys.argv) == 1 or sys.argv[1] in ("-h", "--help"):
        print_main_help()
        sys.exit(0)

    parser = argparse.ArgumentParser(
        prog="oget",
        description="Oget — Ollama Model Direct Downloader & Installer",
        add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    # 'get' command
    parser_get = subparsers.add_parser(
        "get",
        help="Fetch direct download links for a model",
        description=f"""
{Colors.BOLD}oget get{Colors.ENDC} — Fetch direct download links for an Ollama model.

Connects to the Ollama registry and retrieves the manifest,
then prints direct download URLs for all blobs and ready-to-use curl commands.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            f"{Colors.BOLD}Examples:{Colors.ENDC}\n"
            "  oget get gemma2:2b\n"
            "  oget get deepseek-r1:7b\n"
            "  oget get huihui_ai/deepseek-r1-abliterated:8b\n"
            "  oget get llama3.2:latest"
        )
    )
    parser_get.add_argument(
        "model",
        help="Model name with tag. Format: <model>:<tag> or <namespace>/<model>:<tag>"
    )
    parser_get.set_defaults(func=cmd_get)

    # 'install' command
    parser_install = subparsers.add_parser(
        "install",
        help="Install a locally downloaded model into Ollama",
        description=f"""
{Colors.BOLD}oget install{Colors.ENDC} — Install a locally downloaded model into Ollama.

Copies the manifest and blob files into the correct Ollama directory
structure so Ollama can use the model with `ollama run`.

{Colors.WARNING}Requires elevated permissions (sudo / Administrator).{Colors.ENDC}

{Colors.BOLD}Your download folder must contain:{Colors.ENDC}
  - A file named exactly {Colors.BOLD}manifest{Colors.ENDC} (no extension) — the model manifest JSON
  - All blob files (sha256-... named files or raw files)

{Colors.BOLD}Models path priority:{Colors.ENDC}
  1. --modelsPath argument (highest priority)
  2. OLLAMA_MODELS environment variable
  3. Error with instructions if neither is set
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            f"{Colors.BOLD}Examples:{Colors.ENDC}\n"
            "  sudo oget install --model gemma2:2b --blobsPath ./downloads\n"
            "  sudo oget install --model gemma2:2b --blobsPath ./downloads --modelsPath /usr/share/ollama/.ollama/models\n"
            "\n"
            f"{Colors.BOLD}After install:{Colors.ENDC}\n"
            "  ollama run gemma2:2b"
        )
    )
    parser_install.add_argument(
        "--model",
        required=True,
        metavar="MODEL",
        help="Model name (e.g., gemma2:2b)"
    )
    parser_install.add_argument(
        "--blobsPath",
        required=True,
        metavar="PATH",
        help="Folder containing the downloaded 'manifest' file and all blob files"
    )
    parser_install.add_argument(
        "--modelsPath",
        default=None,
        metavar="PATH",
        help="Ollama models directory. Overrides OLLAMA_MODELS env var. If not set, OLLAMA_MODELS is used."
    )
    parser_install.set_defaults(func=cmd_install)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

