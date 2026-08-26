from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from bson import ObjectId
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

class PresentationStatus(str, Enum): # 정상 업로드 이후여야 
    WAITING = "waiting"
    CONVERTING = "converting"
    CONVERTED = "converted"
    FAILED = "failed"

class UserDB(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    user_name: str
    user_id: str
    # presentations_oid: list[ObjectId] = Field(default_factory=list)  -> 제거, presentation에서만 찾기
    password: str

class PresentationDB(BaseModel): 
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")

    title: str
    user_oid: ObjectId
    slides_oid: list[ObjectId] = Field(default_factory=list) # 순서 때문에 배열은 필요
    status : PresentationStatus = PresentationStatus.WAITING
    # 파일 경로
    uploaded_path : str
    created_at: datetime = Field(
    default_factory=lambda: datetime.now(ZoneInfo("Asia/Seoul"))
)

class SlideDB(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    presentation_oid: ObjectId
    img_src: str
    replies: list[ObjectId]
    idx: int


class CommentDB(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    reply: str
    user_oid : ObjectId
    slide_oid: ObjectId
    created_at: datetime = Field(
    default_factory=lambda: datetime.now(ZoneInfo("Asia/Seoul"))
   
)

