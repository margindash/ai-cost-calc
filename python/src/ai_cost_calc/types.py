from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AiCostCalcError:
    message: str
    cause: Exception | None = None
    events: list | None = None


@dataclass
class ModelPricing:
    slug: str
    input_price_per_1m: float
    output_price_per_1m: float


@dataclass
class CostResult:
    model: str
    input_cost: float
    output_cost: float
    total_cost: float
    input_tokens: int = 0
    output_tokens: int = 0
    estimated: bool = False
