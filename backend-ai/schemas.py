from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

DeviceName = Literal["JBL K12 Plus", "Beta Three FX99 Plus"]
VocalType = Literal["male_thick", "male_normal", "male_weak", "female_high", "female_normal", "female_weak"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class EQ(StrictModel):
    low_gain_db: float = Field(ge=-3, le=3)
    mid_gain_db: float = Field(ge=-3, le=3)
    high_gain_db: float = Field(ge=-3, le=3)


class Echo(StrictModel):
    delay_ms: int = Field(ge=80, le=250)
    feedback_percent: int = Field(ge=0, le=30)
    mix_percent: int = Field(ge=0, le=25)


class Reverb(StrictModel):
    decay_seconds: float = Field(ge=0.3, le=2)
    mix_percent: int = Field(ge=0, le=25)


class DSPParameters(StrictModel):
    eq: EQ
    echo: Echo
    reverb: Reverb


class MicEQ(StrictModel):
    bass_pct: float = Field(ge=0, le=100)
    mid_pct: float = Field(ge=0, le=100)
    treble_pct: float = Field(ge=0, le=100)


class JBLEcho(StrictModel):
    level_pct: float = Field(ge=0, le=100)
    delay_ms: int = Field(ge=80, le=250)
    repeat_pct: float = Field(ge=0, le=100)


class JBLReverb(StrictModel):
    level_pct: float = Field(ge=0, le=100)
    # Only mode 2 is represented by the supplied dataset. Do not regress modes.
    mode: Literal[2]


class JBLDSPParameters(StrictModel):
    mic_eq: MicEQ
    echo: JBLEcho
    reverb: JBLReverb


class RecommendationMetadata(StrictModel):
    mapping_status: Literal["unverified"] = "unverified"
    reasons: list[str]
    source: Literal["rules", "model"] = "rules"
    trained_on_mock: bool = False


class Recommendation(DSPParameters, RecommendationMetadata):
    parameter_schema: Literal["generic-v1"] = "generic-v1"


class JBLRecommendation(JBLDSPParameters, RecommendationMetadata):
    parameter_schema: Literal["jbl-v2"] = "jbl-v2"


class JBLFeatures(StrictModel):
    mfcc_mean: list[float] = Field(min_length=13, max_length=13)
    pitch_estimate_hz: float = Field(ge=65, le=1000)
    vocal_type: VocalType | None = None


class PredictDSPRequest(StrictModel):
    device: Literal["JBL K12 Plus"] = "JBL K12 Plus"
    features: JBLFeatures
    room_rt60_seconds: float = Field(ge=0.1, le=5)


class AnalysisResponse(BaseModel):
    analysis_id: str
    filename: str
    engine: str
    is_dummy: bool
    features: dict
    room: dict
    recommendations: dict[str, JBLRecommendation | Recommendation]
    warnings: list[str]


class Feedback(StrictModel):
    analysis_id: UUID
    device: DeviceName
    rating: int = Field(ge=1, le=5)
    notes: str = Field(default="", max_length=2000)
    expert_parameters: JBLDSPParameters | DSPParameters | None = None

    @model_validator(mode="after")
    def match_device_parameters(self):
        if self.expert_parameters is not None:
            expected = JBLDSPParameters if self.device == "JBL K12 Plus" else DSPParameters
            if not isinstance(self.expert_parameters, expected):
                raise ValueError("expert_parameters schema does not match the selected device")
        return self
