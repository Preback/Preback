import bcrypt
from flask import Flask, jsonify, render_template, request
from bson import ObjectId
from pymongo import MongoClient

from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
client = MongoClient(os.getenv("MONGO_URI"), int(os.getenv("MONGO_PORT")))  # mongoDB는 27017 포트로 돌아갑니다.
db = client.preback_db
user_collection = db.users
presentations_collection = db.presentations

def registerUser(userid, username, password):
    # 비밀번호 암호화 (보안 필수)
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    # DB 입장에서는 그저 하나의 '문서(Document)' 데이터일 뿐입니다
    user_data = User()

    # 데이터 삽입 (생성 자체는 auth와 무관)
    result = users_collection.insert_one(user_data)
    print(f"유저 생성 완료! ID: {result.inserted_id}")
def getAllPresentations():



def getUserPresentations(user_oid_str):
    user_oid = ObjectId(user_oid_str)
