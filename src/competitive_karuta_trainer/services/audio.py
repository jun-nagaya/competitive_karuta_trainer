from __future__ import annotations

from functools import lru_cache
from io import BytesIO

from src.competitive_karuta_trainer.app.ports.session_store import SessionStore
from src.competitive_karuta_trainer.services import data_access

try:
    from gtts import gTTS
except Exception:  # pragma: no cover - import error handling
    gTTS = None  # type: ignore


@lru_cache(maxsize=256)
def synthesize_kami(text: str, lang: str = "ja") -> bytes | None:
    """上の句テキストから音声(mp3)のバイト列を生成して返す。

    - gTTS のネットワーク障害などが起きた場合は None を返す。
    - lru_cache でテキストごとの結果をメモリキャッシュ。
    """
    if not text:
        return None
    if gTTS is None:
        return None
    try:
        tts = gTTS(text=text, lang=lang)
        bio = BytesIO()
        tts.write_to_fp(bio)
        return bio.getvalue()
    except Exception:
        return None


def get_target_audio_bytes(store: SessionStore) -> bytes | None:
    """現在のターゲットの上の句音声を返す（キャッシュ利用）。"""
    target_id = store.get("target_id")
    if target_id is None:
        return None
    cache: dict[int, bytes] = store.get("audio_cache", {})
    if target_id in cache:
        return cache[target_id]
    pair = data_access.get_pair(store, target_id)
    if pair is None:
        return None
    audio_bytes = synthesize_kami(pair.kami)
    if audio_bytes:
        cache[target_id] = audio_bytes
        # 変更を永続化
        store.set("audio_cache", cache)
    return audio_bytes
