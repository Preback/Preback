import bcrypt
from flask import Flask, jsonify, render_template, request
from bson import ObjectId
from pymongo import MongoClient
import pymongo
from werkzeug.security import check_password_hash, generate_password_hash
from . import schemas
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
client = MongoClient(os.getenv("MONGO_URI")) 
db = client.preback_db


# TODO : 프레젠테이션 삭제 / 댓글 update, del.  구현 필요/ 프레젠테이션에서 슬라이드 데이터 get 필요

user_collection = db.users
db.users.create_index("user_id", unique=True)

presentation_collection = db.presentations
slide_collection = db.slides
comment_collection = db.comments


def checkDupUserId(user_id):
    return user_collection.find_one({
        "user_id" : user_id
    }) is not None

def registerUser(userid, username, password):

    hashed_password = generate_password_hash(password)
    

    user_data = schemas.UserDB(
        user_id=userid,
        user_name=username,
        password=hashed_password,
    )

    # 데이터 삽입 (생성 자체는 auth와 무관)

    result = user_collection.insert_one(user_data.model_dump(by_alias=True))
    

def identifyUser(userid, password):

    user = user_collection.find_one({"user_id" : userid})
    if user is None: return False
    elif check_password_hash(user["password"], password):
        return True
    else: return False


def deletePresentation(oid: str) -> bool:
    presentation_delete_result = presentation_collection.delete_one()

def createPresentation(title, user_oid: str, uploaded_path):

    new_presentation = schemas.PresentationDB(title=title, user_oid=ObjectId(user_oid), uploaded_path=uploaded_path)
    presentation_document = presentation_collection.insert_one(new_presentation.model_dump(by_alias=True))
    oid = presentation_document.inserted_id
     # user에도 배열추가? -> user에 있는 presentation id 배열 빼는게 나을듯
    return str(oid)

def updateConvertingPresentation(presentation_oid):
    update to 

def updateConvertedPresentation(presentation_oid: str, uploaded_imgs: list[str]):


    return True

    return False

items_per_page = 10

presentation_preview_pipeline = lambda page_num : [ # 유저 이름 추가해야됨
        {
            "$sort": {
                "created_at": pymongo.DESCENDING
            }
        },
        {
            "$skip": items_per_page * page_num
        },
        {
            "$limit": items_per_page
        },
        {
            "$set": {
                "first_slide_oid": {
                    "$arrayElemAt": ["$slides_oid", 0]
                }
            }
        },
        {
            "$lookup": {
                "from": "slides", 
                "localField": "slides_oid",  
                "foreignField": "_id",  
                "as": "slides"  
            }
        },
        { # lookup이 slides 배열을 순서에 맞게 못가져오기 때문에 돌아갔다
            "$set" : { # lookup이 실제 도큐먼트를 가져와야 slide 가져오기 가능,
                "first_slide" : {
                    "$arrayElemAt": [
                        {
                            "$filter" : {
                                "input" : "$slides",
                                "as" : "slide",
                                "cond" :  {
                                    "$eq" : [
                                        "$$slide._id",
                                        "$first_slide_oid"
                                    ]
                                }
                            }
                        },
                        0
                    ]
                }
            }
        },
        {
            "$project": {
                "user_oid": 1,
                "title" : 1,
                "created_at" : 1,
                "slide_thumbnail" : "$first_slide.img_src",
                "slide_count" : {
                    "$size" : "$slides_oid"
                },
                "status" : 1,
                "created_at" : 1,
                "comment_count" : {
                    "$sum" : {
                        "$map" : {
                            "input": "$slides",
                            "as" : "slide",
                            "in" : {
                                "$size" : "$$slide.replies"
                            }
                        }
                    }
                }
            }
        }
]



def getAllPresentations(page_num): #page_num은 0부터 시작하는 것으로 가정
                        # 처음 이미지 필요. mongo에서도 index 기반 배열 접근 가능하다. python에서 배열 접근시 전체 배열 항목이 적재되어야 함/ 다만 img src str라서 '큰 오버헤드'는 아닌듯
                        # 제목, thumbnail, 전체 댓글 수, 전체 슬라이드 수, createdAt date
    # chaining,, 호출 순서 관련없음. lazy eval, 

    user_name_pipeline = [{
        "$lookup": {
            "from": "users",
            "localField": "user_oid",
            "foreignField": "_id",
            "as": "user"
        }},
        {
            "$set": {
                "user": {
                    "$arrayElemAt": ["$user", 0]
                }
            }
        },
        {
            "$set" : {
                "user_name": "$user.user_name"
            }
        },
        {
            "$unset" : "user"
        }
    ]
    presentations = presentation_collection.aggregate(presentation_preview_pipeline(page_num) + user_name_pipeline)

    return [{
            **presentation,
            "created_at" : presentation["created_at"].isoformat(),
            "user_oid" : str(presentation["user_oid"]),
            "_id" : str(presentation["_id"])
        }
            for presentation in presentations
        ]

def getUserPresentations(user_oid_str, page_num):
    filter_user_pipeline = [{
        "$match" : {
            "user_oid" : ObjectId(user_oid_str)
        }
    }]

    presentations = presentation_collection.aggregate(filter_user_pipeline + presentation_preview_pipeline(page_num))

    return [{
        **presentation,
        "created_at" : presentation["created_at"].isoformat(),
        "user_oid" : str(presentation["user_oid"]),
        "_id" : str(presentation["_id"])
    }
        for presentation in presentations
    ]

def createComment(user_oid_str, slide_oid_str, text):
    new_comment = schemas.CommentDB(reply=text, user_oid=ObjectId(user_oid_str), slide_oid=ObjectId(slide_oid_str))
    comment_document = comment_collection.insert_one(new_comment.model_dump(by_alias=True))
    oid = comment_document.inserted_id
    
    return True, str(oid)

def getSlidesByPresentation(presentation_oid: str):

    #프레젠테이션 배열에서만 순서 -> 
    slides_pipeline = [
        {
            "$match" : {
                "presentation_oid" : str(presentation_oid)
            }
        },
        {
            "$limit" : 1
        },{
            "$lookup" : {
                "from" : "users",
                "localField" : "user_oid",
                "foreignField" : "_id",
                "as" : "user"
            }
        },
        {
            "$set" : {
                "user_name": "$"
            }
        }
        {
            "$lookup": {
                "from": "slides",
                "localField": "slides_oid",
                "foreignField": "_id",
                "as": "slides"
            }
        },
        {
            "$set" : {
                "slides" : {
                    "$map" : {
                        "input" : "$slides_oid",
                        "as" : "$slide_oid",
                        "in" : {
                            "$arrayElemAt" : [{
                                "$filter": {
                                "input": "$slide_docs",
                                "as": "slide",
                                "cond": { "$eq": ["$$slide._id", "$$slide_oid"] }
                                }
                            }, 0
                            ]
                        }
                    }
                }
            }
        }
        ,{
            "$set" : {
                "slides" : {
                "$map" : {
                "input": "$slides",
                "as" : "slide",
                "in" : {
                    "replies_count" : {
                        "$size" : "$$slide.replies"
                    },
                    "img_src" : "$$slide.img_src",
                    "_id" : "$$slide._id"
                }
            }
            }

        }
        },
        "$project" : {
            "slides" : 1,
            "_id" : 1,

        }
    ]

def getCommentsBySlide(slide_oid):
    comments = comment_collection.find({
        "slide_oid" : ObjectId(slide_oid)
    }).sort({"created_at": pymongo.ASCENDING})

    return [{
        **comment,
        "_id": str(comment["_id"]),
        "user_oid": str(comment["user_oid"]),
        "slide_oid": str(comment["slide_oid"]),
        "created_at": comment["created_at"].isoformat()
    } for comment in comments]



if "__name__" == "__main__":
    repository_local_test_user = "locTestUser"
    repository_local_test_local_oid
    if not checkDupUserId:
        registerUser(repository_local_test_user, )