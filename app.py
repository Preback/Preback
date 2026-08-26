import os
import uuid
import pymongo
from db.repository import createComment, createPresentation, getCommentsBySlide, getSlidesByPresentation, identifyUser, registerUser, getPresentations, getPresentationPageCounts, getUserPresentations, updateComment
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect, render_template, request, url_for, session
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
# 세션(로그인 유지)에 필수. 없으면 session 사용 시 RuntimeError.
app.secret_key = os.getenv('SECRET_KEY')

# TODO: config.py로 옮기기
# 로그인 없이 접근 가능한 엔드포인트. 함수명과 정확히 일치해야 한다.
PUBLIC_ENDPOINTS = {'getLogin', 'postLogin', 'getSignUp', 'postSignUp', 'static'}
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'.pdf'}
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

# TODO: db/repository.py 연동 전까지 쓰는 임시 더미 데이터. DB 붙으면 제거한다.
DUMMY_MY_PRESENTATIONS = [
    {'id': 1, 'title': '2026 사업계획 발표',   'thumbnail': None, 'slide_count': 24, 'comment_count': 12, 'updated_at': date(2026, 8, 20)},
    {'id': 2, 'title': '제품 디자인 리뷰',      'thumbnail': None, 'slide_count': 18, 'comment_count': 5,  'updated_at': date(2026, 8, 18)},
    {'id': 3, 'title': '마케팅 캠페인 제안서',  'thumbnail': None, 'slide_count': 32, 'comment_count': 27, 'updated_at': date(2026, 8, 15)},
    {'id': 4, 'title': '분기 실적 보고',        'thumbnail': None, 'slide_count': 14, 'comment_count': 0,  'updated_at': date(2026, 8, 10)},
    {'id': 5, 'title': '신규 기능 킥오프',      'thumbnail': None, 'slide_count': 9,  'comment_count': 3,  'updated_at': date(2026, 8, 5)},
]

DUMMY_ALL_PRESENTATIONS = [
    {'id': 1,  'title': '2026 사업계획 발표',   'author': '김민준', 'thumbnail': None, 'slide_count': 24, 'comment_count': 12, 'updated_at': date(2026, 8, 20)},
    {'id': 6,  'title': '브랜드 리뉴얼 제안',   'author': '이서연', 'thumbnail': None, 'slide_count': 20, 'comment_count': 8,  'updated_at': date(2026, 8, 19)},
    {'id': 2,  'title': '제품 디자인 리뷰',     'author': '박도윤', 'thumbnail': None, 'slide_count': 18, 'comment_count': 5,  'updated_at': date(2026, 8, 18)},
    {'id': 7,  'title': '채용 온보딩 가이드',   'author': '최지우', 'thumbnail': None, 'slide_count': 11, 'comment_count': 2,  'updated_at': date(2026, 8, 17)},
    {'id': 3,  'title': '마케팅 캠페인 제안서', 'author': '정하은', 'thumbnail': None, 'slide_count': 32, 'comment_count': 27, 'updated_at': date(2026, 8, 15)},
    {'id': 8,  'title': '데이터 인프라 로드맵', 'author': '강시우', 'thumbnail': None, 'slide_count': 15, 'comment_count': 9,  'updated_at': date(2026, 8, 12)},
    {'id': 4,  'title': '분기 실적 보고',       'author': '윤예은', 'thumbnail': None, 'slide_count': 14, 'comment_count': 0,  'updated_at': date(2026, 8, 10)},
    {'id': 5,  'title': '신규 기능 킥오프',     'author': '임준호', 'thumbnail': None, 'slide_count': 9,  'comment_count': 3,  'updated_at': date(2026, 8, 5)},
]

# 서버가 살아있는 동안만 유지되는 임시 저장소. 재시작하면 초기화된다.
DUMMY_COMMENTS = [
    {'presentation_id': 1, 'slide': 2, 'author': '이서연', 'body': '이 장표 제목이 다음 장이랑 겹칩니다.',        'created_at': datetime.now() - timedelta(hours=3)},
    {'presentation_id': 1, 'slide': 2, 'author': '최지우', 'body': '폰트 크기를 조금 키우면 좋겠어요.',            'created_at': datetime.now() - timedelta(hours=2)},
    {'presentation_id': 1, 'slide': 5, 'author': '박지훈', 'body': '여기 수치 데이터 출처를 각주로 넣어주세요.',   'created_at': datetime.now() - timedelta(minutes=40)},
    {'presentation_id': 1, 'slide': 7, 'author': '정하은', 'body': '그래프 축 단위가 빠진 것 같습니다.',           'created_at': datetime.now() - timedelta(minutes=15)},
]


def find_presentation(presentation_id):
    # 라우트 파라미터는 문자열인데 더미 데이터의 id는 정수라 문자열로 맞춰 비교한다.
    # TODO: DB 연동 시 ObjectId 조회로 교체
    for p in DUMMY_MY_PRESENTATIONS + DUMMY_ALL_PRESENTATIONS:
        if str(p['id']) == str(presentation_id):
            return p
    return None


@app.template_filter('timeago')
def timeago(value):
    seconds = int((datetime.now() - value).total_seconds())
    if seconds < 60:
        return '방금 전'
    if seconds < 3600:
        return '%d분 전' % (seconds // 60)
    if seconds < 86400:
        return '%d시간 전' % (seconds // 3600)
    return '%d일 전' % (seconds // 86400)

@app.before_request
def require_login():
    if request.endpoint in PUBLIC_ENDPOINTS:
        return
    if request.endpoint is None:
        return
    if 'user_oid' not in session:
        return redirect(url_for('getLogin'))    # 비로그인시 로그인 페이지로 리다이렉트

@app.route('/')
def index():
    return redirect(url_for('getMyPresentations'))

@app.route('/upload')
def getUpload():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def postUpload():
    user_oid = session.get('user_oid')
    if not user_oid:
        return redirect(url_for('getLogin'))
    title = request.form.get('title', '').strip()
    if not title:
        return render_template('upload.html', error='제목을 입력해주세요.'), 400

    file = request.files.get('file')
    if file is None or not file.filename:
        return render_template('upload.html', error='파일을 선택해주세요.'), 400

    if os.path.splitext(file.filename)[1].lower() not in ALLOWED_EXTENSIONS:
        return render_template('upload.html', error='.pdf 파일만 업로드할 수 있습니다.'), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    file_id = uuid.uuid4().hex + '.pdf'
    save_path = os.path.join(UPLOAD_FOLDER, secure_filename(file_id))
    file.save(save_path)

    try:
        presentation_id = createPresentation(title, user_oid, save_path)
    except Exception:
        os.remove(save_path)
        app.logger.exception('presentation insert 실패')
        return render_template('upload.html', error='업로드 중 오류가 발생했습니다. 다시 시도해주세요.'), 500

    # TODO: services/converter.py로 슬라이드 이미지 변환 + db/repository.py에 메타데이터 저장
    # TODO: 저장 후 상세 뷰어로 리다이렉트 ("첨부하고 열기")
    return redirect(url_for('getPresentation', presentation_id=presentation_id))

@app.route('/login')
def getLogin():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def postLogin():
    user_id = request.form.get('user_id')
    user_pw = request.form.get('user_pw')
    isSuccess, user_oid = identifyUser(user_id, user_pw)
    if not isSuccess:
        return render_template('login.html', error='아이디 또는 비밀번호가 올바르지 않습니다.'), 401
    session['user_oid'] = user_oid
    return redirect(url_for('getMyPresentations'))

@app.route('/signup')
def getSignUp():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def postSignUp():
    user_name = request.form.get('user_name', '').strip()
    user_id = request.form.get('user_id', '').strip()
    user_pw = request.form.get('user_pw')
    user_pw_check = request.form.get('user_pw_check')
    if not user_name or not user_id or not user_pw or not user_pw_check:
        return render_template('signup.html', error='입력하지 않은 정보가 있습니다.'), 400
    if user_pw!=user_pw_check:
        return render_template('signup.html', error='비밀번호가 일치하지 않습니다.'), 400

    try:
        registerUser(user_id, user_name, user_pw)
    except pymongo.errors.DuplicateKeyError:
        return render_template('signup.html', error='중복된 아이디입니다.'), 409
    except pymongo.errors.PyMongoError:
        return render_template('signup.html', error='회원가입에 실패했습니다.'), 500
    
    return redirect(url_for('getLogin'))

@app.route('/logout')
def getLogout():
    session.clear()
    return redirect(url_for('getLogin'))

@app.route('/presentations/my')
def getMyPresentations():
    page = request.args.get('page', type=int)
    if page is None or page < 0:
        page = 1
    total_pages = getPresentationPageCounts(session.get('user_oid', '').strip())
    user_oid = session['user_oid']
    presentations = getUserPresentations(user_oid, page)
    return render_template('mypresen.html', total_pages= total_pages, page=page, presentations=presentations, active='all')

@app.route('/presentations/all')
def getAllPresentations():
    page = request.args.get('page', type=int)
    if page is None or page < 0:
        page = 1
    total_pages = getPresentationPageCounts()
    presentations = getPresentations(page-1)
    return render_template('all_presentations.html', total_pages= total_pages, page=page, presentations=presentations, active='all')

@app.route('/presentations/<presentation_id>') #  댓글만 ajax로, 한 프레젠테이션은 새로고침 없는
def getPresentation(presentation_id): # 
    if presentation_id == "debug":
        dummy_slides = [
            {
                "_id": "slide_001",
                "presentation_oid": "presentation_debug",
                "img_src": "/static/img/sample1.jpg",
                "idx": 0,
                "comments_count": 3
            },
            {
                "_id": "slide_002",
                "presentation_oid": "presentation_debug",
                "img_src": "/static/img/sample2.jpg",
                "idx": 1,
                "comments_count": 0
            },
            {
                "_id": "slide_003",
                "presentation_oid": "presentation_debug",
                "img_src": "/static/img/sample3.jpg",
                "idx": 2,
                "comments_count": 5
            }
        ]

        return render_template(
            "viewer.html",
            presentation_title="디버그 프레젠테이션",
            presentation_status="converted",
            slides=dummy_slides
        )
    
    try: presentation = getSlidesByPresentation(presentation_id)
    except: 
        abort(404)

    return render_template(
        'viewer.html',
        presentation_title = presentation["presentation_title"],
        presentation_status = presentation["presentation_status"],
        slides= presentation["slides"]
    )

    # slides =[ {
    #     "_id" : string,
    #     "presentation_oid" : string,
    #     "img_src" : string,
    #     "idx" : int,
    #     "comments_count" : int
    # } ]

@app.route('/api/slide/<slide_oid>/comments', methods=['GET'])
def getComments(slide_oid):
    comments = getCommentsBySlide(slide_oid) # created-at ascending 순서대로 배열 정렬됨
    # comments = [
    #     {
    #         _id : str 
    #         reply : str 
    #         slide_oid : str,
    #         created_at : iso formatted str, 프론트에서 파싱하기
    #     }
    # ]

    return jsonify(
        comments
    )



#comment crud는 성공 결과만 반환, 최신 업데이트는 클라이언트가 직접 요청 필요

@app.route('/api/slide/<slide_oid>/comments', methods=['POST'])
def postComment(slide_oid):
    user_oid = session['user_oid']
    new_text = request.form.get('text')

    if createComment(user_oid, slide_oid, new_text) is True:
        return jsonify({
            'result' : "success"
        })
    else: abort(500)



@app.route('/api/comments/<comment_oid>', methods=['PATCH']) # updated_at이 없음. created_at은 최초 생성으로만 유지하는 구현
def patchComment(comment_oid):
    new_text = request.form.get('text')

    if updateComment(comment_oid, new_text) is True:
        return jsonify({
            'result' : "success"
        })
    else: abort(500)

@app.route('/api/comments/<comment_oid>', methods=['DELETE'])
def deleteComment(comment_oid):

    if deleteComment(comment_oid) is True:
        return jsonify({
            "result" : "success"
        })
    else: abort(500)

if __name__ == '__main__':
   app.run('0.0.0.0', port=5000, debug=True)
