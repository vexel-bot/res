"""Bounded, local-only preparation. No arbitrary provider, path, model or filter."""
from typing import Literal
from pydantic import Field, model_validator
from .contracts import StudioContract

JOB_TYPE = "material_effect"
PROVIDER = "local.material-effects-v1"


class EffectRequest(StudioContract):
    expected_revision: int = Field(ge=1)
    kit_revision: int = Field(ge=1)
    request_key: str = Field(min_length=8,max_length=80)
    source_asset_id: str = Field(min_length=1,max_length=120)
    operation: Literal["segment_person","replace_background","localized_edit"]
    prompt: str = Field(default="",max_length=2000)
    seed: int = Field(default=20261108,ge=0,le=2**32-1)
    strength: float = Field(default=.8,ge=.2,le=.9,allow_inf_nan=False)
    start_seconds: float = Field(default=0,ge=0,le=3600,allow_inf_nan=False)
    duration_seconds: int = Field(default=6,ge=2,le=12)
    preserve_interaction_area: bool = Field(default=True,strict=True)
    region: tuple[float,float,float,float] | None = None

    @model_validator(mode="after")
    def valid_operation(self):
        if self.operation != "segment_person" and not self.prompt.strip():
            raise ValueError("material_effect_prompt_required")
        if self.operation=="localized_edit":
            if not self.region or any(not 0<=v<=1 for v in self.region):
                raise ValueError("material_effect_region_required")
            x,y,w,h=self.region
            if w<=0 or h<=0 or x+w>1 or y+h>1:
                raise ValueError("material_effect_region_invalid")
        elif self.region is not None:
            raise ValueError("material_effect_region_not_applicable")
        return self
