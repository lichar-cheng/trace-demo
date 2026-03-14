import os
from pathlib import Path
from typing import Any, Dict

from .config import YoutubePipelineConfig


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

        if os.path.exists(txt_path):
            return {"ok": True, "txt_path": txt_path, "cached": True}

        try:
            audio_size_bytes = Path(audio_path).stat().st_size
        except OSError:
            audio_size_bytes = 0
        audio_size_mb = audio_size_bytes / (1024 * 1024)
        if self.config.max_audio_size_mb and audio_size_mb > float(self.config.max_audio_size_mb):
            return {
                "ok": False,
                "reason": "audio_file_too_large",
                "audio_size_mb": round(audio_size_mb, 2),
                "max_audio_size_mb": self.config.max_audio_size_mb,
            }

        segments, info = model.transcribe(
            audio_path,
            language=self.config.language,
            vad_filter=True,
            beam_size=5,
            condition_on_previous_text=False,
        )

        text_output = []
        for segment in segments:
            text = segment.text.strip()
            if text:
                text_output.append(text)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(text_output))

        return {
            "ok": True,
            "txt_path": txt_path,
            "duration": float(getattr(info, "duration", 0) or 0),
            "cached": False,
        }
