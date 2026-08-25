import bcrypt
from flask import Flask, jsonify, render_template, request
from bson import ObjectId
from pymongo import MongoClient
import pymongo
import schemas
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
client = MongoClient(os.getenv("MONGO_URI"), int(os.getenv("MONGO_PORT")))  # mongoDB는 27017 포트로 돌아갑니다.
db = client.preback_db


user_collection = db.users
db.users.create_index("user_id", unique=True)

presentation_collection = db.presentations
slide_collection = db.slides
comment_collection = db.comments



def registerUser(userid, username, password):

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


    user_data = schemas.UserDB(
        user_id=userid,
        user_name=username,
        password=hashed_password,
    )

    # 데이터 삽입 (생성 자체는 auth와 무관)
    result = user_collection.insert_one(user_data.model_dump())
    print(f"유저 생성 완료! ID: {result.inserted_id}")

items_per_page = 10

def getAllPresentations(page_num): # 처음 이미지 필요. mongo에서도 index 기반 배열 접근 가능하다. python에서 배열 접근시 전체 배열 항목이 적재되어야 함/ 다만 img src str라서 '큰 오버헤드'는 아닌듯

    # chaining,, 호출 순서 관련없음. lazy eval, 
    presentation_fragments = (
        presentation_collection.find({}).sort("createdAt", pymongo.DESCENDING).
        skip()
    )

    

    return 




def getUserPresentations(user_oid_str):
    user_oid = ObjectId(user_oid_str)
