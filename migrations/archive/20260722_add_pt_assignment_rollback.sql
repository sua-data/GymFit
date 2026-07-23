-- 경고: 이 롤백은 모든 PT 숙제 데이터를 영구 삭제합니다. 먼저 아래 건수와 백업을 확인하십시오.
SELECT COUNT(*) AS pt_assignment_count FROM pt_assignment;
DROP TABLE pt_assignment;
