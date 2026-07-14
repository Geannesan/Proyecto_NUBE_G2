from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DetectionResult:
    prediction: str
    confidence: float
    probabilities: dict[str, float]
    model_name: str
    evidence: list[str] = field(default_factory=list)
    raw_label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "prediction": self.prediction,
            "confidence": round(float(self.confidence), 2),
            "probabilities": {
                key: round(float(value), 2)
                for key, value in self.probabilities.items()
            },
            "model_name": self.model_name,
            "evidence": self.evidence,
            "raw_label": self.raw_label,
            "metadata": self.metadata,
        }
