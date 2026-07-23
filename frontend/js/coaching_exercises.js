const exerciseAnalyzers = {
  SQUAT: {
    code: "SQUAT",
    displayName: "스쿼트",
    apiPath: "squat",
    cameraGuide: "전신이 화면에 보이도록 위치를 조정하세요.",
    initialTest: false,
  },
  PUSHUP: {
    code: "PUSHUP",
    displayName: "푸시업",
    apiPath: "pushup",
    cameraGuide: "푸시업 자세의 전신이 옆면으로 보이도록 위치를 조정하세요.",
    initialTest: true,
  },
  SHOULDER_PRESS: {
    code: "SHOULDER_PRESS",
    displayName: "숄더프레스",
    apiPath: "shoulder-press",
    cameraGuide: "상체와 양팔이 모두 화면에 보이도록 위치를 조정하세요.",
    initialTest: true,
  },
};

function getExerciseAnalyzer(exerciseCode) {
  return exerciseAnalyzers[exerciseCode] || null;
}

function isCoachingExerciseCode(exerciseCode) {
  return Boolean(getExerciseAnalyzer(exerciseCode));
}
