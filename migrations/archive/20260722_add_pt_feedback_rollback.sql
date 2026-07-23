-- 경고: 이 롤백은 트레이너 피드백 데이터를 영구 삭제합니다. 백업 후 실행하십시오.
SELECT COUNT(*) AS pt_feedback_count FROM pt_feedback;
DROP TABLE pt_feedback;
