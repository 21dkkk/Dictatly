"""
Dictatly Release & Distribution Builder.
Packages Dictatly into a standalone Windows directory, downloads offline Whisper models,
compiles the Inno Setup installer, and generates portable ZIP archives.
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
APP_DIST_DIR = DIST_DIR / "Dictatly"
MODELS_DIR = APP_DIST_DIR / "models"
VERSION = "1.1.1"

def log(msg: str):
    print(f"[Build-Dist] {msg}")

def download_model(model_name: str, target_dir: Path):
    """Download Faster-Whisper model into target directory."""
    log(f"Downloading Whisper model '{model_name}' to {target_dir}...")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # We invoke faster_whisper to download the model
    cmd = [
        sys.executable,
        "-c",
        f"from faster_whisper import WhisperModel; WhisperModel('{model_name}', download_root=r'{target_dir}')"
    ]
    res = subprocess.run(cmd, capture_output=False)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to download model '{model_name}'.")
    log(f"Model '{model_name}' successfully cached in {target_dir}")

def run_pyinstaller():
    """Run PyInstaller with Dictatly.spec."""
    spec_path = ROOT / "Dictatly.spec"
    if not spec_path.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_path}")

    log("Running PyInstaller...")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(spec_path)]
    res = subprocess.run(cmd, cwd=str(ROOT))
    if res.returncode != 0:
        raise RuntimeError("PyInstaller build failed.")
    
    # Ensure resources folder is directly accessible at top level
    res_dest = APP_DIST_DIR / "resources"
    if not res_dest.exists() and (ROOT / "resources").exists():
        shutil.copytree(ROOT / "resources", res_dest)

    log("PyInstaller build completed.")

def find_iscc() -> Path | None:
    """Find Inno Setup Compiler executable."""
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    for p in candidates:
        if p.exists():
            return p
    
    which_iscc = shutil.which("iscc.exe") or shutil.which("iscc")
    if which_iscc:
        return Path(which_iscc)
    return None

def compile_installer(version: str = VERSION):
    """Compile Inno Setup installer."""
    iscc = find_iscc()
    if not iscc:
        log("Inno Setup Compiler (ISCC.exe) not found. Skipping installer generation.")
        log("To build the installer, install Inno Setup (winget install JRSoftware.InnoSetup).")
        return False

    iss_file = ROOT / "installer" / "Dictatly.iss"
    log(f"Compiling installer using {iscc}...")
    cmd = [str(iscc), f"/DAppVersion={version}", str(iss_file)]
    res = subprocess.run(cmd, cwd=str(ROOT))
    if res.returncode != 0:
        log("Inno Setup compilation failed.")
        return False
    log("Installer successfully built in dist/installer/")
    return True

def create_portable_zip(version: str = VERSION):
    """Create portable ZIP archive of dist/Dictatly."""
    zip_name = DIST_DIR / f"Dictatly-v{version}-Portable"
    log(f"Creating portable archive: {zip_name}.zip...")
    shutil.make_archive(str(zip_name), "zip", root_dir=str(DIST_DIR), base_dir="Dictatly")
    log(f"Portable archive created: {zip_name}.zip")

def main():
    parser = argparse.ArgumentParser(description="Dictatly Distribution Builder")
    parser.add_argument("--bundle-model", action="store_true", help="Download and bundle Faster-Whisper model into the distribution")
    parser.add_argument("--model-name", default="large-v3-turbo", help="Whisper model name (default: large-v3-turbo)")
    parser.add_argument("--skip-pyinstaller", action="store_true", help="Skip PyInstaller compilation step")
    parser.add_argument("--skip-installer", action="store_true", help="Skip Inno Setup compilation")
    parser.add_argument("--skip-portable", action="store_true", help="Skip portable ZIP creation")
    parser.add_argument("--version", default=VERSION, help=f"Release version tag (default: {VERSION})")

    args = parser.parse_args()

    # 1. PyInstaller build
    if not args.skip_pyinstaller:
        run_pyinstaller()

    # 2. Bundle offline model if requested
    if args.bundle_model:
        download_model(args.model_name, MODELS_DIR)

    # 3. Create Inno Setup installer
    if not args.skip_installer:
        compile_installer(args.version)

    # 4. Create Portable ZIP
    if not args.skip_portable:
        create_portable_zip(args.version)

    log("Build process complete.")

if __name__ == "__main__":
    main()
