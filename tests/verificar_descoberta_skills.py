"""Confere a descoberta das skills do projeto pelo Codex real."""

import json
import queue
import subprocess
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
EXPECTED = {
    "fabrica-dirigir-cenas", "fabrica-narrar", "fabrica-orquestrar", "fabrica-pesquisar",
    "fabrica-renderizar", "fabrica-revisar", "fabrica-roteirizar",
}


def read_replies(stream, replies):
    try:
        for line in stream:
            replies.put(json.loads(line))
    finally:
        replies.put(None)


def request(process, replies, method, params, request_id=None):
    message = {"jsonrpc": "2.0", "method": method, "params": params}
    if request_id is not None:
        message["id"] = request_id
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()
    if request_id is None:
        return None

    while True:
        try:
            reply = replies.get(timeout=20)
        except queue.Empty as error:
            raise RuntimeError(f"Sem resposta do Codex para {method}.") from error
        if reply is None:
            raise RuntimeError(f"O Codex encerrou antes de responder a {method}.")
        if reply.get("id") == request_id:
            if "error" in reply:
                raise RuntimeError(f"{method}: {reply['error']['message']}")
            return reply["result"]


def main():
    process = subprocess.Popen(
        ["codex", "app-server", "--listen", "stdio://"],
        cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8",
    )
    replies = queue.Queue()
    threading.Thread(target=read_replies, args=(process.stdout, replies), daemon=True).start()

    try:
        request(process, replies, "initialize", {
            "clientInfo": {"name": "fabrica-de-dark-ci", "version": "1.0.0"},
        }, 1)
        request(process, replies, "initialized", {})
        result = request(process, replies, "skills/list", {
            "cwds": [str(ROOT)], "forceReload": True,
        }, 2)
        entry = next(entry for entry in result["data"] if Path(entry["cwd"]).resolve() == ROOT)
        project_errors = [
            error["message"] for error in entry["errors"]
            if Path(error["path"]).resolve().is_relative_to(SKILLS)
        ]
        if project_errors:
            raise RuntimeError(f"Erros nas skills do projeto: {project_errors}")

        discovered = {
            skill["name"] for skill in entry["skills"]
            if skill["enabled"] and Path(skill["path"]).resolve().is_relative_to(SKILLS)
        }
        missing = EXPECTED - discovered
        if missing:
            raise RuntimeError(f"Skills não descobertas: {', '.join(sorted(missing))}")
        print(f"Codex descobriu {len(EXPECTED)} skills do projeto: {', '.join(sorted(EXPECTED))}.")
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
