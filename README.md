# Website Change Discord Watcher

특정 웹사이트의 특정 영역을 감시하고, 변경이 감지되면 Discord 웹훅으로 알림을 보내는 도구입니다.

## 주요 기능
- CSS Selector를 이용한 정밀한 영역 감시
- **`.env` 기반 환경 설정**: 하드코딩 없이 저장소 경로, 파일 경로, 실행 주기를 `.env`로 손쉽게 제어
- **사이트별 개별 감시 주기 설정** (시간 단위)
- **systemd Timer 기반**의 효율적인 실행 및 자동 등록 도구 제공 (리눅스 서버 최적화)
- 안티 봇 방지 (User-Agent 랜덤화, Referer 위장, 지연 시간 적용)
- SQLite 기반의 이전 데이터 및 체크 시간 관리
- Discord 웹훅 알림 지원

---

## 깃허브 리포지토리 복제 및 빠른 시작 (Quick Start)

저장소를 복제하여 재사용할 때 하드코딩된 경로 수정 없이 `.env` 파일 복사만으로 즉시 사용할 수 있습니다.

```bash
# 1. 저장소 복제 및 이동
git clone <repository-url>
cd website-change-discord

# 2. 환경 설정 파일 생성 (.env.bak 복사)
cp .env.bak .env

# 3. .env 파일에 Discord 웹훅 URL 입력 (필요시 경로 및 주기 변경)
# vi .env 또는 nano .env

# 4. 의존성 패키지 동기화
uv sync

# 5. 실행 테스트 (1회성 스캔)
uv run monitor
```

---

## 환경 변수 설정 (`.env`)

모든 주요 파일 경로와 실행 주기는 `.env` 파일을 통해 유연하게 설정할 수 있습니다.

### 환경 변수 목록

| 변수명 | 설명 | 기본값 | 필수 여부 |
| :--- | :--- | :---: | :---: |
| `DISCORD_WEBHOOK_URL` | 알림을 수신할 Discord 웹훅 URL | - | O |
| `PROJECT_DIR` | 프로젝트 루트 디렉토리 (미설정 시 저장소 위치 자동 감지) | 저장소 루트 | X |
| `CONFIG_FILE` | 타깃 사이트 설정 YAML 파일 경로 (상대/절대 경로 지원) | `config.yaml` | X |
| `DB_FILE` | 상태 저장용 SQLite 데이터베이스 경로 | `hashes.db` | X |
| `LOG_FILE` | 실행 로그 기록 파일 경로 | `app.log` | X |
| `DAEMON_INTERVAL_MINUTES` | 데몬 모드 실행 시 스캔 주기 (분 단위) | `60` | X |
| `DEFAULT_INTERVAL_HOURS` | `config.yaml`에 `interval_hours`가 없을 때 기본 주기 (시간 단위) | `24` | X |
| `SYSTEMD_TIMER_ON_CALENDAR` | systemd Timer 실행 주기 (`hourly`, `daily`, `*:0/30` 등) | `hourly` | X |
| `REQUEST_TIMEOUT` | 웹사이트 요청 타임아웃 (초 단위) | `15` | X |
| `DISCORD_TIMEOUT` | Discord 웹훅 전송 타임아웃 (초 단위) | `10` | X |

### `.env` 설정 예시
```env
# Discord 웹훅 URL
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_HERE"

# 프로젝트 디렉토리 (기본값: 저장소 위치 자동 감지)
# PROJECT_DIR=/home/user/website-change-discord

# 주요 파일 경로 (상대 경로는 PROJECT_DIR 기준으로 해석)
CONFIG_FILE=config.yaml
DB_FILE=hashes.db
LOG_FILE=app.log

# 실행 주기 설정
DAEMON_INTERVAL_MINUTES=60
DEFAULT_INTERVAL_HOURS=24
SYSTEMD_TIMER_ON_CALENDAR=hourly
```

---

## 사이트 모니터링 설정 (`config.yaml`)

감시할 사이트 목록과 각 사이트별 주기를 `config.yaml` 파일에서 설정합니다.

### 설정 항목

| 항목 | 설명 | 기본값 | 필수 여부 |
| :--- | :--- | :---: | :---: |
| `name` | 알림 시 표시될 사이트 이름 | - | O |
| `url` | 감시할 웹사이트의 전체 URL | - | O |
| `selector` | 감시할 영역의 CSS Selector | - | O |
| `interval_hours` | 사이트별 체크 주기 (시간 단위) | `.env`의 `DEFAULT_INTERVAL_HOURS` (기본 24) | X |
| `verify_ssl` | SSL 인증서 검증 여부 (`true` / `false`) | `true` | X |

### 설정 예시
```yaml
targets:
  - name: "뉴스 사이트"
    url: "https://news.ycombinator.com"
    selector: ".titleline"
    interval_hours: 12  # 12시간마다 체크

  - name: "공지사항"
    url: "https://www.example.com/notice"
    selector: "table.notice-list"
    interval_hours: 6   # 6시간마다 체크
```

## 간편하게 사이트 추가하기 (`add_site`)

대화형 CLI 도구를 사용하여 `config.yaml`에 사이트를 쉽게 등록할 수 있습니다.

```bash
uv run add_site
```

- **실시간 테스트**: 입력한 URL과 CSS Selector가 올바른지 즉시 확인하고 추출된 텍스트를 미리 보여줍니다.
- **자동 저장**: 테스트 결과 확인 후 `config.yaml`에 자동 반영합니다.
- **중복 방지**: 이미 등록된 URL이 있을 경우 경고를 표시합니다.

---

## 실행 모드

### 1. 1회성 스캔 실행
모든 대상 사이트의 주기 도래 여부를 확인하고 스캔한 뒤 종료됩니다.
```bash
uv run monitor
```

### 2. 데몬 모드로 실행
백그라운드 또는 프로세스 관리자로 계속 실행하며, `.env`의 `DAEMON_INTERVAL_MINUTES` 주기로 스캔하고 `config.yaml` 변경 시 즉시 스캔합니다.
```bash
uv run monitor --daemon
```

---

## 리눅스 서버에서 자동 실행 (systemd User Service)

리눅스 서버에서는 **systemd 사용자 서비스와 타이머**를 사용하는 것이 가장 안정적입니다.
`.env` 파일에 정의된 경로와 실행 주기(`SYSTEMD_TIMER_ON_CALENDAR`)를 바탕으로 유닛 파일을 자동 생성하고 등록할 수 있습니다.

### 방법 1. 자동 설정 (권장)

`setup_systemd` 명령어로 현재 프로젝트 위치와 `.env` 설정을 반영하여 즉시 등록합니다:

```bash
# 유닛 파일 생성 및 daemon-reload 후 타이머/패스 감시 활성화
uv run setup_systemd --enable

# 또는 제공되는 셸 스크립트 실행
./scripts/setup_systemd.sh --enable
```

> 미리 생성될 유닛 파일 내용을 확인하려면 `--dry-run` 옵션을 사용할 수 있습니다:
> ```bash
> uv run setup_systemd --dry-run
> ```

### 방법 2. 수동 설정

수동으로 유닛 파일을 설정하려는 경우 `systemd/` 디렉토리의 파일들을 사용자 디렉토리로 복사하여 등록합니다:

```bash
mkdir -p ~/.config/systemd/user/
cp systemd/website-change.service ~/.config/systemd/user/
cp systemd/website-change.timer ~/.config/systemd/user/
cp systemd/website-change.path ~/.config/systemd/user/

# 필요시 ~/.config/systemd/user/website-change.service 내 WorkingDirectory 경로 수정 후:
systemctl --user daemon-reload
systemctl --user enable --now website-change.timer
systemctl --user enable --now website-change.path
```

### 로그아웃 후에도 실행 유지 (Linger 설정)
서버에서 SSH 세션을 종료해도 사용자 서비스가 계속 실행되도록 유지합니다:
```bash
sudo loginctl enable-linger $USER
```

### 상태 확인 및 관리
```bash
# 타이머 등록 및 다음 실행 시간 확인
systemctl --user list-timers website-change.timer

# 수동으로 즉시 1회 실행 테스트
systemctl --user start website-change.service

# 실시간 서비스 로그 확인
journalctl --user -u website-change.service -f
```

---

## 로그 확인

- **파일 로그**: `app.log` (또는 `.env`의 `LOG_FILE`에 지정된 파일)
  ```bash
  tail -f app.log
  ```
- **systemd 저널 로그**:
  ```bash
  journalctl --user -u website-change.service -f
  ```
