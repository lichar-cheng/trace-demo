# Last Edited: 2026-03-12
import os
from pathlib import Path
from typing import Any, Dict

from .config import YoutubePipelineConfig


def format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    if ms == 1000:
        secs += 1
        ms = 0
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


class YoutubeTranscriber:
    def __init__(self, config: YoutubePipelineConfig):
        self.config = config
        self.model = None

    def _get_model(self):
        if self.model is not None:
            return self.model
        try:
            from faster_whisper import WhisperModel
        except Exception:
            return None

        self.model = WhisperModel(
            self.config.model_size,
            device=self.config.device,
            compute_type=self.config.compute_type,
        )
        return self.model

    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        model = self._get_model()
        if not model:
            return {"ok": False, "reason": "faster_whisper_not_installed"}

        audio_name = Path(audio_path).stem
        txt_path = os.path.join(self.config.transcribe_output_dir, f"{audio_name}.txt")
        srt_path = os.path.join(self.config.transcribe_output_dir, f"{audio_name}.srt")

        if os.path.exists(txt_path):
            return {"ok": True, "txt_path": txt_path, "srt_path": srt_path, "cached": True}

        segments, info = model.transcribe(
            audio_path,
            language=self.config.language,
            vad_filter=True,
            beam_size=5,
            condition_on_previous_text=False,
        )

        text_output = []
        srt_output = []

        for idx, segment in enumerate(segments, start=1):
            text = segment.text.strip()
            text_output.append(text)

            start = format_timestamp(segment.start)
            end = format_timestamp(segment.end)
            srt_output.extend([str(idx), f"{start} --> {end}", text, ""])

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(text_output))
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_output))

        return {
            "ok": True,
            "txt_path": txt_path,
            "srt_path": srt_path,
            "duration": float(getattr(info, "duration", 0) or 0),
            "cached": False,
        }
