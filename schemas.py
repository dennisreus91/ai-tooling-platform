from typing import List, Union

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class RunPocFlowRequest(BaseModel):
    """
    Raw intake payload received from Typebot or another frontend.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., min_length=1)
    target_label: str = Field(..., min_length=1)
    required_measures: Union[str, List[str], None] = None
    file_url: HttpUrl


class Constraints(BaseModel):
    """
    Normalized constraints used internally by later pipeline stages.
    """

    model_config = ConfigDict(extra="forbid")

    target_label: str
    required_measures: List[str]
