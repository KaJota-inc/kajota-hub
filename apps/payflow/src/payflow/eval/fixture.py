import json
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from payflow.models import Category, Dialect, Retryability


class FixtureKind(str, Enum):
    IN_KB = "in_kb"
    OUT_OF_KB = "out_of_kb"
    ADVERSARIAL = "adversarial"
    MALFORMED = "malformed"


class Fixture(BaseModel):
    id: str
    kind: FixtureKind
    envelope_format: str = Field(..., description="soap | json | audit_trail")
    envelope_content: str
    dialect: Optional[Dialect] = None
    expected_retry_strategy: Optional[Retryability] = Field(
        None,
        description="Ground-truth retry strategy. None means unlabelled (real-pilot data awaiting ops labelling).",
    )
    expected_category: Optional[Category] = None
    expected_retryable: Optional[bool] = None
    expected_confidence_min: str = Field(
        "medium",
        description="Weakest acceptable confidence for a correct prediction (high|medium|low).",
    )
    is_labelled: bool = Field(True, description="False for real-pilot fixtures awaiting human labels.")
    source_code: Optional[str] = Field(None, description="Response code minted for; None for malformed or pilot data.")
    notes: str = ""


class Prediction(BaseModel):
    fixture_id: str
    mode: str
    predicted_retry_strategy: Retryability
    predicted_retryable: bool
    predicted_confidence: str
    matched_kb: bool
    duration_ms: float
    error: Optional[str] = None


def save_fixtures(fixtures: list[Fixture], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for fx in fixtures:
            f.write(fx.model_dump_json() + "\n")


def load_fixtures(path: str | Path) -> list[Fixture]:
    fixtures: list[Fixture] = []
    with Path(path).open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            fixtures.append(Fixture.model_validate_json(line))
    return fixtures


def save_predictions(predictions: list[Prediction], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for p in predictions:
            f.write(p.model_dump_json() + "\n")


def load_predictions(path: str | Path) -> list[Prediction]:
    predictions: list[Prediction] = []
    with Path(path).open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            predictions.append(Prediction.model_validate_json(line))
    return predictions
