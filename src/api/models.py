from pydantic import BaseModel
from typing import Optional


class CollectJobRequest(BaseModel):
    collection_id: str
    collection_name: str
    skip_download: bool = False


class AnalyzeJobRequest(BaseModel):
    collection_name: str


class InstagramLoginRequest(BaseModel):
    username: str
    password: str


class Instagram2FARequest(BaseModel):
    token: str
    code: str


class SaveKeysRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    google_places_api: Optional[str] = None
