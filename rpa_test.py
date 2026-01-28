"""
S3 ↔ RPA Input/Completed 동기화 스크립트
- S3 input 폴더 → RPA Input 공유폴더 다운로드
- RPA Completed 공유폴더 → S3 result 업로드
- state.json으로 중복 방지 및 상태 유지
"""

import boto3
import os
import time
import json
import logging
from datetime import datetime

# 기본 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("sync.log", encoding="utf-8")]
)
logger = logging.getLogger(__name__)

# 설정 로딩
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

aws_cfg = config["aws"]
bucket = aws_cfg["bucket"]
path_tpl = config["path_templates"]

# S3 클라이언트 생성
s3 = boto3.client(
    "s3",
    aws_access_key_id=aws_cfg["aws_access_key_id"],
    aws_secret_access_key=aws_cfg["aws_secret_access_key"],
    region_name=aws_cfg["region_name"]
)

# 상태 관리 (state.json에 저장/로드)
STATE_FILE = "state.json"
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    if "baseline_time" not in state:  # 구버전 호환
        state["baseline_time"] = datetime.now().isoformat()
else:
    state = {"downloaded": [], "uploaded": [], "input_times": {}, "baseline_time": datetime.now().isoformat()}

downloaded_from_s3 = set(state["downloaded"])
uploaded_completed = set(state["uploaded"])
input_uploaded_times = {k: datetime.fromisoformat(v) for k, v in state["input_times"].items()}
baseline_time = datetime.fromisoformat(state["baseline_time"])
watching_folders = {}

def save_state():
    """현재 상태를 state.json에 저장 (중복 방지 및 실행 지속성 유지)."""
    state["downloaded"] = list(downloaded_from_s3)
    state["uploaded"] = list(uploaded_completed)
    state["input_times"] = {k: v.isoformat() for k, v in input_uploaded_times.items()}
    state["baseline_time"] = baseline_time.isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

# 매핑 생성
input_mappings = {path_tpl["s3_input"].format(**hq): path_tpl["local_input"].format(**hq) for hq in config["hq_versions"]}
completed_mappings = {path_tpl["local_completed"].format(**hq): path_tpl["s3_result"].format(**hq) for hq in config["hq_versions"]}

def sync_input_from_s3():
    """S3 → RPA Input 동기화. 새로운 파일만 다운로드."""
    for s3_prefix, local_folder in input_mappings.items():
        try:
            continuation = None
            while True:
                kwargs = {"Bucket": bucket, "Prefix": s3_prefix}
                if continuation:
                    kwargs["ContinuationToken"] = continuation
                response = s3.list_objects_v2(**kwargs)

                for obj in response.get("Contents", []):
                    filename = os.path.basename(obj["Key"])
                    if not filename:
                        continue
                    local_path = os.path.join(local_folder, filename)

                    if filename not in downloaded_from_s3:
                        logger.info(f"S3 Input → RPA: {obj['Key']} → {local_path}")
                        os.makedirs(local_folder, exist_ok=True)
                        try:
                            s3.download_file(bucket, obj["Key"], local_path)
                            downloaded_from_s3.add(filename)
                            input_uploaded_times[filename] = datetime.now()
                            save_state()
                        except Exception as e:
                            logger.error(f"다운로드 실패: {local_path}, {e}")

                # S3는 1000개 단위 페이징 → Truncated 시 다음 페이지 요청
                if response.get("IsTruncated"):
                    continuation = response["NextContinuationToken"]
                else:
                    break
        except Exception as e:
            logger.error(f"Input 동기화 오류 ({s3_prefix}): {e}")

def sync_completed_to_s3():
    """Completed → S3 result 동기화. baseline_time 이후, Input 업로드 이후 파일만 업로드."""
    for local_root, s3_prefix in completed_mappings.items():
        year_folder = os.path.join(local_root, str(datetime.now().year))
        if not os.path.exists(year_folder):
            continue

        for day_version in os.listdir(year_folder):
            dv_path = os.path.join(year_folder, day_version)
            if os.path.isdir(dv_path) and dv_path not in watching_folders:
                watching_folders[dv_path] = (datetime.now(), s3_prefix)

        for dv_path, (_, mapped_prefix) in list(watching_folders.items()):
            if not os.path.exists(dv_path):
                continue
            for filename in os.listdir(dv_path):
                if not filename.endswith("_전처리.xlsx"):
                    continue
                file_path = os.path.join(dv_path, filename)
                if file_path in uploaded_completed:
                    continue

                try:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_mtime <= baseline_time:
                        continue
                    if input_uploaded_times:
                        last_input_time = max(input_uploaded_times.values())
                        if file_mtime <= last_input_time:
                            continue

                    s3_key = f"{mapped_prefix}{filename}"
                    logger.info(f"Completed → S3 Result: {file_path} → s3://{bucket}/{s3_key}")
                    s3.upload_file(file_path, bucket, s3_key)
                    uploaded_completed.add(file_path)
                    save_state()
                except Exception as e:
                    logger.error(f"Completed 업로드 실패: {file_path}, {e}")

def main():
    """60초마다 Input/Completed 동기화 실행."""
    logger.info("S3 ↔ RPA Input/Completed 동기화 시작...")
    while True:
        try:
            sync_input_from_s3()
            sync_completed_to_s3()
        except Exception as e:
            logger.error(f"메인 루프 오류: {e}")
        time.sleep(60)

if __name__ == "__main__":
    main()
