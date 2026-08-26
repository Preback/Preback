import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import boto3

S3_BUCKET = os.getenv("S3_BUCKET")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-2")
SLIDE_WIDTH = int(os.getenv("SLIDE_WIDTH", 1000))
MAX_PAGES = int(os.getenv("MAX_PAGES", 50))

# 로컬에서만 필요
POPPLER_PATH = os.getenv("POPPLER_PATH", "").strip()

CONVERT_TIMEOUT = 120  # 120초 이상 변환 미완료시 실패


class ConversionError(Exception):
    """PDF 변환 실패. 손상된 파일이거나 PDF가 아닌 경우."""

# PDF 변환용 pdftoppm 실행 파일 경로를 찾기. 현재 EC2에는 있음
def _pdftoppm_path():
    if POPPLER_PATH:
        found = shutil.which("pdftoppm", path=POPPLER_PATH)
        if found:
            return found
    found = shutil.which("pdftoppm")
    if found:
        return found
    raise ConversionError(
        "pdftoppm 을 찾을 수 없습니다. "
        "Ubuntu: sudo apt install poppler-utils / Windows: POPPLER_PATH 환경변수 설정"
    )

# PDF2PNG, 페이지 순서대로 경로 리스트 반환
def convert_pdf_to_images(pdf_path, out_dir, width=SLIDE_WIDTH, max_pages=MAX_PAGES):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        _pdftoppm_path(),
        "-png",
        "-scale-to-x", str(width),
        "-scale-to-y", "-1",        # 비율 유지
        "-l", str(max_pages),       # 마지막 페이지 제한
        str(pdf_path),
        str(out_dir / "slide"),     # 접두사. slide-01.png 형태로 생성된다.
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=CONVERT_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise ConversionError("변환 시간 초과. 파일이 너무 크거나 손상되었습니다.")
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or b"").decode("utf-8", "replace").strip()
        raise ConversionError(f"PDF 변환 실패: {detail or '알 수 없는 오류'}")

    # 파일명 자릿수 정렬 
    images = sorted(out_dir.glob("slide-*.png"))
    if not images:
        raise ConversionError("변환 결과가 없습니다. 유효한 PDF가 아닐 수 있습니다.")
    return images

# S3 업로드
def upload_slides_to_s3(image_paths, presentation_id):
    s3 = boto3.client("s3") 
    urls = []

    for page, path in enumerate(image_paths, start=1):
        key = f"{presentation_id}/slide-{page:03d}.png"

        with open(path, "rb") as f:
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=f,
                ContentType="image/png",
            )

        urls.append(f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}")

    return urls

# 변환 -> 업로드 -> 임시파일 정리. 슬라이드 URL 리스트 반환
def process_pdf(pdf_path, presentation_id):
    tmp_dir = tempfile.mkdtemp(prefix="preback-")
    try:
        images = convert_pdf_to_images(pdf_path, tmp_dir)
        return upload_slides_to_s3(images, presentation_id)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True) # 실패시 임시파일삭제 
