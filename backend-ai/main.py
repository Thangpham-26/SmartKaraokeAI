"""Local development API. Run from backend-ai with uvicorn main:app."""
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from schemas import AnalysisResponse, Feedback, PredictDSPRequest, VocalType
from storage import get_analysis, save_analysis, save_feedback
from utils.audio_features import AudioValidationError, analyze_features
from utils.media_conversion import MediaDependencyError, prepare_audio
from utils.recommendations import DEVICE_PROFILES, jbl_rules, recommend
from utils.model_inference import model_status, predict_jbl

app = FastAPI(title="SmartKaraokeAI", version="0.3.0")
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@app.get("/health")
def health():
    return {"status": "ok", "engine": "rules-v2-with-optional-jbl-candidate", **model_status()}


@app.get("/devices")
def devices():
    return DEVICE_PROFILES


@app.post("/analyze-audio", response_model=AnalysisResponse)
async def analyze_audio(
    file: UploadFile = File(...),
    room_rt60_seconds: float | None = Form(None, ge=0.1, le=5.0),
    vocal_type: VocalType | None = Form(None),
):
    """Analyze solo vocals. Optional RT60 must come from a separate measurement."""
    try:
        with TemporaryDirectory(prefix="smartkaraoke-") as temp:
            path = Path(temp) / "audio"
            size = 0
            with path.open("wb") as target:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise HTTPException(413, "Maximum upload size is 20 MiB.")
                    target.write(chunk)
            if size == 0:
                raise HTTPException(400, "Audio file is empty.")
            try:
                audio_source = await run_in_threadpool(prepare_audio, path)
                try:
                    features = await run_in_threadpool(analyze_features, audio_source)
                finally:
                    if audio_source is not path:
                        audio_source.close()
            except AudioValidationError as exc:
                raise HTTPException(422, str(exc)) from exc
            except MediaDependencyError as exc:
                raise HTTPException(503, str(exc)) from exc
        if vocal_type is not None:
            features["vocal_type"] = vocal_type
        recommendations, warnings = recommend(features, room_rt60_seconds)
        prediction, model_warning = await run_in_threadpool(predict_jbl, features, room_rt60_seconds)
        if prediction is not None:
            recommendations["JBL K12 Plus"] = prediction
        if model_warning:
            warnings.append(model_warning)
        result = AnalysisResponse(
            analysis_id=str(uuid4()), filename=Path((file.filename or "audio").replace("\\", "/")).name,
            engine="jbl-model-with-beta-rules" if prediction else "rules-v2", is_dummy=False, features=features,
            room={"rt60_seconds": room_rt60_seconds,
                  "source": "user_measurement" if room_rt60_seconds is not None else "unknown"},
            recommendations=recommendations, warnings=warnings,
        )
        await run_in_threadpool(save_analysis, result.model_dump())
        return result
    finally:
        await file.close()


@app.post("/predict-dsp", response_model=AnalysisResponse)
def predict_dsp(payload: PredictDSPRequest):
    """Predict from already extracted features; useful for dataset pipeline checks."""
    features = payload.features.model_dump(exclude_none=True)
    prediction, warning = predict_jbl(features, payload.room_rt60_seconds)
    recommendation = prediction or jbl_rules(features, payload.room_rt60_seconds)
    warnings = ["Device controls remain unverified; this is an experimental recommendation."]
    if warning:
        warnings.append(warning)
    if not features.get("vocal_type") and prediction is None:
        warnings.append("Vocal type is unknown; JBL rule fallback uses 38% bass.")
    result = AnalysisResponse(
        analysis_id=str(uuid4()), filename="extracted-features", is_dummy=False,
        engine="jbl-v2-model" if prediction else "rules-v2", features=features,
        room={"rt60_seconds": payload.room_rt60_seconds, "source": "user_measurement"},
        recommendations={"JBL K12 Plus": recommendation}, warnings=warnings,
    )
    save_analysis(result.model_dump())
    return result


@app.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def analysis(analysis_id: str):
    result = get_analysis(analysis_id)
    if result is None:
        raise HTTPException(404, "Analysis not found.")
    return result


@app.post("/feedback", status_code=201)
def feedback(payload: Feedback):
    if get_analysis(str(payload.analysis_id)) is None:
        raise HTTPException(404, "Analysis not found.")
    return {"feedback_id": save_feedback(payload.model_dump(mode="json"))}
