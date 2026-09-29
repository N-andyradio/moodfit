/* =========================================
   무드핏(MoodFit) 동작 스크립트
   - 모바일 메뉴 열고 닫기
   - 성별/기분 선택
   - 서버에 코디 추천 요청 보내고 결과 보여주기
   ========================================= */

// 서버 응답을 기다리는 최대 시간 (15초 = 15000밀리초)
const REQUEST_TIMEOUT_MS = 15000;

// 사용자에게 보여줄 안내 문구를 한곳에 모아 둬요
const MESSAGES = {
  needSelect: "성별과 기분을 선택해주세요.",
  loading: "코디를 고르는 중이에요...",
  serverError: "잠시 후 다시 시도해주세요.",
  timeout: "응답이 늦어지고 있어요. 다시 시도해주세요.",
};

/* ----- 1. 화면 요소 가져오기 ----- */
// document.getElementById: HTML에서 id로 요소를 찾아와요
const menuToggle = document.getElementById("menuToggle");
const mainNav = document.getElementById("mainNav");
const navLinks = document.querySelectorAll(".nav-link");

const genderGroup = document.getElementById("genderGroup");
const moodGroup = document.getElementById("moodGroup");
const recommendBtn = document.getElementById("recommendBtn");
const retryBtn = document.getElementById("retryBtn");

const statusBox = document.getElementById("status");
const statusText = document.getElementById("statusText");
const spinner = document.getElementById("spinner");

const resultCard = document.getElementById("result");
const resultTop = document.getElementById("resultTop");
const resultBottom = document.getElementById("resultBottom");
const resultShoes = document.getElementById("resultShoes");
const resultReason = document.getElementById("resultReason");

/* ----- 2. 현재 상태를 저장하는 변수 ----- */
let selectedGender = ""; // 선택한 성별 (예: "여성")
let selectedMood = "";   // 선택한 기분 (예: "신나요")
let isLoading = false;   // 지금 서버에 요청 중인지 여부

/* =========================================
   모바일 메뉴 (햄버거 버튼)
   ========================================= */

// 메뉴를 열거나 닫는 함수. open이 true면 열고, false면 닫아요.
function setMenuOpen(open) {
  mainNav.classList.toggle("is-open", open);
  menuToggle.setAttribute("aria-expanded", String(open));
  menuToggle.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
}

// 햄버거 버튼을 누르면 메뉴 상태를 반대로 바꿔요
menuToggle.addEventListener("click", function () {
  const isOpen = menuToggle.getAttribute("aria-expanded") === "true";
  setMenuOpen(!isOpen);
});

// 메뉴 링크를 누르면 해당 섹션으로 부드럽게 이동하고, 모바일 메뉴는 닫아요
navLinks.forEach(function (link) {
  link.addEventListener("click", function (event) {
    const targetId = link.getAttribute("href"); // 예: "#recommend"
    const target = document.querySelector(targetId);
    if (!target) return;

    event.preventDefault(); // 기본 이동(뚝 끊기는 점프)을 막아요
    target.scrollIntoView({ behavior: "smooth" });
    history.pushState(null, "", targetId); // 주소창에도 #위치를 남겨요
    setMenuOpen(false);
  });
});

// ESC 키를 누르면 메뉴를 닫아요
document.addEventListener("keydown", function (event) {
  if (event.key === "Escape") {
    setMenuOpen(false);
  }
});

/* =========================================
   성별 / 기분 선택 버튼
   ========================================= */

// 버튼 묶음(group) 안에서 하나만 선택되게 만드는 함수
// onSelect: 버튼이 선택됐을 때 그 값을 전달받을 함수
function setupChoiceGroup(group, onSelect) {
  const buttons = group.querySelectorAll(".chip");

  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      // 먼저 모든 버튼의 선택을 해제하고
      buttons.forEach(function (b) {
        b.setAttribute("aria-pressed", "false");
      });
      // 누른 버튼만 선택 상태로 바꿔요
      button.setAttribute("aria-pressed", "true");
      onSelect(button.dataset.value);

      // 둘 다 고른 뒤라면, 이전에 떠 있던 "선택해주세요" 안내는 지워요
      if (selectedGender && selectedMood && !isLoading) {
        hideStatus();
      }
    });
  });
}

setupChoiceGroup(genderGroup, function (value) {
  selectedGender = value;
});

setupChoiceGroup(moodGroup, function (value) {
  selectedMood = value;
});

/* =========================================
   안내 메시지 보여주기 / 숨기기
   ========================================= */

// type: "loading"(로딩 중) 또는 "error"(오류)
function showStatus(message, type) {
  statusText.textContent = message;
  statusBox.classList.toggle("is-error", type === "error");
  spinner.hidden = type !== "loading"; // 로딩일 때만 동그라미 표시
  statusBox.hidden = false;
}

function hideStatus() {
  statusBox.hidden = true;
  statusText.textContent = "";
}

/* =========================================
   로딩 상태 켜고 끄기
   ========================================= */

function setLoading(loading) {
  isLoading = loading;
  // 요청 중에는 버튼을 눌러도 반응하지 않게 막아요 (중복 요청 방지)
  recommendBtn.disabled = loading;
  retryBtn.disabled = loading;
  recommendBtn.textContent = loading ? "추천 중..." : "추천 받기";
}

/* =========================================
   결과 카드 보여주기
   ========================================= */

function showResult(data) {
  // textContent를 쓰면 서버에서 온 글자가 HTML로 해석되지 않아 안전해요
  resultTop.textContent = data.top;
  resultBottom.textContent = data.bottom;
  resultShoes.textContent = data.shoes;
  resultReason.textContent = data.reason;
  resultCard.hidden = false;
  resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// 서버가 보낸 데이터에 필요한 항목(top, bottom, shoes, reason)이 다 있는지 확인해요
function isValidResult(data) {
  if (!data || typeof data !== "object") return false;
  const keys = ["top", "bottom", "shoes", "reason"];
  return keys.every(function (key) {
    return typeof data[key] === "string" && data[key].trim() !== "";
  });
}

/* =========================================
   서버에 코디 추천 요청하기
   ========================================= */

// async 함수: 서버 응답을 기다리는(await) 동안 화면이 멈추지 않아요
async function requestRecommendation() {
  // 이미 요청 중이면 아무것도 하지 않아요
  if (isLoading) return;

  // 1) 성별과 기분을 모두 골랐는지 확인
  if (!selectedGender || !selectedMood) {
    showStatus(MESSAGES.needSelect, "error");
    return;
  }

  // 2) 로딩 표시 시작, 이전 결과는 숨기기
  setLoading(true);
  resultCard.hidden = true;
  showStatus(MESSAGES.loading, "loading");

  // 3) 15초가 지나면 요청을 중단하기 위한 준비
  //    AbortController: 진행 중인 fetch 요청을 취소할 수 있게 해줘요
  const controller = new AbortController();
  const timerId = setTimeout(function () {
    controller.abort();
  }, REQUEST_TIMEOUT_MS);

  try {
    // 4) 서버로 POST 요청 보내기
    const response = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gender: selectedGender, mood: selectedMood }),
      signal: controller.signal, // 이 신호로 요청을 중단할 수 있어요
    });

    // 5) 서버가 오류 상태(4xx, 5xx)를 보낸 경우
    //    response.ok는 상태 코드가 200~299일 때만 true예요
    if (!response.ok) {
      throw new Error("서버 오류: " + response.status);
    }

    // 6) 응답을 JSON으로 바꾸고, 필요한 내용이 다 있는지 확인
    const data = await response.json();
    if (!isValidResult(data)) {
      throw new Error("응답 형식이 올바르지 않아요.");
    }

    // 7) 성공! 안내 메시지를 지우고 결과 카드 보여주기
    hideStatus();
    showResult(data);
  } catch (error) {
    // 요청이 실패하면 여기로 와요
    // - AbortError: 15초가 지나서 우리가 요청을 중단한 경우
    // - 그 외: 서버 오류, 인터넷 연결 실패, 서버가 아직 없는 경우 등
    if (error.name === "AbortError") {
      showStatus(MESSAGES.timeout, "error");
    } else {
      showStatus(MESSAGES.serverError, "error");
    }
    // 개발자가 원인을 확인할 수 있도록 콘솔에 남겨요
    console.error("코디 추천 요청 실패:", error);
  } finally {
    // 성공하든 실패하든 마지막에 항상 실행돼요
    clearTimeout(timerId); // 타이머 정리
    setLoading(false);     // 버튼 다시 활성화
  }
}

// "추천 받기" 버튼
recommendBtn.addEventListener("click", requestRecommendation);

// "다시 추천받기" 버튼: 지금 고른 성별/기분으로 새 코디를 다시 요청해요
retryBtn.addEventListener("click", requestRecommendation);
