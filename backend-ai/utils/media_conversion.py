"""Convert MPEG-4 uploads to an in-memory WAV before feature extraction."""
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

from utils.audio_features import AudioValidationError


class MediaDependencyError(RuntimeError):
    pass


def ffmpeg_tools():
    """Find a portable Windows installation or the executables on PATH."""
    local_bin = Path(__file__).resolve().parents[2] / ".tools" / "ffmpeg" / "bin"
    bin_dir = Path(os.environ.get("FFMPEG_BIN_DIR", str(local_bin)))
    extension = ".exe" if os.name == "nt" else ""
    found = []
    for name in ("ffmpeg", "ffprobe"):
        candidate = bin_dir / (name + extension)
        executable = str(candidate) if candidate.is_file() else shutil.which(name)
        if not executable:
            raise MediaDependencyError(
                "MP4/M4A conversion requires FFmpeg and ffprobe. "
                "Run backend-ai/install-media.ps1 or set FFMPEG_BIN_DIR to their bin directory."
            )
        found.append(executable)
    return tuple(found)


def is_mpeg4(path):
    # Android may upload a filename without an extension and a generic MIME type.
    # Check the ISO base media container signature instead of trusting metadata.
    with Path(path).open("rb") as source:
        header = source.read(12)
    return len(header) == 12 and header[4:8] == b"ftyp"


def prepare_audio(path):
    """Return the original audio path or a seekable WAV buffer for MP4/M4A."""
    if not is_mpeg4(path):
        return path
    ffmpeg, ffprobe = ffmpeg_tools()
    try:
        probe = subprocess.run(
            [ffprobe, "-v", "error", "-protocol_whitelist", "file,pipe",
             "-select_streams", "a:0", "-show_entries",
             "stream=codec_name,channels,sample_rate,duration:format=format_name,duration", "-of", "json", str(path)],
            capture_output=True, check=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        metadata = json.loads(probe.stdout)
        streams = metadata.get("streams", [])
        if not streams:
            raise AudioValidationError("MP4/M4A file has no audio track.")
        stream = streams[0]
        codec = stream["codec_name"]
        if not codec or codec == "unknown":
            raise AudioValidationError("MP4/M4A audio codec is unsupported.")
        duration = float(stream.get("duration", metadata.get("format", {}).get("duration", "nan")))
        if not math.isfinite(duration) or not 1 <= duration <= 60:
            raise AudioValidationError("Audio duration must be 1–60 seconds.")
        if not 1 <= int(stream["channels"]) <= 2 or not 1 <= int(stream["sample_rate"]) <= 96000:
            raise AudioValidationError("Use mono/stereo audio at up to 96 kHz.")
    except AudioValidationError:
        raise
    except (subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        raise AudioValidationError("Cannot decode MP4/M4A audio or read its duration.") from exc
    except OSError as exc:
        raise MediaDependencyError("Cannot run ffprobe. Check the FFmpeg installation.") from exc

    try:
        from pydub import AudioSegment
        from pydub.exceptions import CouldntDecodeError
    except ImportError as exc:
        raise MediaDependencyError("MP4/M4A conversion requires pydub. Install backend requirements.") from exc
    AudioSegment.converter = ffmpeg
    try:
        # Supplying a codec avoids pydub's separate PATH-based ffprobe lookup.
        # Decode at most 61 seconds so false duration metadata cannot cause a huge WAV.
        audio = AudioSegment.from_file(str(path), format="mp4", codec=codec, duration=61)
        if not 1 <= audio.frame_count() / audio.frame_rate <= 60:
            raise AudioValidationError("Audio duration must be 1–60 seconds.")
        if audio.channels > 2 or audio.frame_rate > 96000:
            raise AudioValidationError("Use mono/stereo audio at up to 96 kHz.")
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)
        return wav_io
    except CouldntDecodeError as exc:
        raise AudioValidationError("Cannot decode MP4/M4A audio. Use a valid file with an audio track.") from exc
    except OSError as exc:
        raise MediaDependencyError("Cannot run FFmpeg. Check the FFmpeg installation.") from exc
