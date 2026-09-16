#!/usr/bin/env python3
"""
Descarga los datos externos que no se versionan en el repositorio.

En particular, `books_enriched.csv` (metadatos de los libros) procede del
dataset público GoodBooks-10k de Malcolm Osh:
https://github.com/malcolmosh/goodbooks-10k

Uso:
    python scripts/fetch_data.py

Los archivos se guardan en `datasets/goodbooks_ext/`. El resto de datos
(embeddings, valoraciones) ya se distribuyen con el repositorio o se
regeneran con los scripts de este directorio (ver `docs/DATA.md`).
"""

import os
import sys
import urllib.request

REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATASET_DIR = os.path.join(REPO_ROOT, "datasets", "goodbooks_ext")

# Archivo: (URL, nombre local)
FILES = [
    (
        (
            "https://raw.githubusercontent.com/malcolmosh/goodbooks-10k/"
            "master/books_enriched.csv"
        ),
        "books_enriched.csv",
    ),
]


def download(url: str, dest: str) -> None:
    print(f"Descargando {url}")
    tmp = dest + ".part"
    with urllib.request.urlopen(url, timeout=120) as response, open(
        tmp, "wb"
    ) as out:
        total = int(response.headers.get("Content-Length", 0))
        done = 0
        while chunk := response.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {done / total:.1%} ({done / 1e6:.1f} MB)", end="")
                sys.stdout.flush()
        print()
    os.replace(tmp, dest)
    print(f"OK {dest} ({os.path.getsize(dest) / 1e6:.2f} MB)")


def main() -> None:
    os.makedirs(DATASET_DIR, exist_ok=True)
    for url, name in FILES:
        dest = os.path.join(DATASET_DIR, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            print(f"Ya existe {dest}; omitiendo (borra el archivo para re-descargar).")
            continue
        download(url, dest)


if __name__ == "__main__":
    main()
