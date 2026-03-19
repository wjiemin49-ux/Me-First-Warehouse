from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


DEFAULT_OUTPUT_DIR = Path(r"D:\me\音乐\AI音乐尝试存放处")
DEFAULT_CONCEPTS_PATH = Path(__file__).with_name("douyin_concepts.json")
TREND_SIGNATURE = (
    "TikTok/Douyin-ready, catchy chorus, short-video friendly, strong rhythm, "
    "simple modern pop phrasing, polished electronic texture"
)


@dataclass
class SongConcept:
    seed_title: str
    lyrics_prompt: str
    music_prompt: str
    manual_lyrics: str | None = None
    manual_style_tags: str | None = None


class MiniMaxError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a batch of MiniMax songs plus sidecar lyrics files."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Where MP3 and lyrics files are saved. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--concepts-file",
        type=Path,
        default=DEFAULT_CONCEPTS_PATH,
        help=f"JSON file describing song concepts. Default: {DEFAULT_CONCEPTS_PATH}",
    )
    parser.add_argument(
        "--model",
        default="music-2.5",
        choices=["music-2.5", "music-2.5+"],
        help="MiniMax music model to use.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="How many concepts to generate from the concepts file.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Keep going when one concept fails.",
    )
    return parser.parse_args()


def load_concepts(path: Path, count: int) -> list[SongConcept]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    concepts = [
        SongConcept(
            seed_title=item["seed_title"].strip(),
            lyrics_prompt=item["lyrics_prompt"].strip(),
            music_prompt=item["music_prompt"].strip(),
            manual_lyrics=(item.get("manual_lyrics") or "").strip() or None,
            manual_style_tags=(item.get("manual_style_tags") or "").strip() or None,
        )
        for item in raw
    ]
    return concepts[:count]


def build_session(api_key: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    )
    return session


def api_urls(endpoint: str) -> list[str]:
    candidates = [
        os.environ.get("MINIMAX_BASE_URL"),
        "https://api.minimax.chat/v1",
        "https://api.minimaxi.com/v1",
        "https://api.minimax.io/v1",
    ]
    urls: list[str] = []
    seen: set[str] = set()
    for base in candidates:
        if not base:
            continue
        normalized = base.rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        urls.append(f"{normalized}/{endpoint.lstrip('/')}")
    return urls


def safe_status_message(payload: dict[str, Any]) -> str:
    base_resp = payload.get("base_resp") or {}
    return str(base_resp.get("status_msg") or payload)


def post_json(
    session: requests.Session,
    endpoint: str,
    payload: dict[str, Any],
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    failures: list[str] = []
    for url in api_urls(endpoint):
        try:
            response = session.post(url, json=payload, timeout=timeout_seconds)
            response.raise_for_status()
            data = response.json()
            base_resp = data.get("base_resp") or {}
            status_code = base_resp.get("status_code")
            status_message = safe_status_message(data)
            if status_code in (0, "0", None):
                data["_request_url"] = url
                return data
            if "invalid api key" in status_message.lower():
                failures.append(f"{url} -> {status_message}")
                continue
            raise MiniMaxError(
                f"MiniMax API failed via {url}: {status_code} {status_message}"
            )
        except requests.RequestException as exc:
            failures.append(f"{url} -> {exc}")
            continue
    raise MiniMaxError("All MiniMax endpoints failed: " + " | ".join(failures))


def slugify_filename(name: str) -> str:
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "", name)
    clean = re.sub(r"\s+", " ", clean).strip().strip(".")
    return clean[:80] or "untitled"


def make_base_name(index: int, title: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{index:02d}_{slugify_filename(title)}"


def call_lyrics_generation(
    session: requests.Session,
    concept: SongConcept,
) -> dict[str, Any]:
    payload = {
        "mode": "write_full_song",
        "title": concept.seed_title,
        "prompt": concept.lyrics_prompt,
    }
    return post_json(session, "lyrics_generation", payload, timeout_seconds=180)


def extract_audio_payload(music_response: dict[str, Any]) -> tuple[str, str] | None:
    audio = (music_response.get("data") or {}).get("audio")
    if isinstance(audio, str) and audio.startswith(("http://", "https://")):
        return ("url", audio)
    if isinstance(audio, str):
        compact = audio.strip()
        if compact and re.fullmatch(r"[0-9a-fA-F]+", compact):
            return ("hex", compact)
    if isinstance(audio, dict):
        for key in ("url", "audio_url", "download_url"):
            value = audio.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return ("url", value)
        for key in ("hex", "audio_hex"):
            value = audio.get(key)
            if isinstance(value, str) and value and re.fullmatch(r"[0-9a-fA-F]+", value):
                return ("hex", value)
    return None


def call_music_generation(
    session: requests.Session,
    model: str,
    title: str,
    style_tags: str,
    lyrics: str,
    concept: SongConcept,
) -> dict[str, Any]:
    prompt_parts = [style_tags, concept.music_prompt, TREND_SIGNATURE, f"title feel: {title}"]
    payload = {
        "model": model,
        "prompt": ", ".join(part for part in prompt_parts if part),
        "lyrics": lyrics,
        "output_format": "hex",
        "audio_setting": {
            "sample_rate": 44100,
            "bitrate": 256000,
            "format": "mp3",
        },
    }
    return post_json(session, "music_generation", payload, timeout_seconds=900)


def download_file(session: requests.Session, url: str, destination: Path) -> None:
    with session.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    handle.write(chunk)


def write_audio_file(
    session: requests.Session,
    audio_payload: tuple[str, str],
    destination: Path,
) -> None:
    kind, value = audio_payload
    if kind == "url":
        download_file(session, value, destination)
        return
    if kind == "hex":
        destination.write_bytes(bytes.fromhex(value))
        return
    raise MiniMaxError(f"Unsupported audio payload kind: {kind}")


def try_embed_metadata(
    mp3_path: Path,
    title: str,
    style_tags: str,
    lyrics: str,
) -> bool:
    try:
        from mutagen.id3 import ID3, COMM, TIT2, TPE1, USLT
        from mutagen.id3._util import ID3NoHeaderError
    except ImportError:
        return False

    try:
        tags = ID3(mp3_path)
    except ID3NoHeaderError:
        tags = ID3()

    tags.delall("TIT2")
    tags.delall("TPE1")
    tags.delall("COMM")
    tags.delall("USLT")
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text="MiniMax Music 2.5"))
    tags.add(COMM(encoding=3, lang="eng", desc="style_tags", text=style_tags))
    tags.add(USLT(encoding=3, lang="eng", desc="lyrics", text=lyrics))
    tags.save(mp3_path)
    return True


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def build_lyrics_sidecar(title: str, style_tags: str, lyrics: str) -> str:
    return (
        f"歌名: {title}\n"
        f"风格标签: {style_tags}\n"
        f"生成时间: {datetime.now().isoformat(timespec='seconds')}\n\n"
        f"{lyrics}\n"
    )


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        print("Missing MINIMAX_API_KEY environment variable.", file=sys.stderr)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    concepts = load_concepts(args.concepts_file, args.count)
    session = build_session(api_key)
    run_summary: list[dict[str, Any]] = []

    for index, concept in enumerate(concepts, start=1):
        print(f"[{index}/{len(concepts)}] Generating concept: {concept.seed_title}")
        try:
            if concept.manual_lyrics:
                lyrics_response = {
                    "song_title": concept.seed_title,
                    "style_tags": concept.manual_style_tags or "",
                    "lyrics": concept.manual_lyrics,
                    "_request_url": "manual_lyrics",
                }
                title = concept.seed_title
                style_tags = concept.manual_style_tags or ""
                lyrics = concept.manual_lyrics
            else:
                lyrics_response = call_lyrics_generation(session, concept)
                title = (lyrics_response.get("song_title") or concept.seed_title).strip()
                style_tags = str(lyrics_response.get("style_tags") or "").strip()
                lyrics = str(lyrics_response.get("lyrics") or "").strip()
                if not lyrics:
                    raise MiniMaxError("Lyrics generation returned empty lyrics.")

            music_response = call_music_generation(
                session=session,
                model=args.model,
                title=title,
                style_tags=style_tags,
                lyrics=lyrics,
                concept=concept,
            )
            audio_payload = extract_audio_payload(music_response)
            if not audio_payload:
                raise MiniMaxError(
                    "Music generation succeeded but no usable audio payload was returned."
                )

            base_name = make_base_name(index, title)
            mp3_path = args.output_dir / f"{base_name}.mp3"
            lyrics_path = args.output_dir / f"{base_name}.lyrics.txt"
            manifest_path = args.output_dir / f"{base_name}.json"

            write_audio_file(session, audio_payload, mp3_path)
            write_text(lyrics_path, build_lyrics_sidecar(title, style_tags, lyrics))

            metadata_embedded = try_embed_metadata(
                mp3_path=mp3_path,
                title=title,
                style_tags=style_tags,
                lyrics=lyrics,
            )

            manifest = {
                "song_title": title,
                "seed_title": concept.seed_title,
                "style_tags": style_tags,
                "lyrics_prompt": concept.lyrics_prompt,
                "music_prompt": concept.music_prompt,
                "model": args.model,
                "lyrics_endpoint": lyrics_response.get("_request_url"),
                "music_endpoint": music_response.get("_request_url"),
                "audio_payload_kind": audio_payload[0],
                "audio_payload_ref": audio_payload[1][:120] if audio_payload[0] == "url" else None,
                "lyrics_file": str(lyrics_path),
                "mp3_file": str(mp3_path),
                "metadata_embedded": metadata_embedded,
                "lyrics_response": lyrics_response,
                "music_response": music_response,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
            }
            write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))

            run_summary.append(
                {
                    "song_title": title,
                    "mp3_file": str(mp3_path),
                    "lyrics_file": str(lyrics_path),
                    "metadata_embedded": metadata_embedded,
                    "duration_ms": (music_response.get("extra_info") or {}).get("music_duration"),
                }
            )
            print(f"  Saved: {mp3_path.name}")
        except Exception as exc:  # noqa: BLE001
            print(f"  Failed: {exc}", file=sys.stderr)
            run_summary.append(
                {
                    "song_title": concept.seed_title,
                    "error": str(exc),
                }
            )
            if not args.continue_on_error:
                break

    summary_path = args.output_dir / "run_summary.json"
    write_text(summary_path, json.dumps(run_summary, ensure_ascii=False, indent=2))
    print(f"Summary written to: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
