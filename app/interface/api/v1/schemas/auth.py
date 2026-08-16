from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: str | None = None
