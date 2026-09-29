"""
무드핏(MoodFit) 코디 추천 서버 함수

- Vercel Serverless Function(Python) 방식이에요.
  api/recommend.py 파일은 자동으로 /api/recommend 주소가 돼요.
- 요청(POST):  { "gender": "여성", "mood": "신나요" }
- 응답(JSON):  { "top": "...", "bottom": "...", "shoes": "...", "reason": "..." }
- AI는 Google Gemini API(google-genai 패키지의 Interactions API)를 사용해요.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from http.server import BaseHTTPRequestHandler

from google import genai
from google.genai import types


# ===== 1. 설정 값 =====

# 모델 이름: 환경 변수 GEMINI_MODEL이 있으면 그 값을, 없으면 기본값을 써요.
# 기본값은 Google 공식 문서 기준 가장 빠르고 저렴한 모델이에요.
DEFAULT_MODEL = "gemini-3.5-flash-lite"

# 허용하는 성별과 기분 목록 (이 목록에 없는 값은 거절해요)
ALLOWED_GENDERS = ["여성", "남성", "상관없음"]
ALLOWED_MOODS = ["신나요", "평온해요", "우울해요", "피곤해요", "자신감 있어요"]

# AI 응답에 꼭 있어야 하는 키
REQUIRED_KEYS = ["top", "bottom", "shoes", "reason"]

# 시간 제한 (화면 쪽은 15초가 지나면 포기하므로, 서버는 그보다 먼저 끝내요)
HTTP_TIMEOUT_MS = 10_000   # Gemini 서버와 통신할 때 기다리는 최대 시간 (밀리초)
TOTAL_TIMEOUT_SEC = 12     # AI 호출 전체를 기다리는 최대 시간 (초)

# 요청 본문 최대 크기 (너무 큰 요청은 받지 않아요)
MAX_BODY_BYTES = 1024

# AI가 이 모양(JSON 스키마)대로만 답하도록 알려줘요
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "top": {"type": "string", "description": "추천 상의 (한국어, 흔한 옷 이름)"},
        "bottom": {"type": "string", "description": "추천 하의 (한국어, 흔한 옷 이름)"},
        "shoes": {"type": "string", "description": "추천 신발 (한국어, 흔한 신발 이름)"},
        "reason": {"type": "string", "description": "이 코디가 오늘 기분에 어울리는 이유 한 줄"},
    },
    "required": REQUIRED_KEYS,
    "additionalProperties": False,
}

# AI에게 주는 역할 설명
SYSTEM_INSTRUCTION = (
    "너는 친절한 패션 코디네이터야. "
    "사용자의 성별과 오늘의 기분에 어울리는 상의, 하의, 신발을 하나씩 추천해. "
    "반드시 한국어로, 옷가게나 온라인 쇼핑몰에서 실제로 쉽게 구할 수 있는 흔한 옷 이름으로 답해. "
    "(예: 흰색 오버핏 티셔츠, 연청 와이드 데님 팬츠, 흰색 캔버스 스니커즈) "
    "브랜드 이름은 쓰지 마. "
    "답은 top, bottom, shoes, reason 네 개의 키만 가진 JSON 객체로만 해. 다른 글은 쓰지 마. "
    "reason에는 이 코디가 왜 오늘 기분에 어울리는지 한 줄(한 문장)로 설명해."
)


# ===== 2. 우리가 직접 만든 오류 종류 =====
# 오류마다 "사용자에게 보여줄 상태 코드와 메시지"를 담아 둬요.
# 내부 오류 내용(키, 상세 원인)은 절대 여기에 넣지 않아요.

class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


# ===== 3. 입력 검증 =====

def validate_input(data):
    """요청 데이터에서 gender와 mood를 꺼내고, 허용된 값인지 확인해요."""
    if not isinstance(data, dict):
        raise ApiError(400, "요청 형식이 올바르지 않아요.")

    gender = data.get("gender")
    mood = data.get("mood")

    if not gender or not mood:
        raise ApiError(400, "성별과 기분을 모두 선택해주세요.")
    if gender not in ALLOWED_GENDERS:
        raise ApiError(400, "지원하지 않는 성별 값이에요.")
    if mood not in ALLOWED_MOODS:
        raise ApiError(400, "지원하지 않는 기분 값이에요.")

    return gender, mood


# ===== 4. AI 호출 =====

def build_prompt(gender, mood):
    """AI에게 보낼 질문을 만들어요."""
    return (
        f"성별: {gender}\n"
        f"오늘의 기분: {mood}\n\n"
        "위 정보에 맞는 오늘의 코디를 추천해줘. "
        '{"top": "...", "bottom": "...", "shoes": "...", "reason": "..."} '
        "형식의 JSON으로만 답해."
    )


def get_status_code(error):
    """
    SDK가 던진 오류에서 HTTP 상태 코드(예: 429)를 찾아요.
    SDK 버전이나 기능에 따라 코드가 담긴 이름이 달라서 여러 곳을 확인해요.
    """
    for name in ("code", "status_code"):
        value = getattr(error, name, None)
        if isinstance(value, int):
            return value
    response = getattr(error, "response", None)
    value = getattr(response, "status_code", None)
    if isinstance(value, int):
        return value
    return None


def call_gemini(gender, mood):
    """Gemini API를 호출하고, AI가 돌려준 글자(JSON 문자열)를 반환해요."""
    # API 키는 반드시 환경 변수에서만 읽어요. (코드에 직접 쓰지 않아요)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # 키가 없다는 사실만 기록하고, 사용자에게는 일반적인 안내만 보여줘요
        print("[recommend] GEMINI_API_KEY 환경 변수가 설정되지 않았어요.")
        raise ApiError(500, "서버 설정에 문제가 있어요. 잠시 후 다시 시도해주세요.")

    model = os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=HTTP_TIMEOUT_MS,
            # 자동 재시도를 꺼요. (재시도하면 시간이 너무 길어질 수 있어요)
            # Interactions API에서는 attempts가 "재시도 횟수"라서 0이면 딱 한 번만 시도해요.
            retry_options=types.HttpRetryOptions(attempts=0),
        ),
    )

    def request():
        interaction = client.interactions.create(
            model=model,
            system_instruction=SYSTEM_INSTRUCTION,
            input=build_prompt(gender, mood),
            # 공식 문서의 JSON 출력 설정: 답을 JSON 스키마 모양으로 받아요
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": RESPONSE_SCHEMA,
            },
            store=False,  # 대화 기록을 서버에 저장하지 않아요
        )
        return interaction.output_text

    # 혹시 SDK 시간 제한이 제대로 동작하지 않더라도,
    # 정해진 시간(TOTAL_TIMEOUT_SEC)이 지나면 기다리지 않고 바로 응답하도록 한 번 더 막아둬요.
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(request)
        return future.result(timeout=TOTAL_TIMEOUT_SEC)
    except FutureTimeoutError:
        print("[recommend] Gemini 호출 시간 초과")
        raise ApiError(500, "AI 응답이 늦어지고 있어요. 잠시 후 다시 시도해주세요.")
    except ApiError:
        raise
    except Exception as error:
        status = get_status_code(error)
        # 오류 종류와 상태 코드만 기록해요. (오류 메시지 전체는 남기지 않아요)
        print(f"[recommend] Gemini 호출 실패: {type(error).__name__}, status={status}")
        if status == 429:
            raise ApiError(429, "요청이 많아 잠시 쉬고 있어요. 잠시 후 다시 시도해주세요.")
        raise ApiError(500, "코디 추천 중 문제가 생겼어요. 잠시 후 다시 시도해주세요.")
    finally:
        # 기다리던 작업이 남아 있어도 붙잡지 않고 바로 정리해요
        executor.shutdown(wait=False)


def parse_ai_result(text):
    """AI가 돌려준 글자를 JSON으로 바꾸고, 필요한 키가 다 있는지 확인해요."""
    if not text:
        raise ApiError(502, "AI가 올바른 답을 주지 않았어요. 다시 시도해주세요.")

    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        raise ApiError(502, "AI가 올바른 답을 주지 않았어요. 다시 시도해주세요.")

    if not isinstance(data, dict):
        raise ApiError(502, "AI가 올바른 답을 주지 않았어요. 다시 시도해주세요.")

    result = {}
    for key in REQUIRED_KEYS:
        value = data.get(key)
        # 키가 없거나, 글자가 아니거나, 비어 있으면 잘못된 답으로 봐요
        if not isinstance(value, str) or not value.strip():
            raise ApiError(502, "AI가 올바른 답을 주지 않았어요. 다시 시도해주세요.")
        result[key] = value.strip()

    # 필요한 네 개 키만 골라서 돌려줘요
    return result


# ===== 5. Vercel이 실행하는 요청 처리기 =====
# Vercel Python 함수는 handler라는 이름의 클래스를 찾아서 실행해요.

class handler(BaseHTTPRequestHandler):

    def send_json(self, status, data):
        """상태 코드와 JSON 데이터를 응답으로 보내요."""
        # ensure_ascii=False: 한글이 \uXXXX 모양으로 바뀌지 않고 그대로 나가요
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")  # 추천 결과는 저장(캐시)하지 않아요
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        """요청 본문(body)을 읽어서 파이썬 딕셔너리로 바꿔요."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(400, "요청 형식이 올바르지 않아요.")

        if length <= 0:
            raise ApiError(400, "성별과 기분을 모두 선택해주세요.")
        if length > MAX_BODY_BYTES:
            raise ApiError(400, "요청 데이터가 너무 커요.")

        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "요청 형식이 올바르지 않아요.")

    def do_POST(self):
        """POST /api/recommend 요청을 처리해요."""
        try:
            data = self.read_json_body()          # 1) 요청 읽기
            gender, mood = validate_input(data)   # 2) 입력 검증
            text = call_gemini(gender, mood)      # 3) AI 호출
            result = parse_ai_result(text)        # 4) AI 답 확인
            self.send_json(200, result)           # 5) 성공 응답
        except ApiError as error:
            # 우리가 미리 정한 안전한 메시지만 보내요
            self.send_json(error.status, {"error": error.message})
        except Exception as error:
            # 예상하지 못한 오류: 내부 내용은 숨기고 일반 안내만 보내요
            print(f"[recommend] 예상하지 못한 오류: {type(error).__name__}")
            self.send_json(500, {"error": "잠시 후 다시 시도해주세요."})

    def do_GET(self):
        """POST가 아닌 요청은 받지 않아요."""
        self.send_response(405)
        self.send_header("Allow", "POST")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "POST 요청만 사용할 수 있어요."}, ensure_ascii=False).encode("utf-8"))

    # PUT, DELETE 등 다른 방식도 GET과 똑같이 거절해요
    do_PUT = do_GET
    do_DELETE = do_GET
    do_PATCH = do_GET

    def log_message(self, format, *args):
        """기본 접속 기록은 끄고, 필요한 것만 직접 print로 남겨요."""
        return
