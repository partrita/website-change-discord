# Website Change Discord Watcher

특정 웹사이트의 특정 영역을 감시하고, 변경이 감지되면 Discord 웹훅으로 알림을 보내는 도구입니다.

## 주요 기능
- CSS Selector를 이용한 정밀한 영역 감시
- **사이트별 개별 감시 주기 설정** (시간 단위)
- **systemd Timer 기반**의 효율적인 실행 (리눅스 서버 최적화)
- 안티 봇 방지 (User-Agent 랜덤화, Referer 위장, 지연 시간 적용)
- SQLite 기반의 이전 데이터 및 체크 시간 관리
- Discord 웹훅 알림 지원

---

## 설정 방법 (`config.yaml`)

감시할 사이트 목록과 각 사이트별 주기를 `config.yaml` 파일에서 설정합니다.

### 설정 항목

| 항목 | 설명 | 기본값 | 필수 여부 |
| :--- | :--- | :---: | :---: |
| `name` | 알림 시 표시될 사이트 이름 | - | O |
| `url` | 감시할 웹사이트의 전체 URL | - | O |
| `selector` | 감시할 영역의 CSS Selector | - | O |
| `interval_hours` | 체크 주기 (시간 단위) | 24 | X |

### 설정 예시
```yaml
targets:
  - name: "뉴스 사이트"
    url: "https://news.ycombinator.com"
    selector: ".titleline"
    interval_hours: 12  # 12시간마다 체크

  - name: "구글 공지사항"
    url: "https://www.google.com/"
    selector: "h1"
    interval_hours: 24  # 하루에 한 번 체크
```

---

## 설치 및 실행

### 1. 환경 변수 설정
`.env` 파일을 생성하고 Discord 웹훅 URL을 입력합니다.
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 2. 의존성 설치 및 실행
이 도구는 실행 시 한 번 스캔을 수행하고 종료됩니다. `uv`를 사용하여 실행할 수 있습니다.
```bash
uv run src/main.py
```

---

## 모니터링 및 로그 확인

프로젝트의 작동 상태를 확인하기 위해 두 가지 방법으로 로그를 제공합니다.

### 1. 로그 파일 확인 (`app.log`)
실행 시마다 상세한 작업 내용이 `app.log` 파일에 기록됩니다. 파일 크기가 커지면 자동으로 백업(Rotation) 처리됩니다.
```bash
# 실시간 로그 확인
tail -f app.log
```

**로그 내용 예시:**
- `[INFO] Starting scan...`: 스캔 시작
- `[INFO] Checking: [사이트명] ([URL])`: 사이트 체크 시작
- `[INFO] CHANGE DETECTED!`: 변동 사항 감지 및 디스코드 알림 발송
- `[INFO] Skipping: [사이트명] (Interval not reached)`: 아직 체크 주기가 되지 않아 건너뜀
- `[ERROR] ...`: 네트워크 오류 또는 설정 오류 발생 시 출력

### 2. 시스템디 로그 확인 (`journalctl`)
`systemd` 타이머에 의해 실행된 기록은 시스템 저널에서도 확인할 수 있습니다.
```bash
# 최근 실행 기록 및 실시간 모니터링
journalctl --user -u website-change.service -f
```

---

## 리눅스 서버에서 자동 실행 (systemd User Service)

리눅스 서버(Ubuntu, Debian 등)를 사용 중이라면, **systemd 사용자 서비스와 타이머**를 사용하여 주기적으로 자동 실행되도록 설정하는 것이 가장 권장됩니다. 이 방식은 루트(root) 권한 없이도 설정 가능하며 사용자별로 독립적으로 동작합니다.

### 1. 설정 파일 준비
프로젝트의 `systemd/` 디렉토리에 있는 설정 파일들을 사용자 폴더로 복사합니다.

```bash
mkdir -p ~/.config/systemd/user/
cp systemd/website-change.service ~/.config/systemd/user/
cp systemd/website-change.timer ~/.config/systemd/user/
```

### 2. 서비스 등록 및 시작
다음 명령어를 실행하여 타이머를 활성화합니다.

```bash
# systemd 설정 새로고침
systemctl --user daemon-reload

# 타이머 활성화 및 즉시 시작
systemctl --user enable --now website-change.timer
```

### 3. 로그아웃 후에도 실행 유지 (Linger 설정)
기본적으로 `systemd --user` 서비스는 사용자가 로그아웃하면 종료됩니다. 서버 부팅 시 자동으로 시작되고 로그아웃 후에도 서비스가 계속 실행되도록 하려면 다음 명령어를 실행해야 합니다.

```bash
sudo loginctl enable-linger $USER
```

### 4. 상태 확인 및 관리
```bash
# 타이머가 정상적으로 등록되었는지 확인 (다음 실행 시간 표시)
systemctl --user list-timers website-change.timer

# 로그 확인 (실행 결과 및 오류 확인)
journalctl --user -u website-change.service -f

# 수동으로 즉시 실행 테스트
systemctl --user start website-change.service
```

### 참고: 작동 원리
타이머는 매시간(`hourly`) 스크립트를 실행합니다. 스크립트 내부에서 각 사이트별로 설정된 `interval_hours`가 지났는지 확인하여, 주기가 된 사이트만 실제로 스캔을 수행합니다. 따라서 서버 자원을 매우 효율적으로 사용합니다.
