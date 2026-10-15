import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FILE = json.loads((ROOT / "conformance" / "documents.json").read_text())["documents"][0]["file"]

HELD = ROOT / "docs" / FILE


def flatten(laid_out: str) -> str:
    return " ".join(laid_out.split())


def text(pdf: Path = HELD) -> str:
    if not pdf.is_file() or shutil.which("pdftotext") is None:
        return ""
    done = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True
    )
    return flatten(done.stdout)
