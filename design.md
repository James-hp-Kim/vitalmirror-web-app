# VitalMirror Design Notes

작성일: 2026-04-25

## 유사 서비스 리서치

VitalMirror와 유사한 사이트/제품은 이미 존재한다. 공통점은 카메라 기반 영상에서 rPPG 또는 PPG 신호를 추출하고, HR, HRV, RR, 스트레스 또는 회복 지표를 보여준다는 점이다.

| 서비스 | 형태 | 참고할 점 | VitalMirror와의 차이 |
| --- | --- | --- | --- |
| [Binah.ai](https://www.binah.ai/) | B2B SDK / Health Data Platform | 35초 영상 스캔, 스마트폰/태블릿 카메라, HR/HRV/RR/스트레스/혈압 등 폭넓은 지표 | 의료/보험/기업 통합 지향. VitalMirror는 초기에 개인 웰니스 웹앱으로 좁히는 편이 좋음 |
| [NuraLogix Anura](https://nuralogix.ai/anura/) | 앱/SDK/텔레헬스 통합 | 30초 비디오 셀피, 활력징후와 건강 위험 평가, 모바일/데스크톱 지원 | 진단/리스크 평가 영역이 넓음. VitalMirror MVP는 진단 표현을 피하고 회복/스트레스 루틴 중심 |
| [FaceHeart](https://faceheart.com/) | FDA-cleared SDK / Web integration | 45~50초 얼굴 스캔, HR/RR/BP/SpO2/HRV/Stress, HTML5 웹 통합 옵션 | 규제 등급과 SDK 신뢰성이 강점. VitalMirror는 연구/프로토타입 단계임을 명확히 해야 함 |
| [Welltory](https://welltory.com/) | 소비자 앱 | HRV 기반 Stress/Energy/Recovery 해석, 쉬운 언어의 코칭과 추세 분석 | 손가락+카메라 PPG/웨어러블 중심. VitalMirror는 얼굴 기반 rPPG 경험을 차별점으로 삼을 수 있음 |

## 웹앱 방향

VitalMirror는 네이티브 앱보다 웹앱으로 먼저 발전시키는 것이 좋다.

- 사용자는 설치 없이 URL로 바로 진입할 수 있다.
- 브라우저 `getUserMedia()`로 카메라 접근이 가능하다.
- 데스크톱과 모바일을 동시에 검증하기 쉽다.
- 연구/데모/파일럿 배포 속도가 빠르다.
- 다만 실제 스마트폰 카메라 사용은 `https` 또는 `localhost` 환경이 필요하므로, 휴대폰 테스트용 배포/터널 환경을 준비해야 한다.

## 다음 디자인 목표

1. 첫 화면은 랜딩페이지가 아니라 바로 스캔 가능한 웹앱 화면으로 유지한다.
2. 스캔 중에는 얼굴 위치, 조명, 움직임, 남은 시간을 명확히 보여준다.
3. 결과는 의료 수치보다 `오늘의 부하`, `회복 여력`, `추천 행동` 중심으로 표현한다.
4. HR/HRV/RR 같은 세부 지표는 접을 수 있는 상세 영역으로 둔다.
5. 피드백 루프를 제품의 핵심 기능으로 둔다. 사용자가 결과가 맞는지 알려주면 이후 개인 기준선 보정에 쓰는 구조다.

## 추천 정보 구조

- Scan: 30초 카메라 스캔, 사진 분석 fallback
- Result: Mood, Stress Load, Recovery, 신뢰도
- Signal Quality: 밝기, 움직임, 얼굴 감지, rPPG 품질
- Coaching: 즉시 할 수 있는 1~3분 루틴
- Trend: 7일/30일 변화
- Feedback: 맞음/다름, 자가 보고 무드/불안, 메모
- Data Export: 연구/학습용 CSV

## 차별화 포인트

- “건강 진단”보다 “컨디션 미러”로 포지셔닝한다.
- 30초 스캔 후 과한 설명 대신 바로 실행 가능한 작은 행동을 제안한다.
- 개인 기준선과 추세를 강조한다. 단일 측정보다 반복 측정에서 가치가 커지는 구조가 좋다.
- rPPG 신호 품질을 숨기지 않는다. 품질이 낮으면 결과보다 재측정을 권한다.

## 구현 메모

- 현재 로컬 프로토타입은 Python 서버 + 정적 웹앱 구조다.
- 다음 단계에서 Vite/React 또는 Next.js 기반 PWA로 전환하면 화면 상태, 라우팅, 차트, 모바일 UX를 더 안정적으로 확장할 수 있다.
- 카메라 권한과 HTTPS 제약 때문에 실제 모바일 테스트는 배포 URL 또는 HTTPS 터널이 필요하다.
- 의료/진단 문구는 피하고 `wellness`, `stress load`, `recovery`, `reference only` 표현을 사용한다.

## Binah.ai 참고 방향

2026-04-25 기준 Binah.ai 홈은 `AI-powered health and wellness check software`, `35 seconds`, `smartphone or tablet camera`, `software solution`, `SDK`, `real-time health data`를 전면에 둔다. VitalMirror의 새 웹앱 디자인은 이를 참고하되 다음처럼 다르게 적용한다.

- Binah.ai의 B2B 플랫폼 신뢰감은 유지하되, VitalMirror는 개인이 바로 조작하는 웹앱 화면을 첫 화면에 둔다.
- 딥 블루, 화이트, 밝은 블루 계열을 사용해 헬스 데이터 플랫폼 느낌을 만든다.
- 제품 이미지는 실제 카메라 스캔 패널과 모바일 컨트롤 데크로 대체한다.
- 카피는 진단/리스크 판정보다 `컨디션`, `스트레스 부하`, `회복 여력`, `웰니스 참고용`으로 제한한다.
- 데스크톱에서는 폰 프레임으로 작동 흐름을 보여주고, 휴대폰에서는 `/phone` 주소로 직접 조작하는 구조를 둔다.
