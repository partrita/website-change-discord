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

## 간편하게 사이트 추가하기 (`add_site`)

`config.yaml` 파일을 직접 수정하는 대신, 대화형 스크립트를 사용하여 새로운 사이트를 쉽게 추가할 수 있습니다.

```bash
# 사이트 추가 헬퍼 실행
uv run add_site
```

### 주요 기능
- **실시간 테스트**: 입력한 URL과 Selector가 올바른지 즉시 확인하고 추출된 텍스트를 보여줍니다.
- **자동 저장**: 테스트 결과가 만족스러우면 `config.yaml`에 자동으로 추가합니다.
- **중복 방지**: 이미 등록된 URL이 있는 경우 경고를 표시합니다.

---

## 설치 및 실행

### 1. 환경 변수 설정
`.env` 파일을 생성하고 Discord 웹훅 URL을 입력합니다.
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 2. 의존성 설치 및 실행
이 도구는 `uv`를 통해 간편하게 실행할 수 있습니다. 한 번의 스캔을 수행하고 종료됩니다.

```bash
# 동기화 및 실행 (최초 1회 권장)
uv sync

# 스캔 실행
uv run monitor
```

### 3. 데몬 모드로 실행
스크립트를 종료하지 않고 계속 실행하며, 설정 파일이 변경되면 즉시 스캔을 수행합니다.

```bash
# 데몬 모드로 실행
uv run monitor --daemon
```

---

## 모니터링 및 로그 확인

프로젝트의 작동 상태를 확인하기 위해 두 가지 방법으로 로그를 제공합니다.

### 1. 로그 파일 확인 (`app.log`)
실행 시마다 상세한 작업 내용이 `app.log` 파일에 기록됩니다.
```bash
# 실시간 로그 확인
tail -f app.log
```

### 2. 시스템디 로그 확인 (`journalctl`)
`systemd` 타이머에 의해 실행된 기록은 시스템 저널에서도 확인할 수 있습니다.
```bash
# 최근 실행 기록 및 실시간 모니터링
journalctl --user -u website-change.service -f
```

---

## 리눅스 서버에서 자동 실행 (systemd User Service)

리눅스 서버를 사용 중이라면, **systemd 사용자 서비스와 타이머**를 사용하는 것이 가장 권장됩니다.

### 1. 설정 파일 준비
프로젝트의 `systemd/` 디렉토리에 있는 설정 파일들을 사용자 폴더로 복사합니다.

```bash
mkdir -p ~/.config/systemd/user/
cp systemd/website-change.service ~/.config/systemd/user/
cp systemd/website-change.timer ~/.config/systemd/user/
cp systemd/website-change.path ~/.config/systemd/user/
```

### 2. 서비스 등록 및 시작
```bash
# systemd 설정 새로고침
systemctl --user daemon-reload

# 타이머 활성화 및 즉시 시작
systemctl --user enable --now website-change.timer

# (선택 사항) config.yaml 변경 시 즉시 실행되도록 설정
systemctl --user enable --now website-change.path
```

### 3. 로그아웃 후에도 실행 유지 (Linger 설정)
```bash
sudo loginctl enable-linger $USER
```

### 4. 상태 확인 및 관리
```bash
# 타이머가 정상적으로 등록되었는지 확인
systemctl --user list-timers website-change.timer

# 수동으로 즉시 실행 테스트
systemctl --user start website-change.service
```
