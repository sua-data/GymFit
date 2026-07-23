-- trainer_member의 모든 요청·연결 이력이 삭제됩니다. 필요한 데이터를 먼저 백업하십시오.
-- users와 기존 프로필·운동 데이터는 변경하거나 삭제하지 않습니다.

SHOW TABLES LIKE 'trainer_member';
SELECT status, COUNT(*) AS relationship_count
FROM trainer_member
GROUP BY status;

DROP TABLE trainer_member;

SHOW TABLES LIKE 'trainer_member';
