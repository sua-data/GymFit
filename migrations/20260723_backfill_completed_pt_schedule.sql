-- 선택 실행용: 기존 COMPLETED PT 일정 중 기록이 없는 일정만 PT 세션으로 생성합니다.
-- 상세 운동은 알 수 없으므로 생성하지 않습니다. 실행 전 검토/백업하십시오.
INSERT INTO workout_record (
  user_id, record_type, title, workout_date, trainer_id, pt_schedule_id,
  location, memo, record_source, started_at, completed_at,
  completed_sets, repetition_count, workout_minutes, calories, created_at, updated_at
)
SELECT ps.member_id, 'PT', 'PT 수업', DATE(ps.start_at), ps.trainer_id, ps.schedule_id,
       ps.location, ps.memo, 'PT_SCHEDULE', ps.start_at, ps.end_at,
       0, 0, TIMESTAMPDIFF(MINUTE, ps.start_at, ps.end_at), 0, ps.updated_at, ps.updated_at
FROM pt_schedule ps
WHERE ps.status = 'COMPLETED'
  AND NOT EXISTS (
    SELECT 1 FROM workout_record wr WHERE wr.pt_schedule_id = ps.schedule_id
  );

SELECT COUNT(*) AS completed_pt_without_record
FROM pt_schedule ps
LEFT JOIN workout_record wr ON wr.pt_schedule_id = ps.schedule_id
WHERE ps.status = 'COMPLETED' AND wr.workout_record_id IS NULL;
