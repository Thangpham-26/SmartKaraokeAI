import librosa
import numpy as np
import soundfile as sf

SAMPLE_RATE = 22050


class AudioValidationError(ValueError):
    pass


def load_audio(file_path):
    """Decode 1–60 second WAV/FLAC/OGG recordings and resample to mono."""
    try:
        with sf.SoundFile(file_path) as source:
            if source.format not in {"WAV", "WAVEX", "FLAC", "OGG"}:
                raise AudioValidationError("Use WAV, FLAC or OGG audio.")
            duration = source.frames / source.samplerate
            if not 1 <= duration <= 60:
                raise AudioValidationError("Audio duration must be 1–60 seconds.")
            if source.channels > 2 or source.samplerate > 96000:
                raise AudioValidationError("Use mono/stereo audio at up to 96 kHz.")
            raw = source.read(dtype="float32", always_2d=True)
            sr = source.samplerate
    except AudioValidationError:
        raise
    except (RuntimeError, ValueError) as exc:
        raise AudioValidationError("Cannot decode audio. Use a valid WAV, FLAC or OGG file.") from exc
    if not np.isfinite(raw).all():
        raise AudioValidationError("Audio contains invalid samples.")
    if float(np.max(np.abs(raw))) > 16:
        raise AudioValidationError("Audio sample levels are outside the supported range.")
    clipping = float(np.mean(np.abs(raw) >= 0.999))
    y = raw.mean(axis=1)
    if sr != SAMPLE_RATE:
        y = librosa.resample(y, orig_sr=sr, target_sr=SAMPLE_RATE)
    if float(np.sqrt(np.mean(y ** 2))) < 1e-5:
        raise AudioValidationError("Audio is silent or too quiet to analyze.")
    return y, clipping


def extract_mfcc(file_path):
    """Extract 13 MFCC features per audio frame with librosa.

    Returns an ndarray of shape (13, frames) at a 22050 Hz analysis rate.
    """
    y, _ = load_audio(file_path)
    return librosa.feature.mfcc(y=y, sr=SAMPLE_RATE, n_mfcc=13)


def analyze_features(file_path):
    y, clipping = load_audio(file_path)
    rms = float(np.sqrt(np.mean(y ** 2)))
    spectrum = np.abs(librosa.stft(y))
    power = spectrum ** 2
    frequencies = librosa.fft_frequencies(sr=SAMPLE_RATE)
    total = float(power.sum())
    bands = {name: float(power[(frequencies >= low) & (frequencies < high)].sum() / total)
             for name, low, high in [("low", 80, 250), ("mid", 250, 4000), ("high", 4000, 10000)]}
    frame_rms = librosa.feature.rms(y=y)[0]
    f0 = librosa.yin(y, fmin=65, fmax=1000, sr=SAMPLE_RATE, hop_length=512)
    active = frame_rms > max(0.01, rms * 0.4)
    pitch = float(np.median(f0[active])) if active.any() else None
    mfcc = librosa.feature.mfcc(y=y, sr=SAMPLE_RATE, n_mfcc=13)
    return {
        "duration_seconds": round(len(y) / SAMPLE_RATE, 3),
        "sample_rate_hz": SAMPLE_RATE,
        "rms_dbfs": round(20 * np.log10(max(rms, 1e-12)), 2),
        "peak_dbfs": round(20 * np.log10(max(float(np.max(np.abs(y))), 1e-12)), 2),
        "clipping_fraction": round(clipping, 6),
        "spectral_centroid_hz": round(float(librosa.feature.spectral_centroid(S=spectrum, sr=SAMPLE_RATE).mean()), 2),
        "pitch_estimate_hz": round(pitch, 2) if pitch else None,
        "band_energy_ratio": bands,
        "mfcc_mean": mfcc.mean(axis=1).tolist(),
        "mfcc_std": mfcc.std(axis=1).tolist(),
    }
