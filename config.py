import os
from pathlib import Path

# 기본 디렉터리 설정
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CHROME_PROFILE_DIR = BASE_DIR / "chrome_profile"
QUEUE_DIR = BASE_DIR / "posts_queue"

for d in [DATA_DIR, CHROME_PROFILE_DIR, QUEUE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 네이버 블로그 기본 계정 정보
NAVER_BLOG_ID = os.getenv("NAVER_BLOG_ID", "cjm7054")

# Gemini API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# 4타임 포스팅 스케줄 시간 (새벽, 아침, 점심, 오후)
POSTING_SCHEDULE = {
    "dawn": "06:30",       # 새벽: 출근길 / 밤사이 이슈 및 생활 정보
    "morning": "09:00",    # 아침: 오전 핫트렌드 및 경제/생활 이슈
    "lunch": "12:30",      # 점심: 점심시간 화제거리 / IT·문화 트렌드
    "evening": "18:00",    # 오후: 퇴근길 이슈 정리 및 저녁 관심사
}

# 애드포스트 승인용 검증된 주제 카테고리 (생활정보/IT/정부지원/건강)
APPROVAL_KEYWORDS = [
    {"topic": "2026 알뜰교통카드 K-패스 신청 방법 및 환급 혜택 총정리", "category": "생활정보"},
    {"topic": "스마트폰 배터리 수명 2배 늘리는 실전 충전 꿀팁 7가지", "category": "IT/모바일"},
    {"topic": "2026 청년 주거지원 정책 및 전월세 보증금 대출 자격 요건", "category": "정부지원"},
    {"topic": "카카오톡 용량 줄이기 및 캐시 삭제로 10GB 확보하는 법", "category": "IT/모바일"},
    {"topic": "건강검진 대상자 조회 및 연말 전 필수 체크리스트", "category": "건강/생활"},
    {"topic": "윈도우 11 PC 속도 빠르게 만드는 최적화 설정 가이드", "category": "IT/컴퓨터"},
    {"topic": "2026 근로장려금 정기 반기 신청 자격 및 지급일 계산법", "category": "정부지원"},
    {"topic": "해외여행 환전 수수료 0원 카드 비교 및 추천 (트래블로그/트래블월렛)", "category": "재테크/생활"},
    {"topic": "스팸 전화 차단 및 개인정보 유출 방지하는 두낫콜 등록 방법", "category": "생활정보"},
    {"topic": "구글 드라이브 용량 부족 해결 및 대용량 파일 정리 팁", "category": "IT/컴퓨터"},
    {"topic": "2026 연말정산 미리보기 및 절세 환급금 극대화 전략", "category": "재테크/생활"},
    {"topic": "넷플릭스 유튜브 프리미엄 가족 공유 및 할인 혜택 비교", "category": "IT/생활"},
    {"topic": "눈 피로 줄이는 모니터 블루라이트 차단 및 다크모드 설정법", "category": "건강/IT"},
    {"topic": "2026 출산 장려금 및 부모급여 신청 기준 총정리", "category": "정부지원"},
    {"topic": "집에서 쉽게 따라하는 거북목 일자목 교정 스트레칭 5선", "category": "건강/생활"},
    {"topic": "네이버페이 포인트 무료 적립 및 현금영수증 등록 가이드", "category": "재테크"},
    {"topic": "운전면허 적성검사 갱신 인터넷 신청 및 준비물 총정리", "category": "생활정보"},
    {"topic": "크롬 브라우저 속도 느려짐 해결하는 캐시 청소 및 확장 프로그램 정리", "category": "IT/컴퓨터"},
    {"topic": "국민연금 예상 수령액 조회 및 임의계속가입 활용 팁", "category": "재테크"},
    {"topic": "스마트폰 분실 시 원격 위치 추적 및 데이터 백업 잠금 방법", "category": "IT/모바일"},
    {"topic": "자동차세 연납 할인 신청 기간 및 위택스 납부 혜택", "category": "생활정보"},
    {"topic": "생체리듬을 회복하는 불면증 극복 수면 위생 루틴", "category": "건강/생활"},
    {"topic": "인터넷 속도 무료 측정 및 통신사 비대칭형 회선 확인법", "category": "IT/컴퓨터"},
    {"topic": "탄소중립포인트 가입하고 연간 최대 7만원 환급받는 법", "category": "정부지원"},
    {"topic": "에어컨 전기세 절약하는 냉방 인버터 가동 꿀팁", "category": "생활정보"},
    {"topic": "신용점수 올리는 가장 빠른 방법 5가지 (KCB, NICE)", "category": "재테크"},
    {"topic": "스마트폰 사진 고화질로 PC에 케이블 없이 무선 전송하기", "category": "IT/모바일"},
    {"topic": "주민등록등본 초본 인터넷 무료 발급 및 PDF 저장 방법 (정부24)", "category": "생활정보"},
    {"topic": "아침 공복에 마시는 미온수의 효능과 올바른 수분 섭취법", "category": "건강/생활"},
    {"topic": "내 계좌 한눈에 어카운트인포로 잠자는 휴면 예금 찾기", "category": "재테크"}
]
