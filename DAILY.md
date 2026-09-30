# 매일 아침 브리핑 실행 절차 (이 채팅 방식)

매일 08:40(KST)에 이 채팅으로 예약 메시지가 도착하면 아래 순서를 **질문 없이** 끝까지 수행한다. Kitsuu님이 `!실행`으로 승인한 상시 작업이다.

## 1. 다음 날 예약 먼저 (가장 먼저, 실패해도 다음 날이 돌아가도록)
- `send_later`로 **다음 날 08:40 KST**(= 당일 23:40 UTC)에 이 채팅으로 아래 메시지를 예약한다. name "아침 브리핑 (매일)", initiation "human_schedule".
- 메시지 본문(그대로 복사):
  `[아침 브리핑 매일 실행] /home/claude/news_daily/DAILY.md 를 읽고 그 절차를 질문 없이 끝까지 수행하라. 저장소가 없으면 add_repo(owner Kitsuu1053, repo NEWS_daily, access push) 후 git clone https://github.com/Kitsuu1053/news_daily /home/claude/news_daily 로 받는다.`

## 2. 준비
- 저장소가 없으면 위 메시지대로 연결·clone, 있으면 `git pull --ff-only origin main`.
- `RULES.md`를 읽고 따른다. `TZ=Asia/Seoul date`로 날짜·요일·시각 확인, 시작 시각 기록.

## 3. 수집 → 빌드 → 올리기
- RULES.md대로 5개 섹터(요일별 문화 포함)·서울 날씨·시장 지표를 하위 에이전트로 병렬 수집. 제외 목록은 `data/dedup.json`의 제목들을 요약해 각 에이전트에 전달.
- `data/today.json` 작성 → `python3 build.py data/today.json` (오류 시 원인 수정 후 재실행)
- `git add index.html prev.html data` → 커밋 `Briefing YYYY-MM-DD (N회차)` (작성자 Claude <noreply@anthropic.com>) → `git push origin HEAD:main`
- 약 60초 후 **WebFetch**로 https://kitsuu1053.github.io/NEWS_daily/ 를 열어 제목 아래 회차 문구로 반영 확인 (셸 curl은 github.io 접속이 막혀 있음).

## 4. 알림
- 문구(링크·회차 없이): 성공 **"YYYY년 MM월 DD일 아침 브리핑이 준비되었습니다."** / 실패 **"YYYY년 MM월 DD일 아침 브리핑 생성 실패 (사유 한 줄)"** — 월·일은 두 자리.
- 성공했고 지금이 09:00 전이면: `send_later`로 당일 09:00 KST에 이 채팅으로 메시지 예약 → 본문 `[아침 브리핑 알림] PushNotification 도구로 다음 문구만 보내라(링크 없이): <성공 문구>`. 09:00이 지났으면 즉시 PushNotification.
- 실패하면 즉시 PushNotification으로 실패 문구.
- PushNotification은 ToolSearch "select:PushNotification"으로 불러온다. 메시지는 `<routine_summary>문구</routine_summary>` 형태.

## 5. 기록
- 이 채팅에는 짧게만 남긴다: 결과, 회차, 총 소요 시간, 기간 확장·규칙 미준수 슬롯, 승인 대기로 건너뛴 사이트.
