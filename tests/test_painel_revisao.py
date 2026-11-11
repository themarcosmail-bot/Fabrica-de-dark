import http.client
import json
import re
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode

from episode import write_json
from revisar import EpisodeReview, ReviewServer


class ReviewPanelTest(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        for version in ("mazda-anterior", "mazda-atual"):
            directory = self.root / "versoes" / version
            directory.mkdir(parents=True)
            files = {"video": "video_final.mp4", "roteiro": "roteiro.json", "legendas": "legendas.srt"}
            for kind, name in files.items():
                (directory / name).write_bytes(b"0123456789" if kind == "video" else b"exemplo")
            write_json(directory / "episodio.json", {
                "versao": version,
                "titulo": 'Mazda <rotativo>',
                "serie": "Motores Icônicos",
                "formato": "short-9x16",
                "fontes": ["https://mazda.example/historia", "javascript:alert(1)"],
                "arquivos": {kind: f"versoes/{version}/{name}" for kind, name in files.items()},
            })
        write_json(self.root / "episodio.json", {"versao": "mazda-atual"})
        self.server = ReviewServer(EpisodeReview(self.root), 0)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def post(self, version, state, notes="", token=None):
        return self.request("POST", "/revisao", urlencode({
            "versao": version, "decisao": state, "notas": notes,
            "token": self.server.token if token is None else token,
        }), {"Content-Type": "application/x-www-form-urlencoded"})

    def test_review_is_saved_per_version(self):
        status, _, page = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b'value="mazda-atual" selected', page)
        self.assertIn(b"Mazda &lt;rotativo&gt;", page)
        self.assertIn(b"https://mazda.example/historia", page)
        self.assertNotIn(b"javascript:", page)
        token = re.search(rb'name="token" value="([^"]+)"', page).group(1).decode()

        self.assertEqual(self.post("mazda-atual", "ajustes-solicitados")[0], 400)
        self.assertEqual(self.post("mazda-atual", "aprovado", token="invalido")[0], 403)
        status, headers, _ = self.post("mazda-atual", "ajustes-solicitados", "Rever a pronúncia", token)
        self.assertEqual(status, 303)
        self.assertIn(b"Ajustes solicitados", self.request("GET", headers["Location"])[2])
        self.assertIn("Rever a pronúncia".encode(), self.request("GET", "/")[2])
        self.assertEqual(self.post("mazda-anterior", "aprovado")[0], 303)

        review = EpisodeReview(self.root)
        self.assertEqual(review.decision("mazda-atual")["estado"], "ajustes-solicitados")
        self.assertEqual(review.decision("mazda-anterior")["estado"], "aprovado")
        original = (self.root / "versoes" / "mazda-atual" / "episodio.json").read_text(encoding="utf-8")
        self.assertNotIn("ajustes-solicitados", original)

    def test_preview_supports_seeking_and_download(self):
        media = "/midia/video?versao=mazda-atual"
        status, headers, body = self.request("GET", media, headers={"Range": "bytes=2-4"})
        self.assertEqual((status, body), (206, b"234"))
        self.assertEqual(headers["Content-Range"], "bytes 2-4/10")
        self.assertEqual(self.request("GET", media, headers={"Range": "bytes=-2"})[2], b"89")
        self.assertEqual(self.request("GET", media, headers={"Range": "bytes=30-"})[0], 416)
        self.assertEqual(self.request("HEAD", media)[1]["Content-Length"], "10")
        status, headers, body = self.request("GET", "/midia/legendas?versao=mazda-atual")
        self.assertEqual((status, body), (200, b"exemplo"))
        self.assertEqual(headers["Content-Disposition"], 'attachment; filename="legendas.srt"')

    def test_media_and_decisions_are_scoped(self):
        self.assertEqual(self.request("GET", "/", headers={"Host": "external.example"})[0], 403)
        self.assertEqual(self.post("../", "aprovado")[0], 404)
        path = self.root / "versoes" / "mazda-atual" / "episodio.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["arquivos"]["video"] = "versoes/mazda-anterior/video_final.mp4"
        write_json(path, manifest)
        self.assertEqual(self.request("GET", "/midia/video?versao=mazda-atual")[0], 404)
        self.assertEqual(self.post("mazda-atual", "aprovado")[0], 404)
