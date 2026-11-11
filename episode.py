"""Reaproveitamento de mídia e registro das versões de um episódio."""

import hashlib
import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path


def file_digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def write_json(path, value):
    data = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    temporary = tempfile.NamedTemporaryFile(dir=path.parent, delete=False)
    try:
        with temporary:
            temporary.write(data.encode("utf-8"))
        os.replace(temporary.name, path)
    finally:
        with suppress(FileNotFoundError):
            Path(temporary.name).unlink()


class MediaCache:
    def __init__(self, root):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.stats = {
            "falas_geradas": 0,
            "falas_reutilizadas": 0,
            "cenas_geradas": 0,
            "cenas_reutilizadas": 0,
        }

    def asset(self, kind, inputs, filename, create):
        data = json.dumps([kind, inputs], ensure_ascii=False, sort_keys=True).encode("utf-8")
        key = hashlib.sha256(data).hexdigest()
        target = self.root / key / filename
        if target.is_file():
            self.stats[f"{kind}_reutilizadas"] += 1
            return target

        with tempfile.TemporaryDirectory(dir=self.root, prefix=".media-") as directory:
            entry = Path(directory) / "entry"
            entry.mkdir()
            create(entry / filename)
            if not (entry / filename).is_file():
                raise ValueError(f"O processamento não gerou {filename}.")
            try:
                entry.rename(target.parent)
            except OSError:
                if not target.is_file():
                    raise
        self.stats[f"{kind}_geradas"] += 1
        return target
