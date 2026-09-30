# 무드핏 (MoodFit)

> 성별과 오늘의 기분을 고르면 AI가 상의·하의·신발을 추천해주는 코디 도우미

**배포 주소:** https://moodfit-9lkd2ajo8-codyssey7.vercel.app/

---

## 1. 서비스 소개

무드핏은 "오늘 뭐 입지?" 고민을 덜어주는 웹 서비스예요.
성별과 지금 기분을 하나씩 고르고 **추천 받기**를 누르면, Google Gemini AI가 기분에 어울리는 **상의, 하의, 신발**과 **추천 이유 한 줄**을 알려줘요.

- 성별: 여성 / 남성 / 상관없음
- 기분: 신나요 / 평온해요 / 우울해요 / 피곤해요 / 자신감 있어요
- AI에게는 한국어로, 옷가게나 온라인 쇼핑몰에서 쉽게 구할 수 있는 흔한 옷 이름으로, 브랜드 이름 없이 추천하라고 요청해요.

## 2. 주요 기능과 페이지 구성

한 페이지 안에 3개의 섹션이 있어요. 상단 메뉴(홈 / 코디 추천 / 이용 방법)를 누르면 해당 섹션으로 부드럽게 스크롤돼요. 화면 너비가 768px보다 좁으면 햄버거 버튼(☰)으로 메뉴를 열고 닫아요.

| 섹션 | 내용 |
| --- | --- |
| **홈** | 서비스 이름, 한 줄 소개, "코디 받으러 가기" 버튼 (누르면 코디 추천 섹션으로 이동) |
| **코디 추천** | 성별·기분 선택 버튼(각각 하나만 선택), "추천 받기" 버튼, 결과 카드(상의·하의·신발·추천 이유), "다시 추천받기" 버튼 |
| **이용 방법 / FAQ** | 3단계 이용 방법 카드, 누르면 열리는 자주 묻는 질문 4개 |

그 밖의 동작:

- 요청 중에는 "추천 받기"와 "다시 추천받기" 버튼이 비활성화돼서 중복 요청을 막아요.
- "다시 추천받기"는 지금 선택된 성별·기분으로 새 코디를 다시 요청해요.
- 화면은 모바일(375px), 태블릿(768px 이상), 데스크톱(1200px 이상)에 맞춰 레이아웃이 바뀌어요.

## 3. 기술 스택

| 구분 | 사용 기술 |
| --- | --- |
| 화면(프론트엔드) | 순수 HTML / CSS / JavaScript (프레임워크·라이브러리 없음) |
| 서버(백엔드) | Vercel Serverless Functions (Python, WSGI 방식) |
| AI | Google Gemini API (`google-genai` 패키지의 Interactions API) |
| 기본 AI 모델 | `gemini-3.5-flash-lite` (환경 변수 `GEMINI_MODEL`로 바꿀 수 있음) |
| 배포 | Vercel (GitHub 연동) |

## 4. 폴더 구조

```
moodfit/
├── public/                 # 화면에 보이는 정적 파일 (Vercel이 그대로 보여줘요)
│   ├── index.html          # 페이지 뼈대 (홈 / 코디 추천 / 이용 방법·FAQ)
│   ├── css/
│   │   └── style.css       # 디자인과 반응형 레이아웃
│   ├── js/
│   │   └── main.js         # 메뉴, 선택 버튼, 서버 요청, 결과 표시
│   └── images/             # 이미지 폴더 (현재는 비어 있음)
├── api/
│   └── recommend.py        # 서버 함수: /api/recommend 요청 처리 + Gemini 호출
├── pyproject.toml          # Python 프로젝트 정보와 Vercel 진입점(api.recommend:app)
├── requirements.txt        # 필요한 Python 패키지 (google-genai)
├── .gitignore              # git에 올리지 않을 파일 목록 (.env 등)
└── README.md
```

> `.env`, `.env.local`처럼 API 키가 들어가는 파일은 `.gitignore`에 등록되어 있어서 GitHub에 올라가지 않아요.

## 5. 데이터 흐름

```
[화면: public/js/main.js]
   │  1. 사용자가 성별·기분을 고르고 "추천 받기" 클릭
   │  2. fetch('/api/recommend') 로 POST 요청
   │     보내는 데이터: { "gender": "여성", "mood": "신나요" }
   ▼
[서버 함수: api/recommend.py 의 app]
   │  3. 요청 본문을 읽고, gender·mood가 허용된 값인지 검사
   │  4. 환경 변수에서 GEMINI_API_KEY를 읽어 Gemini 호출
   ▼
[Google Gemini API]
   │  5. JSON 형식으로 코디 추천을 돌려줌
   ▼
[서버 함수]
   │  6. AI 답이 올바른 JSON인지, top·bottom·shoes·reason이 다 있는지 확인
   │  7. 화면에 JSON으로 응답
   │     받는 데이터: { "top": "...", "bottom": "...", "shoes": "...", "reason": "..." }
   ▼
[화면]
      8. 결과 카드에 상의·하의·신발·추천 이유를 보여줌
```

API 키는 서버 함수에서만 쓰여요. 화면(브라우저) 코드에는 키가 없어요.

## 6. 로컬에서 실행하기

### 준비물

- [Python](https://www.python.org/) 3.12 이상 (`pyproject.toml`의 `requires-python = ">=3.12"`)
- [Node.js](https://nodejs.org/) (Vercel CLI 설치용)
- Vercel 계정과 [Google AI Studio](https://aistudio.google.com/)에서 발급받은 Gemini API 키

### 실행 순서

**1) 저장소 받기**

```bash
git clone <이 저장소 주소>
cd moodfit
```

**2) Python 가상환경을 만들고 패키지 설치**

```bash
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

**3) `.env` 파일 만들기**

프로젝트 루트(`moodfit/`)에 `.env` 파일을 만들고 아래처럼 적어요. `여기에_발급받은_키`는 본인 키로 바꿔주세요.

```
GEMINI_API_KEY=여기에_발급받은_키
```

모델을 바꾸고 싶을 때만 아래 줄을 추가해요. (없으면 `gemini-3.5-flash-lite`를 써요)

```
GEMINI_MODEL=사용할_모델_이름
```

> ⚠️ `.env` 파일은 절대 GitHub에 올리거나 다른 사람에게 공유하지 마세요.

**4) Vercel CLI 설치 후 실행**

```bash
npm install -g vercel
vercel login
vercel dev
```

처음 실행하면 Vercel 프로젝트와 연결할지 물어봐요. 안내에 따라 답하면 돼요.
실행되면 터미널에 나온 주소(보통 `http://localhost:3000`)를 브라우저에서 열어요.

> 참고: `public/index.html`을 더블클릭해서 바로 열면 화면은 보이지만, 서버 함수가 없어서 추천을 받을 때 "잠시 후 다시 시도해주세요."가 나와요. AI 추천까지 확인하려면 `vercel dev`로 실행해야 해요.

## 7. 환경 변수 설정

| 이름 | 필수 여부 | 설명 |
| --- | --- | --- |
| `GEMINI_API_KEY` | **필수** | Gemini API 키. 없으면 서버가 500 오류를 돌려줘요. |
| `GEMINI_MODEL` | 선택 | 사용할 Gemini 모델 이름. 비워두면 `gemini-3.5-flash-lite`를 사용해요. |

### 로컬

위의 [6. 로컬에서 실행하기](#6-로컬에서-실행하기)처럼 프로젝트 루트의 `.env` 파일에 적어요.

### 배포 (Vercel)

1. Vercel 대시보드에서 moodfit 프로젝트를 열어요.
2. **Settings → Environment Variables** 로 이동해요.
3. Key에 `GEMINI_API_KEY`, Value에 발급받은 키를 넣어요. (필요하면 `GEMINI_MODEL`도 추가)
4. 적용할 환경(Production / Preview / Development)을 골라 저장해요.

> ⚠️ **환경 변수를 추가하거나 바꾼 뒤에는 꼭 재배포해야 해요.**
> Vercel에서 환경 변수를 바꿔도 이미 만들어진 배포에는 적용되지 않고, **새로 배포할 때부터** 적용돼요.
> Deployments 메뉴에서 **Redeploy**를 누르거나, 새 커밋을 push하면 돼요.

## 8. 배포 방법

1. 이 프로젝트를 GitHub 저장소에 올려요.
2. [Vercel](https://vercel.com/)에서 **Add New → Project**를 누르고 GitHub 저장소를 가져와요(Import).
3. [7. 환경 변수 설정](#7-환경-변수-설정)대로 `GEMINI_API_KEY`를 등록해요.
4. 배포(Deploy)해요.

연동이 끝나면 **GitHub에 push할 때마다 Vercel이 자동으로 배포**해요.

- Production 브랜치(보통 `main`)에 push → 실제 서비스(Production)에 배포
- 다른 브랜치에 push → 미리보기(Preview) 배포

## 9. AI 기능의 입력 / 출력과 실패 처리

### 입력 (화면 → 서버)

`POST /api/recommend`

```json
{ "gender": "여성", "mood": "신나요" }
```

- `gender`: `"여성"`, `"남성"`, `"상관없음"` 중 하나
- `mood`: `"신나요"`, `"평온해요"`, `"우울해요"`, `"피곤해요"`, `"자신감 있어요"` 중 하나

### 출력 (서버 → 화면)

성공하면 HTTP 200과 함께:

```json
{
  "top": "상의",
  "bottom": "하의",
  "shoes": "신발",
  "reason": "이 코디가 오늘 기분에 어울리는 이유 한 줄"
}
```

실패하면 오류 상태 코드와 함께 `{ "error": "안내 문구" }`를 돌려줘요.
오류 응답에는 미리 정해 둔 안내 문구만 들어가고, API 키나 내부 오류 내용은 들어가지 않아요.

### 서버 오류 코드 (`api/recommend.py`)

| 코드 | 언제 나오나요? | 서버가 보내는 `error` 문구 |
| --- | --- | --- |
| **400** | 요청 본문이 비어 있거나, 성별·기분 중 하나가 없음 | 성별과 기분을 모두 선택해주세요. |
| | 요청이 JSON 형식이 아니거나 객체가 아님 | 요청 형식이 올바르지 않아요. |
| | 요청 본문이 1024바이트보다 큼 | 요청 데이터가 너무 커요. |
| | 허용 목록에 없는 성별 | 지원하지 않는 성별 값이에요. |
| | 허용 목록에 없는 기분 | 지원하지 않는 기분 값이에요. |
| **429** | Gemini 사용 한도 초과 | 요청이 많아 잠시 쉬고 있어요. 잠시 후 다시 시도해주세요. |
| **500** | 서버에 `GEMINI_API_KEY`가 설정되지 않음 | 서버 설정에 문제가 있어요. 잠시 후 다시 시도해주세요. |
| | Gemini 호출이 12초 안에 끝나지 않음 | AI 응답이 늦어지고 있어요. 잠시 후 다시 시도해주세요. |
| | 그 밖의 Gemini 호출 오류 | 코디 추천 중 문제가 생겼어요. 잠시 후 다시 시도해주세요. |
| | 예상하지 못한 서버 오류 | 잠시 후 다시 시도해주세요. |
| **502** | AI 답이 비어 있거나, JSON이 아니거나, top·bottom·shoes·reason 중 빠지거나 빈 값이 있음 | AI가 올바른 답을 주지 않았어요. 다시 시도해주세요. |

> POST가 아닌 방식(GET 등)으로 요청하면 405와 "POST 요청만 사용할 수 있어요."를 돌려줘요.

시간 제한: 서버는 Gemini와의 통신을 10초, AI 호출 전체를 12초로 제한하고, 자동 재시도는 하지 않아요. 화면이 15초에 요청을 끊기 전에 서버가 먼저 응답하도록 맞춘 거예요.

### 화면에 나오는 안내 문구 (`public/js/main.js`)

화면은 서버가 보낸 `error` 문구를 그대로 보여주지 않고, 상황에 따라 아래 문구 중 하나를 보여줘요.

| 상황 | 화면 안내 문구 |
| --- | --- |
| 성별이나 기분을 고르지 않고 "추천 받기"를 누름 (서버에 요청하지 않음) | 성별과 기분을 선택해주세요. |
| 응답을 기다리는 중 (로딩 표시와 함께) | 코디를 고르는 중이에요... |
| 서버가 오류 코드(400, 429, 500, 502 등)를 돌려줌 | 잠시 후 다시 시도해주세요. |
| 서버에 연결할 수 없음 (네트워크 오류 등) | 잠시 후 다시 시도해주세요. |
| 200을 받았지만 top·bottom·shoes·reason 중 빠진 값이 있음 | 잠시 후 다시 시도해주세요. |
| 15초 안에 응답이 없어 요청을 중단함 | 응답이 늦어지고 있어요. 다시 시도해주세요. |

## 10. 배포 주소

👉 https://moodfit-9lkd2ajo8-codyssey7.vercel.app/
