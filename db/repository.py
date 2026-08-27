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

    return result.inserted_id
    

def identifyUser(userid, password):

    user = user_collection.find_one({"user_id" : userid})
    if user is None: return False, "", ""
    elif check_password_hash(user["password"], password):
        return True, str(user["_id"]), str(user["user_name"])
    else: return False, "", ""


def deletePresentation(oid: str) -> bool:
    presentation_delete_result = presentation_collection.delete_one()
    #TODO : 연결된 이미지도 모두 삭제해야 함

def createPresentation(title, user_oid: str, uploaded_path):

    new_presentation = schemas.PresentationDB(title=title, user_oid=ObjectId(user_oid), uploaded_path=uploaded_path)
    presentation_document = presentation_collection.insert_one(new_presentation.model_dump(by_alias=True))
    oid = presentation_document.inserted_id
     # user에도 배열추가? -> user에 있는 presentation id 배열 빼는게 나을듯
    return str(oid)

def updatePresentationStatus(presentation_oid: str, status: schemas.PresentationStatus):
    result = presentation_collection.update_one(
        {"_id": ObjectId(presentation_oid)},
        {"$set": {"status": status}}
    )
    return result.modified_count == 1

def updateConvertedPresentation(presentation_oid: str, uploaded_imgs: list[str]):
    if not uploaded_imgs:
        return False

    pres_oid = ObjectId(presentation_oid)

    # process_pdf 가 돌려준 리스트=페이지 순서, enumerate로 idx 기록
    docs = [
        schemas.SlideDB(
            presentation_oid=pres_oid,
            idx=i,
            img_src=url,
        ).model_dump(by_alias=True)
        for i, url in enumerate(uploaded_imgs)
    ]

    slide_collection.insert_many(docs)

    result = presentation_collection.update_one(
        {"_id": pres_oid},
        {"$set": {
            "status": schemas.PresentationStatus.CONVERTED.value,
        }},
    )
    return result.matched_count == 1


items_per_page = 10

presentation_preview_pipeline = lambda page_num : [    #page_num은 0부터 시작하는 것으로 가정
                        # 제목, thumbnail, 전체 댓글 수, 전체 슬라이드 수, createdAt date
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
            "$lookup": {
                "from": "slides",
                "localField": "_id",
                "foreignField": "presentation_oid",
                "as": "slides"
            }
        },
        {
            "$lookup": {
                "from": "comments",
                "localField": "slides._id",
                "foreignField": "slide_oid",
                "as": "comments"
            }
        },
        { # lookup이 slides 배열을 순서에 맞게 못가져오기 때문에 돌아갔다 ->  : idx=  0인 것 필터하면 되므로 더 단순해짐, 수정 하는게 나아 보인다 -> done
            "$set" : { # lookup이 실제 도큐먼트를 가져와야 slide 가져오기 가능,
                "first_slide" : {
                        "$arrayElemAt": [
                            {
                                "$filter": {
                                    "input": "$slides",
                                    "as": "slide",
                                    "cond": { "$eq": ["$$slide.idx", 0] }
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
                    "$size" : "$slides"
                },
                "status" : 1,
                "comment_count" : {"$size" : "$comments"}
            }
        }
]

def getPresentationPageCounts(user_oid : str = None):
    if user_oid is None:
        count = presentation_collection.count_documents({})
    else : count = presentation_collection.count_documents({"user_oid": ObjectId(user_oid)})

    return count // items_per_page + (0 if count % items_per_page == 0 else 1)



def getPresentations(page_num): 

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
            "created_at" : presentation["created_at"],
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
        "created_at" : presentation["created_at"],
        "user_oid" : str(presentation["user_oid"]),
        "_id" : str(presentation["_id"])
    }
        for presentation in presentations
    ]


def createComment(user_oid_str, slide_oid_str, text):
    new_comment = schemas.CommentDB(reply=text, user_oid=ObjectId(user_oid_str), slide_oid=ObjectId(slide_oid_str))
    comment_document = comment_collection.insert_one(new_comment.model_dump(by_alias=True))
    
    return True

def getSlidesByPresentation(presentation_oid: str):
    #일단 pipeline 수행됨. TODO 실제 의미가 제대로 나오는지 실제 유저 데이터로 테스트 필요
    presentation = presentation_collection.find_one({"_id" : ObjectId(presentation_oid)})

    slides_pipeline = [
        {
            "$match" : {
                "presentation_oid" : ObjectId(presentation_oid) 
            }
        },
        {
            "$sort": {
                "idx": pymongo.ASCENDING
            }
        },
            {
                    "$lookup": {
                        "from": "comments",
                        "localField": "_id",
                        "foreignField": "slide_oid",
                        "as": "comments"
                    }
            }
        ,   {
           "$addFields" : {
               "comments_count" : {
                   "$size" : "$comments"
               }
           }
        },
        {
            "$project" : {
                "_id" : 1,
                "presentation_oid" : 1,
                "img_src" : 1,
                "idx" : 1,
                "comments_count" : 1
            }
        }
    ]
    
    slides = slide_collection.aggregate(slides_pipeline)
    res = {
        "presentation_title" : presentation["title"],
        "presentation_created_at" : presentation["created_at"],
        "presentation_status" : presentation["status"],
        "slides" : [
            {
                **slide,
                "presentation_oid" : str(slide["presentation_oid"]),
                "_id" : str(slide["_id"])
            } for slide in slides
        ]
    }
    return res

# def getOneSlide(slide_oid):  -> 보류, CSR 전체화면 고려중
#     res = slide_collection.find_one({"_id" : ObjectId(slide_oid)})
#     return {

#     }


def getCommentsBySlide(slide_oid):
    comments = comment_collection.aggregate([
        {
            "$match": {
                "slide_oid": ObjectId(slide_oid)
            }
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "user_oid",
                "foreignField": "_id",
                "as": "user"
            }
        },
        {
            "$set": {
                "user_name": {
                    "$arrayElemAt": ["$user.user_name", 0]
                }
            }
        },
        {
            "$unset": "user"
        },
        {
            "$sort": {
                "created_at": pymongo.ASCENDING
            }
        }
    ])

    return [{
        **comment,
        "_id": str(comment["_id"]),
        "user_oid": str(comment["user_oid"]),
        "slide_oid": str(comment["slide_oid"]),
        "created_at": comment["created_at"].isoformat()
    } for comment in comments]

def updateComment(comment_oid: str, new_text):
    result = comment_collection.update_one({
        "_id" : ObjectId(comment_oid)}, {
        "$set" : {
            "reply" : new_text
        }
    })

    return True if result.matched_count == 1 else False

def deleteComment(comment_oid: str):
    result = comment_collection.delete_one({
        "_id" : ObjectId(comment_oid)
    })

    return True if result.deleted_count == 1 else False

if __name__ == "__main__":
    repository_local_test_user = "locTestUser"
    repository_local_test_password = "password"

    if not checkDupUserId(repository_local_test_user):
        user_oid = registerUser(repository_local_test_user, "userName", repository_local_test_password)
    else : user_oid = str(user_collection.find_one({
        "user_id" : repository_local_test_user
    })["_id"])

    print(identifyUser(repository_local_test_user, repository_local_test_password+" "))
        
    presentation_oid = createPresentation("title", str(user_oid), "uploaded_path")
    updateConvertedPresentation(
        presentation_oid,
        [
            "uploaded_path/slide-1.png",
            "uploaded_path/slide-2.png",
            "uploaded_path/slide-3.png",
        ],
    )
    print(getPresentationPageCounts())
    print(getPresentations(0))
    print(getUserPresentations("507f191e810c19729de860ea", 0)) # 틀린
    print(getUserPresentations(user_oid, 0))
    print("\n")
    
    sample_slide_oid = slide_collection.find_one({
        "presentation_oid" : ObjectId(presentation_oid),
        "idx" : 0
    })["_id"]
    createComment(user_oid,sample_slide_oid, "someNewComment")
    selected_comment_oid = createComment(user_oid, sample_slide_oid, "newComment to be deleted")
    print(getUserPresentations(user_oid, 0))
    print()
    print(getSlidesByPresentation(presentation_oid))
    print()
    print(getCommentsBySlide(str(sample_slide_oid)))
    print(deleteComment(selected_comment_oid))
    
