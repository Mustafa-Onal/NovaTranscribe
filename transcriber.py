from pathlib import Path
from faster_whisper import WhisperModel

_MODEL: WhisperModel | None = None
_MODEL_NAME: str | None = None


def _get_model(
    model_size: str = "small",
    device: str = "cpu",
    compute_type: str = "int8",
) -> WhisperModel:
    global _MODEL, _MODEL_NAME
    key = f"{model_size}:{device}:{compute_type}"
    if _MODEL is None or _MODEL_NAME != key:
        try:
            _MODEL = WhisperModel(model_size, device=device, compute_type=compute_type)
            _MODEL_NAME = key
        except Exception:
            if device != "cpu":
                _MODEL = WhisperModel(model_size, device="cpu", compute_type="int8")
                _MODEL_NAME = f"{model_size}:cpu:int8"
            else:
                raise
    return _MODEL


def transcribe_audio(
    audio_path: str,
    language: str = "tr",
    model_size: str = "small",
) -> str:
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(f"Ses dosyası bulunamadı: {audio_path}")

    model = _get_model(model_size=model_size, device="cpu", compute_type="int8")
    lang = None if not language or language.lower() == "auto" else language.lower()

    segments, _ = model.transcribe(
        str(path),
        language=lang,
        vad_filter=True,
    )
    text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
    if not text:
        raise RuntimeError("Ses dosyasından metin üretilemedi.")
    return text