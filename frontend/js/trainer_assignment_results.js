(function () {
  const overlay = document.querySelector("#assignmentResultOverlay");
  const panel = document.querySelector("#assignmentResultPanel");
  const content = document.querySelector("#assignmentResultContent");
  let user = null;
  let busy = false;
  try { user = JSON.parse(sessionStorage.getItem("gymfitUser") || "null"); } catch { user = null; }
  const userId = Number(user?.user_id ?? user?.userId);
  if (!userId || String(user?.account_type).toUpperCase() !== "TRAINER" || !overlay || !panel || !content) return;

  const escapeHtml = value => String(value ?? "").replace(/[&<>'"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));

  async function api(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        "X-User-Id": String(userId),
      },
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) throw new Error(body?.detail || "요청을 처리하지 못했습니다.");
    return body;
  }

  function closeResult() {
    if (busy) return;
    overlay.hidden = true;
    document.body.classList.remove("assignment-sheet-open");
    content.replaceChildren();
  }

  async function openResult(assignmentId) {
    overlay.hidden = false;
    document.body.classList.add("assignment-sheet-open");
    content.innerHTML = '<p class="assignment-state">운동 결과를 불러오는 중입니다.</p>';
    try {
      const result = await api(`/api/pt/assignments/${assignmentId}/result`);
      const sourceLabel = result.record_source === "PT_ASSIGNMENT_MANUAL" ? "수동 기록" : "실시간 코칭";
      const score = result.posture_score === null ? "측정 없음" : `${Number(result.posture_score)}점`;
      const calories = result.calories === null || result.calories === undefined
        ? "계산되지 않음"
        : `${Number(result.calories)}kcal`;
      const image = result.image_url
        ? `<img class="assignment-result-image" src="${escapeHtml(result.image_url)}" alt="저장된 대표 자세 이미지">`
        : '<p class="assignment-result-empty">저장된 자세 이미지가 없습니다.</p>';
      const manualNote = result.manual_note ? `<section class="assignment-result-copy"><h3>회원 메모</h3><p>${escapeHtml(result.manual_note)}</p></section>` : "";
      content.innerHTML = `
        <div class="assignment-result-heading">
          <span class="assignment-badge">${sourceLabel}</span>
          <h2>${escapeHtml(result.assignment.exercise_name)}</h2>
          <p>${escapeHtml(result.assignment.member_name)} 회원</p>
        </div>
        <div class="assignment-result-grid">
          <span><strong>${Number(result.completed_sets)}</strong>완료 세트</span>
          <span><strong>${Number(result.repetition_count)}</strong>총 반복</span>
          <span><strong>${Number(result.workout_minutes)}분</strong>운동 시간</span>
          <span><strong>${calories}</strong>예상 소모 칼로리</span>
          <span><strong>${score}</strong>자세 점수</span>
        </div>
        ${image}
        ${manualNote}
        <section class="assignment-result-copy"><h3>${escapeHtml(result.feedback_title || "AI 운동 피드백")}</h3><p>${escapeHtml(result.feedback || (sourceLabel === "수동 기록" ? "수동 기록에는 자세 분석 피드백이 없습니다." : "저장된 자동 피드백이 없습니다."))}</p></section>
        <form id="trainerFeedbackForm" class="assignment-form trainer-feedback-form">
          <label><span>트레이너 피드백</span><textarea id="trainerFeedbackContent" maxlength="5000" required placeholder="회원에게 전달할 피드백을 작성하세요."></textarea></label>
          <button type="submit">피드백 저장</button>
          <p id="trainerFeedbackMessage" class="assignment-form-message" role="alert"></p>
        </form>`;
      document.querySelector("#trainerFeedbackContent").value = result.trainer_feedback_content || "";
      document.querySelector("#trainerFeedbackForm").addEventListener("submit", event => saveFeedback(event, assignmentId, result.trainer_feedback_id));
    } catch (error) {
      console.error("PT 숙제 결과 조회 실패:", error);
      content.innerHTML = '<div class="assignment-state gymfit-state"><strong>운동 결과를 불러오지 못했습니다.</strong><p>목록으로 돌아간 뒤 다시 시도해 주세요.</p></div>';
    }
  }

  async function saveFeedback(event, assignmentId, feedbackId) {
    event.preventDefault();
    if (busy) return;
    const feedbackContent = document.querySelector("#trainerFeedbackContent").value.trim();
    const feedbackMessage = document.querySelector("#trainerFeedbackMessage");
    if (!feedbackContent) { feedbackMessage.textContent = "피드백을 입력해 주세요."; return; }
    busy = true;
    try {
      await api(
        feedbackId ? `/api/pt/feedback/${feedbackId}` : `/api/pt/assignments/${assignmentId}/feedback`,
        { method: feedbackId ? "PATCH" : "POST", body: JSON.stringify({ content: feedbackContent }) }
      );
      await openResult(assignmentId);
    } catch (error) {
      feedbackMessage.textContent = error.message;
    } finally {
      busy = false;
    }
  }

  document.querySelector("#assignmentResultClose").addEventListener("click", closeResult);
  document.querySelector("#assignmentResultBackdrop").addEventListener("click", closeResult);
  window.addEventListener("trainerAssignmentResultRequested", event => {
    const assignmentId = Number(event.detail?.assignmentId);
    if (assignmentId > 0) openResult(assignmentId);
  });
})();
