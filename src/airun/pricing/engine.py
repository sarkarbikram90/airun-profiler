"""Cost and pricing engine for calculating AI workload token and infra costs."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import yaml
from pydantic import BaseModel

from airun.pricing.defaults import DEFAULT_MODEL_PRICING


class ModelPricingConfig(BaseModel):
    input_cost_per_1k_tokens: float = 0.0
    output_cost_per_1k_tokens: float = 0.0
    estimated_infra_cost_per_hour: Optional[float] = None


class CostEngine:
    """Pricing calculation engine with custom pricing overrides."""

    def __init__(self, custom_pricing_path: Optional[Path] = None):
        self._pricing: Dict[str, ModelPricingConfig] = {}
        self._load_defaults()
        if custom_pricing_path:
            self.load_custom_pricing(custom_pricing_path)

    def _load_defaults(self) -> None:
        for model_name, price_dict in DEFAULT_MODEL_PRICING.items():
            self._pricing[model_name.lower()] = ModelPricingConfig(**price_dict)

    def load_custom_pricing(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            models_data = data.get("models", data)
            for model_name, price_dict in models_data.items():
                if isinstance(price_dict, dict):
                    self._pricing[model_name.lower()] = ModelPricingConfig(**price_dict)
        except Exception:
            pass

    def register_model_pricing(self, model: str, pricing: ModelPricingConfig) -> None:
        self._pricing[model.lower()] = pricing

    def normalize_model_name(self, model: str) -> str:
        model = model.lower().strip()
        if "/" in model:
            model = model.split("/")[-1]
        return model

    def calculate_cost(
        self,
        model: Optional[str],
        input_tokens: Optional[int] = 0,
        output_tokens: Optional[int] = 0,
        duration_ms: Optional[float] = None,
        accelerator: Optional[str] = None,
        include_energy: bool = False,
    ) -> Optional[float]:
        """
        Calculate total cost in USD for a model call.
        Returns None if model is unknown or not provided.
        """
        if not model:
            return None

        normalized = self.normalize_model_name(model)
        pricing = self._pricing.get(normalized)

        # Fallback partial matching (e.g. gpt-4o-mini-2024-07-18 -> gpt-4o-mini)
        if not pricing:
            for key, val in self._pricing.items():
                if key in normalized or normalized in key:
                    pricing = val
                    break

        if not pricing:
            return None

        in_tok = input_tokens or 0
        out_tok = output_tokens or 0

        token_cost = (in_tok / 1000.0) * pricing.input_cost_per_1k_tokens + (
            out_tok / 1000.0
        ) * pricing.output_cost_per_1k_tokens

        infra_cost = 0.0
        if pricing.estimated_infra_cost_per_hour and duration_ms:
            hours = duration_ms / (1000.0 * 3600.0)
            infra_cost = hours * pricing.estimated_infra_cost_per_hour

        energy_cost = 0.0
        if include_energy and duration_ms:
            from airun.pricing.energy import calculate_energy

            metrics = calculate_energy(duration_ms=duration_ms, accelerator=accelerator)
            energy_cost = metrics.energy_cost_usd

        return token_cost + infra_cost + energy_cost


# Global default engine instance
_DEFAULT_ENGINE: Optional[CostEngine] = None


def get_cost_engine() -> CostEngine:
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        _DEFAULT_ENGINE = CostEngine()
    return _DEFAULT_ENGINE


def calculate_cost(
    model: Optional[str],
    input_tokens: Optional[int] = 0,
    output_tokens: Optional[int] = 0,
    duration_ms: Optional[float] = None,
    accelerator: Optional[str] = None,
    include_energy: bool = False,
) -> Optional[float]:
    return get_cost_engine().calculate_cost(
        model, input_tokens, output_tokens, duration_ms, accelerator, include_energy
    )
