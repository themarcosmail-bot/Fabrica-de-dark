"""Ilustrações e movimento para cenas documentais."""

import bisect
import math
import subprocess
from functools import lru_cache

from PIL import Image, ImageDraw

WIDTH, HEIGHT = 720, 1280
INK = "#EEF2ED"
MUTED = "#A9B4B4"
GRID = "#232C30"
ORANGE = "#FF9862"
MINT = "#74E3CC"
STYLES = {"impacto", "origem", "mecanica", "cosmo", "lemans"}


def ease(value):
    value = min(1.0, max(0.0, value))
    return 1 - (1 - value) ** 3


@lru_cache(maxsize=1)
def backdrop():
    image = Image.new("RGB", (WIDTH, HEIGHT), "#0C1114")
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        glow = max(0, 1 - abs(y - 565) / 540)
        draw.line((0, y, WIDTH, y), fill=(12 + int(7 * glow), 17 + int(12 * glow), 20 + int(15 * glow)))
    for x in range(20, WIDTH, 40):
        draw.line((x, 360, x, 875), fill=GRID)
    for y in range(360, 875, 40):
        draw.line((20, y, 700, y), fill=GRID)
    return image


def point(cx, cy, distance, angle):
    return cx + distance * math.cos(angle), cy + distance * math.sin(angle)


@lru_cache(maxsize=16)
def housing(cx, cy, radius):
    return [apex_position(cx, cy, radius, i * math.tau / 180) for i in range(181)]


def apex_position(cx, cy, radius, angle):
    rx, ry = point(cx, cy, radius * .17, 3 * angle)
    return point(rx, ry, radius, angle)


def rotor(draw, cx, cy, radius, angle, accent, emphasis=False):
    chamber = housing(cx, cy, radius)
    draw.polygon(chamber, fill="#172429")
    draw.line((cx - radius, cy, cx + radius, cy), fill="#2E4147", width=2)
    draw.line((cx, cy - radius * .76, cx, cy + radius * .76), fill="#2E4147", width=2)

    # A cada volta do rotor, o centro descreve três voltas em torno do eixo.
    rx, ry = point(cx, cy, radius * .17, 3 * angle)
    tips = [point(rx, ry, radius, angle + i * math.tau / 3) for i in range(3)]
    outline = []
    for index, (ax, ay) in enumerate(tips):
        bx, by = tips[(index + 1) % 3]
        mx, my = point(rx, ry, radius * .78, angle + (index + .5) * math.tau / 3)
        side = []
        for step in range(13):
            t = step / 12
            u = 1 - t
            side.append((u * u * ax + 2 * u * t * mx + t * t * bx, u * u * ay + 2 * u * t * my + t * t * by))
        outline.extend(side)
        if emphasis:
            rim = [apex_position(cx, cy, radius, angle + (index + step / 42) * math.tau / 3) for step in range(43)]
            fill = ("#563628", "#244640", "#33435B")[index]
            draw.polygon(rim + list(reversed(side)), fill=fill)
    draw.line(chamber, fill="#52666B", width=max(2, round(radius * .035)))
    draw.polygon(outline, fill="#243D40")
    draw.line(outline + [outline[0]], fill=accent, width=max(2, round(radius * .025)))

    hub = radius * .17
    draw.ellipse((rx - hub, ry - hub, rx + hub, ry + hub), fill="#0D171B", outline=accent, width=2)
    for x, y in tips:
        pin = max(3, round(radius * (.055 if emphasis else .032)))
        if emphasis:
            ring = pin * 2
            draw.ellipse((x - ring, y - ring, x + ring, y + ring), outline=accent, width=2)
        draw.ellipse((x - pin, y - pin, x + pin, y + pin), fill=INK)


def fitted_title(draw, title, font):
    for size in (86, 76, 66, 58, 48):
        face = font(size, True)
        if all(draw.textlength(line, font=face) <= 596 for line in title.splitlines()):
            return face
    raise ValueError("O título da cena documental ultrapassa a largura segura.")


def wrap_caption(draw, text, face):
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}" if line else word
        if line and draw.textlength(candidate, font=face) > 550:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return "\n".join(lines)


def draw_origin(draw, t, accent, font):
    x = 84
    draw.line((x, 470, x, 754), fill="#466064", width=3)
    for index, (year, title, note) in enumerate((
        ("1961", "ACORDO TÉCNICO", "Mazda  /  NSU  /  Wankel"),
        ("WANKEL", "CONCEITO DO ROTATIVO", "Desenvolvido por Felix Wankel"),
    )):
        progress = ease((t - index * .65) * 3.5)
        if progress <= 0:
            continue
        y = 468 + index * 213
        slide = int((1 - progress) * 34)
        draw.ellipse((x - 7, y + 7, x + 7, y + 21), fill=accent)
        draw.text((116 + slide, y - 38), year, font=font(88, True), fill=accent)
        draw.text((122 + slide, y + 56), title, font=font(26, True), fill=INK)
        draw.text((122 + slide, y + 96), note, font=font(25), fill=MUTED)


def draw_cosmo(draw, t, accent):
    # Perfil estilizado desenhado para este episódio.
    slide = int((1 - ease(t * 2.4)) * 120)
    body = [(99, 497), (123, 476), (201, 463), (266, 417), (353, 410),
            (408, 427), (463, 459), (568, 469), (598, 488), (607, 513),
            (588, 524), (107, 524), (92, 514)]
    draw.polygon([(x + slide, y) for x, y in body], fill="#283D40", outline=accent, width=3)
    cabin = [(220, 463), (277, 427), (352, 421), (401, 437), (441, 462)]
    draw.polygon([(x + slide, y) for x, y in cabin], fill="#111D23", outline="#7BA7A6", width=2)
    draw.line((348 + slide, 422, 360 + slide, 462), fill="#7BA7A6", width=2)
    for center in (179, 517):
        x = center + slide
        draw.ellipse((x - 30, 488, x + 30, 548), fill="#10171C", outline=accent, width=2)
        for spoke in range(5):
            theta = t * 3.5 + spoke * math.tau / 5
            draw.line(((x, 518), point(x, 518, 17, theta)), fill="#678687", width=2)


def draw_mechanism(draw, style, t, accent, font):
    angle = .3 + t * .94
    if style in {"impacto", "mecanica"}:
        rotor(draw, 353, 612, 224, angle, accent, emphasis=style == "mecanica")
        callout = "3 PONTAS DE VEDAÇÃO" if style == "mecanica" else "ROTOR EM MOVIMENTO"
        draw.text((351, 845), callout, font=font(23, True), fill=accent, anchor="ma")
        return

    count = 2 if style == "cosmo" else 4
    if count == 2:
        draw_cosmo(draw, t, accent)
        positions = [(217, 699), (485, 699)]
        radius = 96
    else:
        positions = [(212, 501), (489, 501), (212, 727), (489, 727)]
        radius = 92
    for index, (x, y) in enumerate(positions):
        reveal = ease((t - index * .12) * 3.3)
        if reveal > 0:
            rotor(draw, x, y + int((1 - reveal) * 22), radius, angle + index * .36, accent)
    label = "2 ROTORES  /  COSMO SPORT" if count == 2 else "4 ROTORES  /  MOTOR R26B"
    draw.text((351, 845), label, font=font(23, True), fill=accent, anchor="ma")


def draw_frame(scene, seconds, fraction, active, font, label):
    visual = scene["visual"]
    style = visual["tipo"]
    accent = MINT if style in {"origem", "cosmo"} else ORANGE
    image = backdrop().copy()
    draw = ImageDraw.Draw(image)
    draw.text((55, 81), label, font=font(22, True), fill=accent)
    draw.line((55, 122, 625, 122), fill="#35484B", width=2)

    title = visual["titulo"]
    offset = int((1 - ease(seconds * 4.5)) * 24)
    draw.multiline_text((52, 149 + offset), title, font=fitted_title(draw, title, font), fill=INK, spacing=-5)
    draw.text((56, 330), visual["chamada"], font=font(22, True), fill=accent)

    if style == "origem":
        draw_origin(draw, seconds, accent, font)
    else:
        draw_mechanism(draw, style, seconds, accent, font)

    if active:
        text, start = active
        slide = int((1 - ease((seconds - start) * 9)) * 10)
        box_y = 935 + slide
        draw.rounded_rectangle((49, box_y, 641, box_y + 138), radius=14, fill="#0A1114", outline="#375053", width=2)
        draw.rounded_rectangle((49, box_y + 19, 55, box_y + 119), radius=3, fill=accent)
        face = font(37, True)
        caption = wrap_caption(draw, text, face)
        if caption.count("\n") > 1:
            face = font(32, True)
            caption = wrap_caption(draw, text, face)
        draw.multiline_text((72, box_y + 24), caption, font=face, fill=INK, spacing=8)

    draw.rounded_rectangle((55, 1111, 625, 1118), radius=4, fill="#2B3B3F")
    draw.rounded_rectangle((55, 1111, 55 + max(7, int(fraction * 570)), 1118), radius=4, fill=accent)
    return image


def render_clip(ffmpeg, path, scene, cues, frames, fps, font, label):
    starts = [start / 1000 for start, _, _ in cues]
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{WIDTH}x{HEIGHT}",
        "-framerate", str(fps), "-i", "pipe:0", "-an", "-c:v", "libx264",
        "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", str(path),
    ]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as process:
        for index in range(frames):
            seconds = index / fps
            cue = bisect.bisect_right(starts, seconds) - 1
            active = None
            if cue >= 0 and seconds < cues[cue][1] / 1000:
                active = (cues[cue][2], starts[cue])
            frame = draw_frame(scene, seconds, index / max(1, frames - 1), active, font, label)
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        if process.wait():
            raise subprocess.CalledProcessError(process.returncode, command)
