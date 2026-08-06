from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    """Immutable value object passed between pipeline stages."""

    model_config = ConfigDict(frozen=True)
