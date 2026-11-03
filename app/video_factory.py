"""Video production helpers for the content workflow."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import uuid
import wave
from pathlib import Path

VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
SLIDE_SECONDS = 4
DEFAULT_VIDEO_DIR = Path(__file__).parent / "generated" / "videos"


def _format_timestamp(seconds: float) -> str:
    total_milliseconds = round(seconds * 1000)
    total_seconds, milliseconds = divmod(total_milliseconds, 1000)
    minutes, secs = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def _chunk_script(script: str, max_chars: int = 80) -> list[str]:
    sentences = re.split(r"(?<=[.!?।])\s+|\n+", (script or "").strip())
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        cleaned = sentence.strip()
        if not cleaned:
            continue
        if len(current) + len(cleaned) + 1 <= max_chars:
            current = f"{current} {cleaned}".strip()
        else:
            if current:
                chunks.append(current)
            current = cleaned

    if current:
        chunks.append(current)

    return chunks or [script.strip() or "Video content"]


def generate_subtitles(
    script: str,
    seconds_per_chunk: float = 2,
    total_duration_seconds: float | None = None,
) -> str:
    """Create a basic SRT subtitle file from a spoken script."""
    chunks = _chunk_script(script)
    lines: list[str] = []
    cue_duration = total_duration_seconds / len(chunks) if total_duration_seconds else seconds_per_chunk

    for idx, chunk in enumerate(chunks, start=1):
        start = (idx - 1) * cue_duration
        end = idx * cue_duration
        lines.append(f"{idx}\n{_format_timestamp(start)} --> {_format_timestamp(end)}\n{chunk}\n")

    return "\n".join(lines).strip() + "\n"


def _load_font(size: int, bold: bool = False):
    from PIL import ImageFont

    font_name = "NotoSansDevanagari-Bold.ttf" if bold else "NotoSansDevanagari-Regular.ttf"
    font_path = Path("/usr/share/fonts/truetype/noto") / font_name
    if not font_path.exists():
        font_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        font_path = Path("/usr/share/fonts/truetype/dejavu") / font_name
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\n".join(lines)


def _render_slide(topic: str, text: str, slide_number: int, slide_count: int):
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), "#102a2b")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 18, VIDEO_HEIGHT), fill="#b9e3ca")
    draw.text((76, 56), "VIRENDRA AI STUDIO", font=_load_font(23, bold=True), fill="#b9e3ca")
    title_font = _load_font(34, bold=True)
    draw.text((76, 125), _wrap_text(draw, topic, title_font, 1080), font=title_font, fill="#f3f4ed", spacing=10)
    draw.rounded_rectangle((76, 205, 1204, 615), radius=20, fill="#1c3b3a")
    body_font = _load_font(42)
    wrapped = _wrap_text(draw, text, body_font, 1000)
    draw.multiline_text((126, 267), wrapped, font=body_font, fill="#f3f4ed", spacing=22, align="left")
    draw.text((76, 660), "LOCAL VIDEO DRAFT  |  REVIEW BEFORE UPLOAD", font=_load_font(20), fill="#a9c8bd")
    counter = f"{slide_number:02d} / {slide_count:02d}"
    counter_font = _load_font(22)
    counter_width = draw.textbbox((0, 0), counter, font=counter_font)[2]
    draw.text((1204 - counter_width, 658), counter, font=counter_font, fill="#b9e3ca")
    return image


def render_mp4_video(
    topic: str,
    description: str,
    style: str = "government",
    output_dir: str | Path | None = None,
    output_name: str | None = None,
) -> dict:
    """Render captioned slides with offline Hindi narration into a local MP4."""
    cleaned_topic = (topic or "government update").strip()
    cleaned_description = (description or "Video content").strip()
    safe_style = (style or "government").strip().lower()
    ffmpeg = shutil.which("ffmpeg")
    espeak = shutil.which("espeak-ng")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to render MP4 files; install it in the backend image")
    if not espeak:
        raise RuntimeError("espeak-ng is required for local Hindi narration; install it in the backend image")

    chunks = _chunk_script(cleaned_description, max_chars=150)
    destination = Path(output_dir) if output_dir else DEFAULT_VIDEO_DIR
    destination.mkdir(parents=True, exist_ok=True)
    filename = output_name or f"{uuid.uuid4().hex}.mp4"
    if not filename.endswith(".mp4") or Path(filename).name != filename:
        raise ValueError("output_name must be a simple .mp4 filename")
    output_path = destination / filename
    subtitle_path = output_path.with_suffix(".srt")

    with tempfile.TemporaryDirectory(prefix="studio-video-") as temp_dir:
        temp_path = Path(temp_dir)
        audio_path = temp_path / "narration.wav"
        subprocess.run(
            [espeak, "-v", "hi", "-s", "145", "-w", str(audio_path), cleaned_description],
            check=True,
            capture_output=True,
            text=True,
        )
        with wave.open(str(audio_path), "rb") as narration:
            duration_seconds = narration.getnframes() / narration.getframerate()
        slide_seconds = duration_seconds / len(chunks)

        frame_paths: list[Path] = []
        for index, chunk in enumerate(chunks, start=1):
            frame_path = temp_path / f"slide-{index:04d}.png"
            _render_slide(cleaned_topic, chunk, index, len(chunks)).save(frame_path)
            frame_paths.append(frame_path)

        concat_path = temp_path / "slides.txt"
        concat_lines = [f"file '{frame.as_posix()}'\nduration {slide_seconds:.3f}" for frame in frame_paths]
        concat_lines.append(f"file '{frame_paths[-1].as_posix()}'")
        concat_path.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-i",
                str(audio_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-t",
                f"{duration_seconds:.3f}",
                "-vf",
                "fps=30",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    subtitle_path.write_text(
        generate_subtitles(cleaned_description, total_duration_seconds=duration_seconds),
        encoding="utf-8",
    )

    return {
        "topic": cleaned_topic,
        "description": cleaned_description,
        "style": safe_style,
        "format": "mp4",
        "status": "rendered",
        "output_path": str(output_path),
        "subtitle_path": str(subtitle_path),
        "duration_seconds": round(duration_seconds, 2),
        "audio": "Hindi narration",
    }


def plan_mp4_video(topic: str, description: str, style: str = "government") -> dict:
    """Describe a prospective video without rendering files or requiring media tools."""
    cleaned_topic = (topic or "government update").strip()
    return {
        "topic": cleaned_topic,
        "description": (description or "Video content").strip(),
        "style": (style or "government").strip().lower(),
        "format": "mp4",
        "status": "planned",
        "output_path": None,
    }


def build_video_plan(topic: str, script: str) -> dict:
    """Return a simple video-factory payload with subtitles, voiceover script, and render metadata."""
    subtitle_text = generate_subtitles(script)
    chunks = _chunk_script(script)
    video_render = plan_mp4_video(topic, script, "government")
    return {
        "topic": topic,
        "voice_style": "clear_hindi_male",
        "estimated_duration_seconds": max(20, len(chunks) * 2),
        "subtitle_srt": subtitle_text,
        "voiceover_script": script.strip(),
        "render": video_render,
    }
