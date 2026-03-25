# Website Change Discord Watcher

특정 웹사이트의 특정 영역을 감시하고, 변경이 감지되면 Discord 웹훅으로 알림을 보내는 도구입니다.

## 주요 기능
- CSS Selector를 이용한 정밀한 영역 감시
- 안티 봇 방지 (User-Agent 랜덤화, Referer 위장, 지연 시간 적용)
- SQLite 기반의 이전 데이터 관리
- Discord 웹훅 알림 지원

---

## 설정 방법 (`config.yaml`)

감시할 사이트 목록은 `config.yaml` 파일에서 설정합니다.

### 설정 항목

| 항목 | 설명 | 필수 여부 |
| :--- | :--- | :---: |
| `name` | 알림 시 표시될 사이트 이름 | O |
| `url` | 감시할 웹사이트의 전체 URL | O |
| `selector` | 감시할 영역의 CSS Selector | O |

### CSS Selector 사용 가이드 (핵심)

이 도구는 `BeautifulSoup`의 `select_one()` 메서드를 사용하여 데이터를 추출합니다. HTML 요소의 텍스트 내용이 변경되면 이를 감지합니다.

#### 1. ID로 찾기
ID는 페이지에서 유일하므로 가장 확실한 방법입니다. `#` 기호를 사용합니다.
- 예: `<div id="content">...</div>` -> `selector: "#content"`

#### 2. 클래스로 찾기
특정 클래스를 가진 요소를 찾을 때 사용합니다. `.` 기호를 사용합니다.
- 예: `<p class="article-body">...</p>` -> `selector: ".article-body"`

#### 3. 태그와 속성 조합
태그와 클래스, 또는 다른 속성을 조합하여 더 정밀하게 선택할 수 있습니다.
- 예: `<h1 class="title">...</h1>` -> `selector: "h1.title"`
- 예: `<div data-type="main">...</div>` -> `selector: "div[data-type='main']"`

#### 4. 계층 구조 (공백 사용)
특정 부모 요소 아래에 있는 자식 요소를 찾을 때 사용합니다.
- 예: `<div class="main"><span>찾을 내용</span></div>` -> `selector: ".main span"`

#### 팁: 개발자 도구 활용하기
1. 브라우저(Chrome 등)에서 감시할 영역을 마우스 우클릭 -> **검사(Inspect)** 클릭
2. 해당 요소가 강조되면 마우스 우클릭 -> **Copy** -> **Copy selector** 클릭
3. 복사된 값을 `selector` 항목에 붙여넣으세요. (단, 너무 복잡한 경로는 사이트 구조 변경 시 깨지기 쉬우므로 간단한 ID나 클래스 위주로 정리하는 것이 좋습니다.)

---

## 설치 및 실행

### 1. 환경 변수 설정
`.env` 파일을 생성하고 Discord 웹훅 URL을 입력합니다.
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 2. 의존성 설치 및 실행
`uv`를 사용하여 간편하게 실행할 수 있습니다.
```bash
uv run src/main.py
```

## 리눅스 서버에서 영구 실행하기 (systemd)

만약 서버를 사용 중이라면, 터미널을 꺼도 계속 돌아가도록 systemd 설정을 추천합니다.

1. 파일 생성: `sudo nano /etc/systemd/system/website-watcher.service`
2. 내용 입력 (경로 등은 실제 환경에 맞게 수정):

```ini
[Unit]
Description=Website Change Discord Watcher
After=network.target

[Service]
User=fkt
WorkingDirectory=/home/fkt/website-change-discord
ExecStart=/home/fkt/.local/bin/uv run src/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. 명령어 실행:

```bash
sudo systemctl daemon-reload
sudo systemctl enable website-watcher
sudo systemctl start website-watcher
```
