import argparse
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import textwrap
import unicodedata
import wave
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4

import PIL
from PIL import Image, ImageDraw, ImageFont

from episode import MediaCache, file_digest, write_json
from motion import STYLES, render_clip, validate_visual

ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1080, 1920
FPS = 25
AUDIO_RATE = 44100
PAUSE_FRAMES = 8
PALETTES = [
    ("#102020", "#AFF1CE"),
    ("#171E30", "#C0CDFF"),
    ("#29201B", "#FFD4A4"),
    ("#231B2D", "#E7C3FF"),
]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def make_script(topic, config):
    prompt = (
        "Escreva um roteiro para um Short em português do Brasil sobre o tema "
        f"{json.dumps(topic, ensure_ascii=False)}. "
        'Retorne JSON no formato {"titulo":"...", "cenas":[{"texto":"..."}]}. '
        "Escreva quatro cenas, com até duas frases curtas cada. "
        "Evite afirmações incertas. Não invente fontes nem use Markdown."
    )
    request = Request(
        config["ollama_url"],
        data=json.dumps(
            {"model": config["model"], "prompt": prompt, "stream": False, "format": "json"}
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=240) as response:
            result = json.load(response)
        return json.loads(result["response"])
    except (URLError, TimeoutError) as error:
        raise ValueError(
            f"Falha ao chamar o Ollama ({error}). Confira o serviço e o modelo configurado."
        ) from error
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("O Ollama não devolveu um roteiro JSON válido.") from error


def validate_script(script):
    if not isinstance(script, dict):
        raise ValueError("O roteiro precisa ser um objeto JSON.")
    title = script.get("titulo")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Preencha o campo titulo no roteiro.")
    label = script.get("serie", "FÁBRICA DE DARK")
    if not isinstance(label, str) or not label.strip() or len(label) > 40 or len(label.splitlines()) != 1:
        raise ValueError("Use uma linha de até 40 caracteres no campo serie.")
    scenes = script.get("cenas")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 12:
        raise ValueError("O roteiro precisa ter de 1 a 12 cenas.")
    for index, scene in enumerate(scenes, 1):
        if isinstance(scene, dict) and "visual" in scene:
            validate_motion(scene, index)
        text = scene.get("texto") if isinstance(scene, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Preencha o campo texto da cena {index}.")
        scene["texto"] = " ".join(text.split())
    script["titulo"] = title.strip()


def validate_motion(scene, index):
    visual = scene["visual"]
    if not isinstance(visual, dict) or not isinstance(visual.get("tipo"), str) or visual["tipo"] not in STYLES:
        raise ValueError(f"Escolha um visual documental válido para a cena {index}.")
    for key, limit in (("titulo", 55), ("chamada", 45)):
        value = visual.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f"Preencha visual.{key} com até {limit} caracteres na cena {index}.")
    if len(visual["titulo"].splitlines()) > 2 or len(visual["chamada"].splitlines()) != 1:
        raise ValueError(f"Use até duas linhas no título e uma na chamada da cena {index}.")
    phrases = scene.get("falas")
    if not isinstance(phrases, list) or not 1 <= len(phrases) <= 8:
        raise ValueError(f"Informe de 1 a 8 falas curtas na cena {index}.")
    if any(not isinstance(phrase, str) or not phrase.strip() or len(phrase) > 74 for phrase in phrases):
        raise ValueError(f"Cada fala da cena {index} deve ter até 74 caracteres.")
    scene["falas"] = [" ".join(phrase.split()) for phrase in phrases]
    if "falas_voz" in scene:
        spoken = scene["falas_voz"]
        if not isinstance(spoken, list) or len(spoken) != len(phrases) or any(
            phrase is not None and (not isinstance(phrase, str) or not phrase.strip() or len(phrase) > 110)
            for phrase in spoken
        ):
            raise ValueError(f"Use uma entrada em falas_voz para cada fala da cena {index}.")
    scene["texto"] = " ".join(scene["falas"])
    validate_visual(visual, index)


@lru_cache(maxsize=48)
def font(size, bold=False):
    windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    windows_name = "arialbd.ttf" if bold else "arial.ttf"
    linux_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for path in (windows_fonts / windows_name, Path("/usr/share/fonts/truetype/dejavu") / linux_name):
        if path.is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def wrap_text(draw, text, typeface, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}" if line else word
        if draw.textlength(trial, font=typeface) <= width:
            line = trial
            continue
        if line:
            lines.append(line)
        line = word
        while draw.textlength(line, font=typeface) > width:
            split_at = len(line) - 1
            while draw.textlength(line[:split_at], font=typeface) > width:
                split_at -= 1
            lines.append(line[:split_at])
            line = line[split_at:]
    if line:
        lines.append(line)
    return "\n".join(lines)


def render_card(text, title, index, total, path):
    background, accent = PALETTES[(index - 1) % len(PALETTES)]
    image = Image.new("RGB", (WIDTH, HEIGHT), background)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((78, 144, 1002, 1620), radius=38, outline=accent, width=2)
    draw.text((130, 198), "FÁBRICA DE DARK", font=font(30, bold=True), fill=accent)
    draw.text((950, 199), f"{index:02d} / {total:02d}", font=font(30), fill=accent, anchor="ra")
    draw.line((130, 266, 950, 266), fill=accent, width=2)
    heading_font = font(36)
    heading = wrap_text(draw, title, heading_font, 820).splitlines()
    if len(heading) > 2:
        heading = [heading[0], heading[1].rstrip(".") + "…"]
    draw.multiline_text((130, 308), "\n".join(heading), font=heading_font, fill="#E1EBE7", spacing=12)

    for size in (80, 68, 56, 46, 38):
        body_font = font(size, bold=True)
        body = wrap_text(draw, text, body_font, 780)
        bounds = draw.multiline_textbbox((0, 0), body, font=body_font, spacing=18)
        if bounds[3] - bounds[1] <= 920:
            break
    else:
        raise ValueError(f"O texto da cena {index} ficou longo demais para o cartão.")

    draw.rounded_rectangle((130, 518, 204, 530), radius=6, fill=accent)
    draw.multiline_text((130, 590), body, font=body_font, fill="#F7FAF8", spacing=18)
    for step in range(total):
        left = 130 + step * (820 / total)
        right = 130 + (step + 1) * (820 / total) - 8
        color = accent if step < index else "#62736E"
        draw.rounded_rectangle((left, 1546, right, 1553), radius=3, fill=color)
    image.save(path)


def speak(text, audio, config):
    model = ROOT / config["piper_model"]
    model_config = Path(f"{model}.json")
    if not model.is_file() or not model_config.is_file():
        raise ValueError(f"Voz Piper ausente. São necessários {model} e {model_config.name}.")

    if executable := config.get("piper_exe"):
        subprocess.run(
            [executable, "--model", str(model), "--output_file", str(audio)],
            input=text + "\n",
            encoding="utf-8",
            check=True,
        )
    else:
        subprocess.run(
            [sys.executable, "-m", "piper", "-m", str(model), "-f", str(audio), "--", text],
            check=True,
        )


def audio_length(path):
    with wave.open(str(path), "rb") as audio:
        if audio.getnframes() == 0:
            raise ValueError(f"A narração está vazia em {path.name}.")
        return audio.getnframes() / audio.getframerate()


def timestamp(milliseconds):
    seconds, millis = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def spoken_phrases(scene):
    if "visual" not in scene:
        return [scene["texto"]]
    overrides = scene.get("falas_voz", [None] * len(scene["falas"]))
    return [" ".join(voice.split()) if voice else text for text, voice in zip(scene["falas"], overrides)]


def voice_signature(config):
    model = ROOT / config["piper_model"]
    model_config = Path(f"{model}.json")
    if executable := config.get("piper_exe"):
        resolved = shutil.which(executable)
        if not resolved:
            raise ValueError(f"Executável do Piper ausente: {executable}.")
        engine = file_digest(Path(resolved))
    else:
        try:
            engine = version("piper-tts")
        except PackageNotFoundError as error:
            raise ValueError("Instale piper-tts no ambiente Python da Fábrica de Dark.") from error
    return [engine, file_digest(model), file_digest(model_config)]


def voice_track(text, path, config, cache=None, signature=None):
    if cache is None:
        speak(text, path, config)
        return path

    def generate(target):
        speak(text, target, config)
        audio_length(target)

    return cache.asset("falas", [signature, text], "voz.wav", generate)


def build_motion_audio(scene, path, config, cache=None, signature=None):
    cues = []
    elapsed = 0
    phrase_path = path.with_name("fala.wav")
    with wave.open(str(path), "wb") as output:
        for index, (text, spoken) in enumerate(zip(scene["falas"], spoken_phrases(scene))):
            track = voice_track(spoken, phrase_path, config, cache, signature)
            with wave.open(str(track), "rb") as source:
                rate = source.getframerate()
                if source.getnchannels() != 1 or source.getsampwidth() != 2:
                    raise ValueError("A voz do modo documental precisa gerar WAV PCM mono de 16 bits.")
                if index == 0:
                    output.setparams(source.getparams())
                    lead = round(rate * .16)
                    samples = []
                    for frame in range(lead):
                        t = frame / rate
                        envelope = min(1, t * 130) * (1 - frame / lead) ** 3
                        value = 7400 * envelope * math.sin(math.tau * (106 * t - 155 * t * t))
                        samples.append(struct.pack("<h", round(value)))
                    output.writeframes(b"".join(samples))
                    elapsed = lead
                elif rate != output.getframerate():
                    raise ValueError("A taxa de amostragem da voz mudou durante a cena.")
                count = source.getnframes()
                if count == 0:
                    raise ValueError("O Piper retornou uma fala vazia.")
                output.writeframes(source.readframes(count))
                cues.append((round(elapsed * 1000 / rate), round((elapsed + count) * 1000 / rate), text))
                elapsed += count
    return cues


def render_video(script, config, work, media, cache=None, signature=None):
    command = [config["ffmpeg_exe"], "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
    filters, concat_inputs, subtitles = [], [], []
    elapsed_frames = 0
    total = len(script["cenas"])
    if cache is not None and any("visual" in scene for scene in script["cenas"]):
        renderer = [
            file_digest(Path(__file__)), file_digest(ROOT / "motion.py"), PIL.__version__,
            font(22).getname(), font(22, True).getname(),
            subprocess.check_output([config["ffmpeg_exe"], "-version"]).splitlines()[0].decode(),
        ]
    for index, scene in enumerate(script["cenas"], 1):
        text = scene["texto"]
        audio = media / f"voz_{index:02}.wav"
        motion = "visual" in scene
        if motion:
            cues = build_motion_audio(scene, audio, config, cache, signature)
        else:
            audio = voice_track(text, audio, config, cache, signature)

        seconds = audio_length(audio)
        frames = math.ceil(seconds * FPS) + PAUSE_FRAMES
        duration = f"{frames / FPS:.3f}"
        video_input = (index - 1) * 2
        audio_input = video_input + 1
        if motion:
            clip = media / f"movimento_{index:02}.mp4"
            label = script.get("serie", "FÁBRICA DE DARK")

            def create_clip(target):
                render_clip(config["ffmpeg_exe"], target, scene, cues, frames, FPS, font, label)

            if cache is None:
                create_clip(clip)
            else:
                clip = cache.asset("cenas", [renderer, scene["visual"], cues, frames, label], "cena.mp4", create_clip)
            command.extend(["-i", str(clip)])
        else:
            card = media / f"cena_{index:02}.png"
            render_card(text, script["titulo"], index, total, card)
            command.extend(["-loop", "1", "-framerate", str(FPS), "-t", duration, "-i", str(card)])
            cues = [(0, round(seconds * 1000), text)]
        command.extend(["-i", str(audio)])
        filters.append(f"[{video_input}:v]scale={WIDTH}:{HEIGHT},setsar=1,format=yuv420p[v{index}]")
        filters.append(
            f"[{audio_input}:a]aresample={AUDIO_RATE},"
            f"aformat=channel_layouts=mono,apad,atrim=duration={duration}[a{index}]"
        )
        concat_inputs.append(f"[v{index}][a{index}]")

        offset = elapsed_frames * 1000 // FPS
        for start, end, phrase in cues:
            caption = textwrap.fill(phrase, width=42, break_long_words=False, break_on_hyphens=False)
            subtitles.append(
                f"{len(subtitles) + 1}\n{timestamp(offset + start)} --> {timestamp(offset + end)}\n{caption}\n"
            )
        elapsed_frames += frames

    filters.append(f"{''.join(concat_inputs)}concat=n={total}:v=1:a=1[video][voice]")
    filters.append("[voice]volume=-3dB[audio]")
    command.extend([
        "-filter_complex_threads", "1", "-filter_complex", ";".join(filters),
        "-map", "[video]", "-map", "[audio]", "-r", str(FPS), "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", str(work / "video_final.mp4"),
    ])
    subprocess.run(command, check=True)
    (work / "legendas.srt").write_text("\n".join(subtitles), encoding="utf-8")


def prepare_voice(script, config, episode, cache, signature):
    tracks = []
    for scene in script["cenas"]:
        paths = [voice_track(text, None, config, cache, signature) for text in spoken_phrases(scene)]
        tracks.append([path.relative_to(episode).as_posix() for path in paths])
    write_json(episode / "narracao.json", {"titulo": script["titulo"], "faixas_por_cena": tracks, **cache.stats})
    print(f"Narração pronta: {episode / 'narracao.json'}")


def main():
    parser = argparse.ArgumentParser(description="Produza um Short narrado no seu computador.")
    parser.add_argument("tema", nargs="?", help="Tema a enviar ao Ollama")
    parser.add_argument("--roteiro", type=Path, help="Roteiro JSON pronto")
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--episodio", type=Path, help="Pasta do episódio, com cache e versões")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--checar-roteiro", action="store_true", help="Validar o JSON sem renderizar")
    mode.add_argument("--somente-voz", action="store_true", help="Preparar as faixas do roteiro no cache")
    args = parser.parse_args()
    if bool(args.tema and args.tema.strip()) == bool(args.roteiro):
        parser.error("Informe um tema ou use --roteiro com um arquivo JSON.")
    if (args.checar_roteiro or args.somente_voz) and args.roteiro is None:
        parser.error("Este modo requer --roteiro.")
    if args.somente_voz and args.episodio is None:
        parser.error("Use --episodio para salvar a narração.")

    try:
        if args.checar_roteiro:
            validate_script(read_json(args.roteiro))
            print("Roteiro válido.")
            return
        config = read_json(args.config)
        script = read_json(args.roteiro) if args.roteiro else make_script(args.tema.strip(), config)
        validate_script(script)
        episode = args.episodio.resolve() if args.episodio else None
        cache = MediaCache(episode / ".cache") if episode else None
        signature = voice_signature(config) if cache is not None else None
        if args.somente_voz:
            prepare_voice(script, config, episode, cache, signature)
            return

        label = args.tema.strip() if args.tema else script["titulo"]
        ascii_label = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode()
        slug = re.sub(r"[^a-z0-9]+", "-", ascii_label.lower()).strip("-")[:45].rstrip("-")
        output = episode / "versoes" if episode else ROOT / "saida"
        output.mkdir(exist_ok=True)
        destination = output / f"{slug or 'video'}-{uuid4().hex[:12]}"

        with tempfile.TemporaryDirectory(prefix=".render-", dir=output) as temp:
            work = Path(temp) / "video"
            media = Path(temp) / "media"
            work.mkdir()
            media.mkdir()
            render_video(script, config, work, media, cache, signature)
            (work / "roteiro.json").write_text(
                json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            if episode:
                manifest = {
                    "schema": 1,
                    "titulo": script["titulo"],
                    "serie": script.get("serie"),
                    "formato": "short-9x16",
                    "fontes": script.get("fontes", []),
                    "versao": destination.name,
                    "estado": "aguardando-revisao",
                    "arquivos": {
                        kind: (destination / name).relative_to(episode).as_posix()
                        for kind, name in (("video", "video_final.mp4"), ("legendas", "legendas.srt"),
                                           ("roteiro", "roteiro.json"))
                    },
                    "processamento": cache.stats,
                }
                write_json(work / "episodio.json", manifest)
            work.rename(destination)
            if episode:
                write_json(episode / "episodio.json", manifest)
                print(json.dumps(cache.stats, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError, wave.Error, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Erro: {error}\n")

    print(f"Vídeo gerado: {destination / 'video_final.mp4'}")


if __name__ == "__main__":
    main()
