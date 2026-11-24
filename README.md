# 시장 체력 일간·주간·월간 점수표

## 자동화 구조
`GitHub Actions(매일 KST 08:00) → scripts/update_data.py → data/latest.json/history.json → GitHub Pages(index.html)`

## 24점 체계
12개 항목 × -2~+2 = -24~+24
- +9~+24 강한 확장
- +5~+8 우호
- +1~+4 개선 가능
- 0 중립
- -1~-4 주의
- -5~-8 긴축 우세
- -9~-24 위험

## 사용 방법
1. GitHub에 새 repository 생성
2. 이 폴더의 파일을 repository root에 업로드
3. Settings → Pages → Source를 GitHub Actions로 설정
4. Actions에서 `update-market-data`를 수동 1회 실행
5. 생성된 GitHub Pages 주소를 열면 됨

포트폴리오는 원 그래프를 제거하고 QQQ 30% / VOO 28% / SCHD 10% / BTC 12% / 현금 20% 텍스트로 복원했다.

## 데이터 원칙
안정적인 공개 일일 API가 없는 기업실적·AI 투자·KOSPI 외국인 수급은 임의 숫자를 생성하지 않고 `data/manual_overrides.json`에서 명시적으로 관리한다.
