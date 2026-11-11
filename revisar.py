"""Painel local de revisão de versões renderizadas pela Fábrica de Dark."""

import argparse
import html
import json
import os
import re
import secrets
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from string import Template
from urllib.parse import parse_qs, urlencode, urlsplit

from episode import write_json

UI = Path(__file__).resolve().parent / "review_ui"
ARTIFACTS = {
    "video": ("video_final.mp4", "video/mp4"),
    "legendas": ("legendas.srt", "text/plain; charset=utf-8"),
    "roteiro": ("roteiro.json", "application/json"),
}
STATUS = {
    "aguardando-revisao": ("Aguardando revisão", "Assista à versão e registre sua decisão."),
    "ajustes-solicitados": ("Ajustes solicitados", "As notas desta versão estão salvas."),
    "aprovado": ("Aprovado", "A aprovação foi registrada para esta versão."),
}
NOTES_LIMIT = 1500


def read_object(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON inválido em {path.name}.")
    return data


def escape(value):
    return html.escape(str(value), quote=True)


def version_url(version, path="/"):
    return f"{path}?{urlencode({'versao': version})}"


class EpisodeReview:
    def __init__(self, root):
        self.root = root.resolve()
        self.versions_dir = self.root / "versoes"
        if self.versions_dir.is_symlink():
            raise ValueError("A pasta de versões precisa estar dentro do episódio.")

    def versions(self):
        versions = []
        for folder in self.versions_dir.iterdir():
            if folder.is_symlink() or not folder.is_dir() or not re.fullmatch(r"[a-z0-9-]+", folder.name):
                continue
            path = folder / "episodio.json"
            if not path.is_file() or path.is_symlink():
                continue
            manifest = read_object(path)
            if manifest.get("versao") != folder.name:
                raise ValueError(f"Identificador divergente em {folder.name}.")
            versions.append((path.stat().st_mtime_ns, folder.name, manifest))
        return {version: manifest for _, version, manifest in sorted(versions, reverse=True)}

    def default_version(self, versions):
        if not versions:
            raise FileNotFoundError("Nenhuma versão renderizada foi encontrada.")
        pointer = self.root / "episodio.json"
        if pointer.is_file() and not pointer.is_symlink():
            latest = read_object(pointer).get("versao")
            if isinstance(latest, str) and latest in versions:
                return latest
        return next(iter(versions))

    def review_path(self, version):
        return self.versions_dir / version / "revisao.json"

    def decision(self, version):
        path = self.review_path(version)
        if not path.is_file() or path.is_symlink():
            return {"estado": "aguardando-revisao", "notas": ""}
        review = read_object(path)
        if review.get("versao") != version or review.get("estado") not in STATUS or not isinstance(review.get("notas"), str):
            raise ValueError("Registro de revisão inválido.")
        return review

    def save(self, version, state, notes):
        write_json(self.review_path(version), {
            "schema": 1,
            "versao": version,
            "estado": state,
            "notas": notes,
            "atualizado_em": datetime.now(timezone.utc).isoformat(),
        })

    def media_path(self, version, manifest, kind):
        expected = self.versions_dir / version / ARTIFACTS[kind][0]
        files = manifest.get("arquivos")
        raw = files.get(kind) if isinstance(files, dict) else None
        if not isinstance(raw, str):
            raise FileNotFoundError(expected.name)
        path = (self.root / raw).resolve(strict=True)
        if path != expected or not path.is_file():
            raise FileNotFoundError(expected.name)
        return path


def source_links(sources):
    links = []
    for source in sources if isinstance(sources, list) else []:
        if not isinstance(source, str):
            continue
        try:
            url = urlsplit(source)
        except ValueError:
            continue
        if url.scheme not in {"http", "https"} or not url.hostname:
            continue
        links.append(
            f'<li><a href="{escape(source)}" target="_blank" rel="noopener noreferrer">'
            f'<span>{escape(url.hostname)}</span><small>{escape(url.path or "/")}</small>'
            '<span class="external" aria-hidden="true">↗&#65038;</span></a></li>'
        )
    return "".join(links) or '<li class="empty">Nenhuma fonte informada neste roteiro.</li>'


def page(server, versions, selected, *, error="", notes=None, saved=False):
    manifest = versions[selected]
    decision = server.episode.decision(selected)
    state = decision["estado"]
    state_label, state_detail = STATUS[state]
    latest = server.episode.default_version(versions)
    options = []
    for number, version in enumerate(reversed(versions), start=1):
        label = f"Versão {number:02d}"
        if version == latest:
            label += " · mais recente"
        marked = " selected" if version == selected else ""
        identifier = escape(version)
        options.append(f'<option value="{identifier}"{marked} title="{identifier}">{escape(label)}</option>')

    template = Template((UI / "painel.html").read_text(encoding="utf-8"))
    return template.substitute(
        titulo=escape(manifest.get("titulo") or "Episódio"),
        serie=escape(manifest.get("serie") or "Episódio avulso"),
        formato=escape("Vertical · 9:16" if manifest.get("formato") == "short-9x16" else manifest.get("formato", "")),
        versao=escape(selected),
        opcoes="".join(options),
        video=escape(version_url(selected, "/midia/video")),
        legendas=escape(version_url(selected, "/midia/legendas")),
        roteiro=escape(version_url(selected, "/midia/roteiro")),
        fontes=source_links(manifest.get("fontes", [])),
        estado=escape(state),
        estado_rotulo=escape(state_label),
        estado_detalhe=escape(state_detail),
        notas=escape(decision["notas"] if notes is None else notes),
        token=escape(server.token),
        limite=NOTES_LIMIT,
        aviso=f'<p class="form-alert" role="alert">{escape(error)}</p>' if error else (
            '<p class="form-success" role="status">Decisão salva nesta versão.</p>' if saved else ""
        ),
    ).encode("utf-8")


def byte_range(value, size):
    match = re.fullmatch(r"bytes=(\d{0,20})-(\d{0,20})", value)
    if not match or not size:
        raise ValueError("Intervalo inválido.")
    start, end = match.groups()
    if start:
        first, last = int(start), min(int(end), size - 1) if end else size - 1
    elif end:
        first, last = max(0, size - int(end)), size - 1
    else:
        raise ValueError("Intervalo vazio.")
    if not 0 <= first <= last < size:
        raise ValueError("Intervalo fora do arquivo.")
    return first, last


class ReviewHandler(BaseHTTPRequestHandler):
    def send_headers(self, status, mime, length, **extra):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        for name, value in extra.items():
            self.send_header(name.replace("_", "-"), value)
        self.end_headers()

    def send_body(self, status, mime, body, **extra):
        self.send_headers(status, mime, len(body), **extra)
        if self.command != "HEAD":
            self.wfile.write(body)

    def message(self, status, text):
        self.send_body(status, "text/plain; charset=utf-8", text.encode("utf-8"))

    def check_host(self):
        port = self.server.server_port
        if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
            self.message(403, "Abra o painel pelo endereço local exibido no terminal.")
            return False
        return True

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if not self.check_host():
            return
        try:
            url = urlsplit(self.path)
            if url.path == "/painel.css":
                self.send_body(200, "text/css; charset=utf-8", (UI / "painel.css").read_bytes())
                return
            versions = self.server.episode.versions()
            query = parse_qs(url.query)
            selected = query.get("versao", [None])[0] or self.server.episode.default_version(versions)
            if selected not in versions:
                raise FileNotFoundError
            if url.path == "/":
                self.send_body(200, "text/html; charset=utf-8", page(
                    self.server, versions, selected, saved=query.get("salvo") == ["1"]
                ))
            elif url.path.startswith("/midia/"):
                kind = url.path.removeprefix("/midia/")
                if kind not in ARTIFACTS:
                    raise FileNotFoundError
                self.serve_media(selected, versions[selected], kind)
            else:
                raise FileNotFoundError
        except FileNotFoundError:
            self.message(404, "Versão ou arquivo indisponível.")
        except (OSError, ValueError, TypeError):
            self.message(500, "Não foi possível ler os arquivos deste episódio.")

    def serve_media(self, selected, manifest, kind):
        path = self.server.episode.media_path(selected, manifest, kind)
        name, mime = ARTIFACTS[kind]
        if kind != "video":
            self.send_body(200, mime, path.read_bytes(), Content_Disposition=f'attachment; filename="{name}"')
            return
        with path.open("rb") as video:
            size = os.fstat(video.fileno()).st_size
            request = self.headers.get("Range")
            headers = {"Accept_Ranges": "bytes"}
            if request:
                try:
                    first, last = byte_range(request, size)
                except ValueError:
                    self.send_body(416, "text/plain; charset=utf-8", b"", Content_Range=f"bytes */{size}")
                    return
                status = 206
                headers["Content_Range"] = f"bytes {first}-{last}/{size}"
            else:
                status, first, last = 200, 0, size - 1
            remaining = last - first + 1
            self.send_headers(status, mime, remaining, **headers)
            if self.command == "HEAD":
                return
            video.seek(first)
            try:
                while remaining:
                    chunk = video.read(min(remaining, 256 * 1024))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                return

    def do_POST(self):
        if not self.check_host():
            return
        if self.path != "/revisao":
            self.message(404, "Rota indisponível.")
            return
        if self.headers.get_content_type() != "application/x-www-form-urlencoded":
            self.message(415, "Formato de revisão inválido.")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 32_000:
                self.message(400, "Envie uma revisão válida.")
                return
            fields = parse_qs(self.rfile.read(length).decode("utf-8"), max_num_fields=6, errors="strict")
        except (ValueError, UnicodeError):
            self.message(400, "Não foi possível ler a revisão.")
            return
        token = fields.get("token", [""])[0]
        if not secrets.compare_digest(token.encode("utf-8"), self.server.token.encode("ascii")):
            self.message(403, "Reabra o painel e tente novamente.")
            return
        try:
            self.record_review(fields)
        except FileNotFoundError:
            self.message(404, "O vídeo desta versão está indisponível.")
        except (OSError, ValueError, TypeError):
            self.message(500, "Não foi possível salvar a revisão.")

    def record_review(self, fields):
        versions = self.server.episode.versions()
        selected = fields.get("versao", [""])[0]
        state = fields.get("decisao", [""])[0]
        notes = fields.get("notas", [""])[0].strip()
        if selected not in versions:
            self.message(404, "Versão indisponível.")
            return
        if state not in {"aprovado", "ajustes-solicitados"}:
            self.message(400, "Escolha uma decisão de revisão.")
            return
        error = ""
        if len(notes) > NOTES_LIMIT:
            error = f"Use até {NOTES_LIMIT} caracteres nas notas."
        elif state == "ajustes-solicitados" and not notes:
            error = "Descreva o que precisa ser ajustado."
        if error:
            self.send_body(400, "text/html; charset=utf-8", page(self.server, versions, selected, error=error, notes=notes))
            return
        self.server.episode.media_path(selected, versions[selected], "video")
        self.server.episode.save(selected, state, notes)
        self.send_body(303, "text/plain; charset=utf-8", b"", Location=version_url(selected) + "&salvo=1")


class ReviewServer(ThreadingHTTPServer):
    def __init__(self, episode, port):
        self.episode = episode
        self.token = secrets.token_urlsafe(24)
        super().__init__(("127.0.0.1", port), ReviewHandler)


def main():
    parser = argparse.ArgumentParser(description="Abra o painel local de revisão de um episódio.")
    parser.add_argument("--episodio", required=True, type=Path, help="Pasta usada com main.py --episodio")
    parser.add_argument("--porta", type=int, default=8765)
    args = parser.parse_args()
    try:
        episode = EpisodeReview(args.episodio)
        episode.default_version(episode.versions())
        with ReviewServer(episode, args.porta) as server:
            print(f"Painel de revisão em http://127.0.0.1:{server.server_port}/", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        return
    except (OSError, ValueError, OverflowError) as error:
        parser.exit(1, f"Erro ao abrir o painel: {error}\n")


if __name__ == "__main__":
    main()
