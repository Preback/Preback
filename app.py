import os
import uuid
from datetime import date, datetime, timedelta
from pymongo import MongoClient

from flask import Flask, abort, redirect, render_template, request, url_for, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
client = MongoClient('localhost', 27017)
db = client.dbpreback

# TODO: config.py로 옮기기
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
    for p in DUMMY_MY_PRESENTATIONS + DUMMY_ALL_PRESENTATIONS:
        if p['id'] == presentation_id:
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


@app.route('/')
def index():
    return redirect(url_for('getMyPresentations'))

@app.route('/upload')
def getUpload():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def postUpload():
    file = request.files.get('file')

    if file is None or not file.filename:
        return render_template('upload.html', error='파일을 선택해주세요.'), 400

    if os.path.splitext(file.filename)[1].lower() not in ALLOWED_EXTENSIONS:
        return render_template('upload.html', error='.pdf 파일만 업로드할 수 있습니다.'), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    presentation_id = uuid.uuid4().hex
    file.save(os.path.join(UPLOAD_FOLDER, secure_filename(presentation_id)))

    title = request.form.get('title', '').strip()
    user_oid = session.get('user_oid')
    if not user_oid:
        return redirect(url_for(getLogin))
    db.presentations.insert_one({
        'title' : title,
        'user_oid' : user_oid,
    })

    # TODO: services/converter.py로 슬라이드 이미지 변환 + db/repository.py에 메타데이터 저장
    # TODO: 저장 후 상세 뷰어로 리다이렉트 ("첨부하고 열기")
    return redirect(url_for('getMyPresentations'))

@app.route('/login')
def getLogin():
    return render_template('login.html')

@app.route('/signup')
def getSignUp():
    return render_template('signup.html')

@app.route('/logout')
def getLogout():
    # TODO: 세션 구현 후 session.clear() 추가
    return redirect(url_for('getLogin'))

@app.route('/presentations/my')
def getMyPresentations():
    return render_template('mypresen.html', presentations=DUMMY_MY_PRESENTATIONS, active='my')

@app.route('/presentations/all')
def getAllPresentations():
    return render_template('all_presentations.html', presentations=DUMMY_ALL_PRESENTATIONS, active='all')

@app.route('/presentations/<int:presentation_id>')
def getPresentation(presentation_id):
    presentation = find_presentation(presentation_id)
    if presentation is None:
        abort(404)

    slide_count = presentation['slide_count']
    current_slide = min(max(request.args.get('slide', default=1, type=int), 1), slide_count)

    comments = sorted(
        (c for c in DUMMY_COMMENTS
         if c['presentation_id'] == presentation_id and c['slide'] == current_slide),
        key=lambda c: c['created_at'],
    )

    comment_counts = {}
    for c in DUMMY_COMMENTS:
        if c['presentation_id'] == presentation_id:
            comment_counts[c['slide']] = comment_counts.get(c['slide'], 0) + 1

    return render_template(
        'viewer.html',
        presentation=presentation,
        slides=range(1, slide_count + 1),
        current_slide=current_slide,
        comments=comments,
        comment_counts=comment_counts,
    )

@app.route('/presentations/<int:presentation_id>/comments', methods=['POST'])
def postComment(presentation_id):
    presentation = find_presentation(presentation_id)
    if presentation is None:
        abort(404)

    slide = min(max(request.form.get('slide', default=1, type=int), 1), presentation['slide_count'])
    body = (request.form.get('body') or '').strip()

    if body:
        # TODO: db/repository.py 연동 후 교체. 작성자는 로그인 세션에서 가져온다.
        DUMMY_COMMENTS.append({
            'presentation_id': presentation_id,
            'slide': slide,
            'author': '사용자 이름',
            'body': body,
            'created_at': datetime.now(),
        })

    return redirect(url_for('getPresentation', presentation_id=presentation_id, slide=slide))

if __name__ == '__main__':
   app.run('0.0.0.0', port=5000, debug=True)
