const camera = document.getElementById("camera");
const photoPreview = document.getElementById("photoPreview");
const cameraStatus = document.getElementById("cameraStatus");
const scanButton = document.getElementById("scanButton");
const heroScanButton = document.getElementById("heroScanButton");
const demoButton = document.getElementById("demoButton");
const photoInput = document.getElementById("photoInput");
const photoButton = document.getElementById("photoButton");
const photoStatus = document.getElementById("photoStatus");
const canvas = document.getElementById("snapshotCanvas");
const ctx = canvas.getContext("2d", { willReadFrequently: true });
const timelineBar = document.getElementById("timelineBar");
const feedbackStatus = document.getElementById("feedbackStatus");
const exportStatus = document.getElementById("exportStatus");
const refreshStatsButton = document.getElementById("refreshStatsButton");
const exportButton = document.getElementById("exportButton");
const phoneStartButton = document.getElementById("phoneStartButton");
const phoneDemoButton = document.getElementById("phoneDemoButton");
const syncButton = document.getElementById("syncButton");
const phoneStage = document.getElementById("phoneStage");
const phoneScore = document.getElementById("phoneScore");
const phoneState = document.getElementById("phoneState");
const phoneProgress = document.getElementById("phoneProgress");
const phoneHr = document.getElementById("phoneHr");
const phoneStress = document.getElementById("phoneStress");
const phoneRecovery = document.getElementById("phoneRecovery");

const feedbackButtons = Array.from(document.querySelectorAll("[data-feedback]"));

const state = {
  analysis: null,
  stream: null,
  isScanning: false,
  uploadedPhoto: null,
};

const sampleCanvas = document.createElement("canvas");
sampleCanvas.width = 320;
sampleCanvas.height = 240;
const sampleCtx = sampleCanvas.getContext("2d");

function setButtonLabel(button, text) {
  const label = button?.querySelector("span");
  if (label) {
    label.textContent = text;
  }
}

function updateMetric(id, value, suffix = "") {
  const target = document.getElementById(id);
  if (!target) {
    return;
  }
  target.textContent = value === null || value === undefined || value === "" ? "--" : `${value}${suffix}`;
}

function formatSignedDecimal(value) {
  const number = Number(value);
  return Number.isNaN(number) ? "--" : number.toFixed(2);
}

function updatePhone(stage, progress, detail = "") {
  phoneStage.textContent = stage;
  phoneState.textContent = detail;
  phoneProgress.style.width = `${Math.max(0, Math.min(100, progress))}%`;
}

function renderPhoneResult(result) {
  phoneScore.textContent = result.mood_index ?? "--";
  phoneHr.textContent = result.hr || "--";
  phoneStress.textContent = result.stress_index ?? "--";
  phoneRecovery.textContent = result.recovery_index ?? "--";
  updatePhone("Insight ready", result.mood_index ?? 100, result.advice_title || "결과가 준비되었습니다.");
}

async function setupCamera() {
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
    camera.srcObject = state.stream;
    cameraStatus.textContent = "카메라 연결됨";
    updatePhone("Camera ready", 8, "휴대폰에서도 같은 방식으로 카메라 권한을 요청합니다.");
  } catch (error) {
    console.error(error);
    cameraStatus.textContent = "카메라 접근 실패";
    scanButton.disabled = true;
    updatePhone("Demo mode", 8, "카메라 없이도 파이프라인 데모를 실행할 수 있습니다.");
  }
}

function computeFrameStats() {
  ctx.drawImage(camera, 0, 0, canvas.width, canvas.height);
  const { data } = ctx.getImageData(0, 0, canvas.width, canvas.height);
  let brightness = 0;
  let motionSeed = 0;

  for (let index = 0; index < data.length; index += 4) {
    const r = data[index];
    const g = data[index + 1];
    const b = data[index + 2];
    const luma = r * 0.2126 + g * 0.7152 + b * 0.0722;
    brightness += luma;
    motionSeed += Math.abs(r - g) + Math.abs(g - b);
  }

  const pixels = data.length / 4;
  const normalizedBrightness = Math.round(brightness / pixels / 2.55);
  const motion = Math.round(((motionSeed / pixels) / 7.5) % 100);
  const ambientNoise = Math.max(6, Math.round((100 - normalizedBrightness) * 0.35));

  return {
    brightness: normalizedBrightness,
    motion,
    ambient_noise: ambientNoise,
    duration_seconds: 30,
  };
}

function captureFrameSample() {
  sampleCtx.drawImage(camera, 0, 0, sampleCanvas.width, sampleCanvas.height);
  return sampleCanvas.toDataURL("image/jpeg", 0.8);
}

function renderSummary(summary) {
  updateMetric("analysisCount", summary.analyses_count);
  updateMetric("feedbackCount", summary.feedback_count);
  updateMetric("likeCount", summary.likes_count);
  updateMetric("dislikeCount", summary.dislikes_count);
}

function renderAnalysis(result, telemetry) {
  state.analysis = result;
  const isPhotoOnly = result.rppg_source === "photo-expression-only";

  updateMetric("moodIndex", result.mood_index);
  updateMetric("stressIndex", result.stress_index);
  updateMetric("recoveryIndex", result.recovery_index);
  updateMetric("hrValue", isPhotoOnly ? null : result.hr);
  updateMetric("rmssdValue", isPhotoOnly ? null : result.rmssd);
  updateMetric("sdnnValue", isPhotoOnly ? null : result.sdnn);
  updateMetric("rrValue", isPhotoOnly ? null : result.rr);
  updateMetric("brightnessValue", telemetry.brightness, "%");
  updateMetric("motionValue", telemetry.motion, "%");
  updateMetric("signalQualityValue", isPhotoOnly ? null : result.signal_quality, isPhotoOnly ? "" : "%");
  updateMetric("rppgSourceValue", result.rppg_source);
  updateMetric("emojiValue", result.emoji);
  updateMetric("valenceValue", formatSignedDecimal(result.valence));
  updateMetric("arousalValue", formatSignedDecimal(result.arousal));

  document.getElementById("adviceTitle").textContent = result.advice_title;
  document.getElementById("adviceBody").textContent = result.advice_body;
  document.getElementById("disclaimer").textContent = result.disclaimer;
  document.getElementById("confidenceBadge").textContent = `신뢰도 ${result.confidence}%`;
  timelineBar.style.width = `${result.mood_index}%`;

  feedbackButtons.forEach((button) => {
    button.disabled = false;
  });
  feedbackStatus.textContent = "코칭이 현재 상태와 맞는지 알려주세요.";
  if (isPhotoOnly) {
    photoStatus.textContent = "사진 분석 완료. 이 모드는 표정 신호만 추정합니다.";
  }
  renderPhoneResult(result);
}

async function loadHealth() {
  const response = await fetch("/api/health");
  const data = await response.json();
  renderSummary(data.summary);
  exportStatus.textContent = `저장소: ${data.db_path}`;
}

async function runThirtySecondScan() {
  const durationMs = 30000;
  const startedAt = performance.now();
  const frameSamples = [];
  const sampleIntervalMs = 250;
  let samplerId = null;

  return new Promise((resolve) => {
    samplerId = window.setInterval(() => {
      if (state.stream) {
        frameSamples.push(captureFrameSample());
      }
    }, sampleIntervalMs);

    const tick = () => {
      const elapsedMs = performance.now() - startedAt;
      const progressRatio = Math.min(elapsedMs / durationMs, 1);
      const progress = Math.max(3, progressRatio * 100);
      const secondsLeft = Math.max(0, Math.ceil((durationMs - elapsedMs) / 1000));

      timelineBar.style.width = `${progress}%`;
      cameraStatus.textContent = `스캔 중: ${secondsLeft}초 남음`;
      feedbackStatus.textContent = `얼굴을 중앙에 두고 움직임을 줄여주세요. ${secondsLeft}초 남음`;
      updatePhone("Capturing frames", progress, `${secondsLeft}초 남음 · ROI 신호 수집 중`);

      if (progressRatio >= 1) {
        if (samplerId !== null) {
          window.clearInterval(samplerId);
        }
        resolve({
          frameSamples,
          sampleFps: 1000 / sampleIntervalMs,
        });
        return;
      }

      window.requestAnimationFrame(tick);
    };

    window.requestAnimationFrame(tick);
  });
}

async function analyzePayload(payload, endpoint = "/api/analyze") {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return response.json();
}

async function runScan() {
  if (!state.stream || state.isScanning) {
    if (!state.stream) {
      await runDemoScan();
    }
    return;
  }

  state.isScanning = true;
  scanButton.disabled = true;
  heroScanButton.disabled = true;
  setButtonLabel(scanButton, "스캔 중...");
  setButtonLabel(heroScanButton, "스캔 중...");
  feedbackButtons.forEach((button) => {
    button.disabled = true;
  });
  timelineBar.style.width = "0%";
  updatePhone("Starting scan", 3, "카메라 프레임을 준비하는 중");

  const scanCapture = await runThirtySecondScan();
  updatePhone("Analyzing signal", 92, "서버에서 expression + rPPG fusion 실행 중");

  const telemetry = computeFrameStats();
  const result = await analyzePayload({
    ...telemetry,
    sample_fps: scanCapture.sampleFps,
    frame_count: scanCapture.frameSamples.length,
    frame_samples: scanCapture.frameSamples,
    device_user_agent: navigator.userAgent,
  });

  renderAnalysis(result, telemetry);
  await loadHealth();

  state.isScanning = false;
  scanButton.disabled = false;
  heroScanButton.disabled = false;
  setButtonLabel(scanButton, "다시 스캔");
  setButtonLabel(heroScanButton, "다시 스캔");
  cameraStatus.textContent = "스캔 완료";
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function runDemoScan() {
  if (state.isScanning) {
    return;
  }
  state.isScanning = true;
  demoButton.disabled = true;
  phoneDemoButton.disabled = true;
  timelineBar.style.width = "0%";

  const steps = [
    ["Camera preview", 16, "브라우저가 카메라 화면을 준비합니다."],
    ["Face ROI", 34, "얼굴 영역과 조명 품질을 확인합니다."],
    ["rPPG trace", 58, "피부색 변화 기반 PPG 후보 신호를 만듭니다."],
    ["Fusion", 82, "표정·HRV·호흡 후보 지표를 결합합니다."],
    ["Insight ready", 96, "코칭 메시지를 생성합니다."],
  ];

  for (const [stage, progress, detail] of steps) {
    timelineBar.style.width = `${progress}%`;
    updatePhone(stage, progress, detail);
    cameraStatus.textContent = `데모 실행 중: ${stage}`;
    await delay(650);
  }

  const telemetry = {
    brightness: 66,
    motion: 14,
    ambient_noise: 8,
    duration_seconds: 30,
    sample_fps: 0,
    frame_count: 0,
    face_detected_ratio: 1,
    frame_samples: [],
    device_user_agent: `${navigator.userAgent} demo-mode`,
  };
  const result = await analyzePayload(telemetry);
  renderAnalysis(result, telemetry);
  await loadHealth();

  state.isScanning = false;
  demoButton.disabled = false;
  phoneDemoButton.disabled = false;
  cameraStatus.textContent = "데모 완료";
}

function setPhotoPreview(dataUrl) {
  return new Promise((resolve, reject) => {
    state.uploadedPhoto = dataUrl;
    photoPreview.onload = () => {
      photoPreview.hidden = false;
      camera.hidden = true;
      cameraStatus.textContent = "사진 분석 준비 완료";
      updatePhone("Photo mode", 24, "표정 기반 분석만 실행합니다.");
      resolve();
    };
    photoPreview.onerror = reject;
    photoPreview.src = dataUrl;
  });
}

function clearPhotoPreview() {
  if (!state.uploadedPhoto) {
    return;
  }
  state.uploadedPhoto = null;
  photoPreview.hidden = true;
  photoPreview.removeAttribute("src");
  camera.hidden = false;
}

function computePhotoStats() {
  sampleCtx.drawImage(photoPreview, 0, 0, sampleCanvas.width, sampleCanvas.height);
  const { data } = sampleCtx.getImageData(0, 0, sampleCanvas.width, sampleCanvas.height);
  let brightness = 0;

  for (let index = 0; index < data.length; index += 4) {
    const r = data[index];
    const g = data[index + 1];
    const b = data[index + 2];
    brightness += r * 0.2126 + g * 0.7152 + b * 0.0722;
  }

  const pixels = data.length / 4;
  return {
    brightness: Math.round(brightness / pixels / 2.55),
    motion: 0,
    ambient_noise: 0,
    duration_seconds: 5,
  };
}

async function analyzeUploadedPhoto() {
  if (!state.uploadedPhoto || state.isScanning) {
    return;
  }

  state.isScanning = true;
  photoButton.disabled = true;
  scanButton.disabled = true;
  photoStatus.textContent = "업로드한 사진을 분석하는 중...";
  updatePhone("Expression analysis", 64, "단일 사진에서 표정 valence/arousal 추정 중");

  const telemetry = computePhotoStats();
  const result = await analyzePayload(
    {
      ...telemetry,
      frame_count: 1,
      frame_samples: [state.uploadedPhoto],
      device_user_agent: navigator.userAgent,
    },
    "/api/analyze-photo",
  );

  renderAnalysis(result, telemetry);
  await loadHealth();

  state.isScanning = false;
  photoButton.disabled = false;
  scanButton.disabled = false;
}

function handlePhotoSelection(event) {
  const [file] = event.target.files || [];
  if (!file) {
    return;
  }

  const reader = new FileReader();
  reader.onload = async () => {
    clearPhotoPreview();
    await setPhotoPreview(reader.result);
    await analyzeUploadedPhoto();
  };
  reader.readAsDataURL(file);
}

async function sendFeedback(type) {
  if (!state.analysis || state.isScanning) {
    return;
  }

  const payload = {
    session_id: state.analysis.session_id,
    feedback: type,
    self_report_mood: Number(document.getElementById("selfMood").value),
    self_report_anxiety: Number(document.getElementById("selfAnxiety").value),
    notes: document.getElementById("notes").value.trim(),
    device_user_agent: navigator.userAgent,
  };

  feedbackButtons.forEach((button) => {
    button.disabled = true;
  });
  feedbackStatus.textContent = "피드백 저장 중...";

  const response = await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (data.error) {
    feedbackStatus.textContent = `저장 실패: ${data.error}`;
    return;
  }

  feedbackStatus.textContent = `피드백 저장 완료. DB: ${data.db_path}`;
  renderSummary(data.summary);
}

async function exportFeedbackCsv() {
  exportButton.disabled = true;
  exportStatus.textContent = "CSV 내보내는 중...";
  const response = await fetch("/api/export-feedback");
  const data = await response.json();
  exportStatus.textContent = `CSV 생성 완료: ${data.export_path}`;
  exportButton.disabled = false;
}

function syncPhoneFromCurrentResult() {
  if (state.analysis) {
    renderPhoneResult(state.analysis);
    return;
  }
  updatePhone("No result yet", 12, "스캔 또는 데모를 먼저 실행하세요.");
}

scanButton.addEventListener("click", runScan);
heroScanButton.addEventListener("click", runScan);
demoButton.addEventListener("click", runDemoScan);
phoneStartButton.addEventListener("click", runScan);
phoneDemoButton.addEventListener("click", runDemoScan);
syncButton.addEventListener("click", syncPhoneFromCurrentResult);
photoButton.addEventListener("click", () => photoInput.click());
photoInput.addEventListener("change", handlePhotoSelection);
feedbackButtons.forEach((button) => {
  button.addEventListener("click", () => sendFeedback(button.dataset.feedback));
});
refreshStatsButton.addEventListener("click", loadHealth);
exportButton.addEventListener("click", exportFeedbackCsv);

window.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) {
    window.lucide.createIcons();
  }
});

setupCamera();
loadHealth();
