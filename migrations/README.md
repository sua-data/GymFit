# GYMFIT 데이터베이스 마이그레이션

## Baseline

`20260723_baseline_schema.sql`은 2026-07-23 현재 최신 GYMFIT 데이터베이스 구조의 기준점입니다. 테이블, 기본키, 외래키, UNIQUE, INDEX, CHECK 제약, 기본값, 문자셋과 collation만 포함하며 실제 데이터는 포함하지 않습니다.

> 경고: 이미 운영 중이거나 기존 개발에 사용 중인 데이터베이스에는 baseline을 다시 실행하지 마세요. 기존 테이블을 다시 생성하기 위한 파일이 아닙니다.

baseline은 신규 빈 데이터베이스를 구성할 때만 실행합니다.

```bash
mysql -u <사용자> -p <빈_데이터베이스명> < migrations/20260723_baseline_schema.sql
```

Windows PowerShell에서는 다음과 같이 실행할 수 있습니다.

```powershell
cmd /c "mysql -u <사용자> -p <빈_데이터베이스명> < migrations\20260723_baseline_schema.sql"
```

## Archive

`archive/`에는 baseline 이전에 작성하고 적용한 변경, 롤백, 검증 SQL 이력이 들어 있습니다. 이 파일들은 과거 변경 이력을 보존하기 위한 것이며 완전히 삭제하지 않습니다.

## 이후 변경 규칙

- baseline 이후의 DB 변경은 `migrations/` 바로 아래에 새 날짜의 migration SQL로 추가합니다.
- 이미 적용된 migration은 수정하거나 삭제하지 않습니다.
- 필요한 경우 원본 migration과 별도의 롤백 SQL을 함께 추가합니다.
- 새 baseline을 만들기 전까지 기존 baseline 파일은 수정하지 않습니다.

## 데이터 백업

실제 데이터가 포함된 로컬 전체 백업은 `backup/gymfit_latest.sql`로 별도 관리합니다. `backup/` 폴더 전체는 Git에 포함되지 않으며, baseline이나 migration 파일에 실제 사용자 데이터를 복사하지 않습니다.
