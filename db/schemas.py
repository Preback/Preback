from bson import ObjectId
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

class PresentationStatus(str, Enum): # 정상 업로드 이후여야 
    WAITING = "waiting"
    CONVERTING = "converting"
    CONVERTED = "converted"


class UserDB(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: ObjectId = Field(alias="_id")
    user_name: str
    user_id: str
    presentations_oid: list[ObjectId]

class PresentationDB(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: ObjectId = Field(alias="_id")
    
    user_oid = ObjectId
    slides_oid: list[ObjectId]
    status : PresentationStatus = PresentationStatus.WAITING

class SlideDB(BaseModel):
    img_src: str
    replies: list[str]