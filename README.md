# 시장 체력 일간/주간/월간 점수표

12개 항목을 -2~+2로 평가하여 총 -24~+24점으로 표시하고 날짜/주간/월간 단위로 당시 시장 상태를 재구성합니다.

## 항목
M1 / M2 / RRP / TGA / Reserve Balances / 기업실적 / AI 투자 사이클 / 비트코인 사이클 / 미국 10년물 금리 / 달러지수(DXY 대용) / 외국인 코스피 순매수 / 시장심리(CNN+CoinMarketCap)

## 설치
1. 이 ZIP을 GitHub 저장소 루트에 압축 해제해 업로드합니다.
2. Settings → Pages → Source를 **GitHub Actions**로 선택합니다.
3. Actions에서 `Update market data`를 한 번 수동 실행합니다.
4. 매일 KST 08:00 자동 업데이트됩니다.

## 주의
M1/M2는 월간, Reserve Balances는 주간 등 발표주기가 다릅니다. 일간 화면은 해당 날짜에 이용 가능한 최신 관측값을 사용합니다. 기업실적/AI/외국인 수급은 `data/manual_overrides.json`에 수동 점수를 넣을 수 있습니다. API 실패 시 직전 성공값을 보존하도록 설계했습니다.
