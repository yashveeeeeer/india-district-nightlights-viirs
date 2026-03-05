from __future__ import annotations

import io
import zipfile
from pathlib import Path

import requests


def download_file(url: str, dest: Path, chunk: int = 1 << 20) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for part in r.iter_content(chunk_size=chunk):
                if part:
                    f.write(part)
    return dest


def unzip_to_bytes(zip_path: Path) -> zipfile.ZipFile:
    # Caller must close
    return zipfile.ZipFile(zip_path, "r")


def unzip_member(zip_path: Path, member: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        with z.open(member) as src, open(out_path, "wb") as dst:
            dst.write(src.read())
    return out_path
