import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from main import app
from utils.audio_features import AudioValidationError
from utils.media_conversion import MediaDependencyError, ffmpeg_tools, prepare_audio
from test_api import recording


class MediaConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "recording"
        self.path.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"fake container")

    def tearDown(self):
        self.temp.cleanup()

    def probe(self, **changes):
        stream = dict(codec_name="aac", channels=1, sample_rate="22050", duration="2")
        stream.update(changes)
        return subprocess.CompletedProcess([], 0, json.dumps({"streams": [stream]}).encode())

    def test_wav_works_without_ffmpeg(self):
        self.path.write_bytes(recording())
        with patch("utils.media_conversion.ffmpeg_tools", side_effect=AssertionError):
            self.assertIs(prepare_audio(self.path), self.path)

    def test_conversion_uses_input_codec_and_rewinds_wav(self):
        segment = MagicMock()
        segment.frame_rate = 22050
        segment.channels = 1
        segment.frame_count.return_value = 44100
        segment.export.side_effect = lambda output, **kwargs: output.write(recording())
        audio_class = MagicMock()
        audio_class.from_file.return_value = segment
        fake_pydub = types.ModuleType("pydub")
        fake_pydub.AudioSegment = audio_class
        fake_errors = types.ModuleType("pydub.exceptions")
        fake_errors.CouldntDecodeError = type("CouldntDecodeError", (Exception,), {})
        with patch.dict(sys.modules, {"pydub": fake_pydub, "pydub.exceptions": fake_errors}), \
             patch("utils.media_conversion.ffmpeg_tools", return_value=("ffmpeg", "ffprobe")), \
             patch("utils.media_conversion.subprocess.run", return_value=self.probe()):
            output = prepare_audio(self.path)
            self.assertEqual(output.tell(), 0)
            self.assertEqual(output.read(4), b"RIFF")
            output.close()
            audio_class.from_file.assert_called_once_with(str(self.path), format="mp4", codec="aac", duration=61)

    def test_rejects_invalid_metadata(self):
        for changes in ({"duration": "61"}, {"duration": "0.2"}, {"duration": "nan"},
                        {"channels": 6}, {"sample_rate": "192000"}):
            with self.subTest(changes=changes), \
                 patch("utils.media_conversion.ffmpeg_tools", return_value=("ffmpeg", "ffprobe")), \
                 patch("utils.media_conversion.subprocess.run", return_value=self.probe(**changes)):
                with self.assertRaises(AudioValidationError):
                    prepare_audio(self.path)

    def test_no_audio_track(self):
        probe = subprocess.CompletedProcess([], 0, b'{"streams": []}')
        with patch("utils.media_conversion.ffmpeg_tools", return_value=("ffmpeg", "ffprobe")), \
             patch("utils.media_conversion.subprocess.run", return_value=probe):
            with self.assertRaisesRegex(AudioValidationError, "no audio track"):
                prepare_audio(self.path)

    def test_missing_tools_returns_service_error(self):
        with TestClient(app) as client, \
             patch("utils.media_conversion.ffmpeg_tools", side_effect=MediaDependencyError("Missing FFmpeg")):
            response = client.post("/analyze-audio", files={"file": ("recording", self.path.read_bytes(), "application/octet-stream")})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Missing FFmpeg")


class RealMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg, _ = ffmpeg_tools()
            import pydub
        except (MediaDependencyError, ImportError) as exc:
            raise unittest.SkipTest(str(exc))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.env = patch.dict(os.environ, {
            "SMARTKARAOKE_DB": str(self.directory / "test.sqlite3"),
            "SMARTKARAOKE_JBL_MODEL": "", "SMARTKARAOKE_ENABLE_MOCK_MODEL": "0",
        })
        self.env.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.env.stop()
        self.temp.cleanup()

    def encode(self, name, seconds=2, video=False, audio=True):
        path = self.directory / name
        command = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
        if audio:
            command += ["-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=22050:duration={seconds}"]
        if video:
            command += ["-f", "lavfi", "-i", f"color=c=blue:s=160x120:r=10:d={seconds}", "-c:v", "mpeg4"]
        if audio:
            command += ["-c:a", "aac"]
        command += [str(path)]
        subprocess.run(command, check=True, capture_output=True, timeout=30,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        return path.read_bytes()

    def test_real_mp4_video_and_m4a_audio_uploads(self):
        for name, video in (("voice.mp4", True), ("voice.m4a", False)):
            with self.subTest(name=name):
                content = self.encode(name, video=video)
                # Match Android's current filename and MIME type exactly.
                response = self.client.post("/analyze-audio", files={"file": ("recording", content, "application/octet-stream")})
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertFalse(result["is_dummy"])
                self.assertEqual(len(result["features"]["mfcc_mean"]), 13)
                self.assertAlmostEqual(result["features"]["pitch_estimate_hz"], 220, delta=10)
                self.assertEqual(self.client.get("/analyses/" + result["analysis_id"]).status_code, 200)

    def test_real_video_without_audio_is_rejected(self):
        content = self.encode("silent-video.mp4", video=True, audio=False)
        response = self.client.post("/analyze-audio", files={"file": ("video.mp4", content, "video/mp4")})
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("no audio track", response.json()["detail"])

    def test_real_long_audio_is_rejected(self):
        content = self.encode("long.m4a", seconds=61)
        response = self.client.post("/analyze-audio", files={"file": ("long.m4a", content, "audio/mp4")})
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()
