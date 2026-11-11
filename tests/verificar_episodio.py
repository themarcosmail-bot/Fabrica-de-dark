"""Teste de ponta a ponta com Piper, FFmpeg e o CLI de produção."""

import json
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
MAZDA = ROOT / "exemplos" / "motores-iconicos-01.json"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(roteiro, *args):
    subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--roteiro", str(roteiro), *map(str, args)],
        cwd=ROOT, check=True,
    )


def verify_video(episode, expected_cues):
    manifest = read_json(episode / "episodio.json")
    assert manifest["estado"] == "aguardando-revisao"
    files = {key: episode / path for key, path in manifest["arquivos"].items()}
    assert read_json(files["video"].parent / "episodio.json") == manifest
    info = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(files["video"])]
    ))
    video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
    assert (video["width"], video["height"], video["codec_name"], audio["codec_name"]) == (1080, 1920, "h264", "aac")
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(files["video"]), "-f", "null", "-"], check=True)
    cues = re.findall(
        r"(\d\d:\d\d:\d\d,\d{3}) --> (\d\d:\d\d:\d\d,\d{3})",
        files["legendas"].read_text(encoding="utf-8"),
    )
    assert len(cues) == expected_cues

    def seconds(stamp):
        hours, minutes, second = stamp.replace(",", ".").split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(second)

    previous = 0
    duration = float(info["format"]["duration"])
    for start, end in cues:
        assert previous <= seconds(start) < seconds(end) <= duration
        previous = seconds(end)
    assert manifest["fontes"] == read_json(files["roteiro"])["fontes"]
    return manifest


def edit_script(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    run(ROOT / "exemplos" / "primeiro-short.json", "--checar-roteiro")
    run(MAZDA, "--checar-roteiro")
    with TemporaryDirectory(prefix="fabrica-") as directory:
        root = Path(directory)
        mazda = root / "mazda"
        revised = root / "revisado.json"
        run(MAZDA, "--episodio", mazda, "--somente-voz")
        narration = read_json(mazda / "narracao.json")
        assert narration["falas_geradas"] == 12
        assert all((mazda / track).is_file() for scene in narration["faixas_por_cena"] for track in scene)

        run(MAZDA, "--episodio", mazda)
        first = verify_video(mazda, 12)
        assert first["processamento"] == dict(
            falas_geradas=0, falas_reutilizadas=12, cenas_geradas=5, cenas_reutilizadas=0,
        )

        script = read_json(MAZDA)
        script["cenas"][4]["visual"]["chamada"] = "1991  /  24 HORAS DE LE MANS"
        edit_script(revised, script)
        run(revised, "--episodio", mazda)
        second = verify_video(mazda, 12)
        assert second["versao"] != first["versao"]
        assert (mazda / first["arquivos"]["video"]).is_file()
        assert second["processamento"] == dict(
            falas_geradas=0, falas_reutilizadas=12, cenas_geradas=1, cenas_reutilizadas=4,
        )

        script["cenas"][1]["falas_voz"] = [None, "A ideia do rotativo era de Félix Vânkel."]
        edit_script(revised, script)
        run(revised, "--episodio", mazda)
        third = verify_video(mazda, 12)
        assert third["processamento"]["falas_geradas"] == 1
        assert third["processamento"]["falas_reutilizadas"] == 11
        assert third["processamento"]["cenas_reutilizadas"] >= 4
        assert "Felix Wankel" in (mazda / third["arquivos"]["legendas"]).read_text(encoding="utf-8")

        toyota_script = {
            "titulo": "O motor do Toyota Supra",
            "serie": "MOTORES ICÔNICOS",
            "fontes": ["https://global.toyota/en/detail/7868203"],
            "cenas": [{
                "visual": {
                    "tipo": "linha-tempo",
                    "titulo": "TOYOTA\nSUPRA",
                    "chamada": "O 2JZ-GTE",
                    "itens": [{"marco": "1993", "titulo": "ESTREIA DO SUPRA", "detalhe": "Nova geração"}],
                },
                "falas": ["Em 1993, a Toyota lançou uma nova geração do Supra."],
            }],
        }
        toyota = root / "toyota"
        edit_script(revised, toyota_script)
        run(revised, "--episodio", toyota)
        verify_video(toyota, 1)

        legacy = root / "cartoes"
        run(ROOT / "exemplos" / "primeiro-short.json", "--episodio", legacy)
        verify_video(legacy, 4)
    print("OK: Mazda, reprocessamento visual, pronúncia isolada, visual genérico no Toyota e cartões.")


if __name__ == "__main__":
    main()
