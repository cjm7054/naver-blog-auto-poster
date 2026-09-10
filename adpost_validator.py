import re
from typing import Dict, List, Tuple


class AdPostValidator:
    """네이버 애드포스트 심사 승인 요건 엄격 자동 검증기 (안전 승인 전용)"""

    # 금지어 및 네이버 스팸/저품질 유발 패턴 (애드포스트 심사 시 감점 요인)
    BANNED_WORDS = [
        "쿠팡 파트너스", "수수료를 제공받", "소정의 원고료", "제휴마케팅", 
        "일수", "대출상담", "불법", "성인", "도박", "카지노", "토토"
    ]

    @classmethod
    def validate(cls, title: str, content: str, tags: List[str] = None) -> Tuple[bool, List[str], Dict]:
        """
        포스팅 내용이 애드포스트 승인 기준에 부합하는지 6대 핵심 항목 엄격 검증
        Returns: (통과여부, 사유목록, 상세통계)
        """
        issues = []
        stats = {}

        # 1. 글자 수 검증 (공백 제외 1,200자 이상)
        clean_text = re.sub(r'[\s\r\n\t]+', '', content)
        char_count_no_space = len(clean_text)
        char_count_with_space = len(content)
        stats["char_count_no_space"] = char_count_no_space
        stats["char_count_with_space"] = char_count_with_space

        if char_count_no_space < 1200:
            issues.append(f"[글자 수 미달] 공백 제외 최소 1,200자 이상 필수 충족이어야 하지만 현재 {char_count_no_space}자입니다.")

        # 2. 제목 완성도 및 가독성 (10자 이상 60자 이하)
        title_len = len(title.strip())
        stats["title_len"] = title_len
        if title_len < 10:
            issues.append(f"[제목 길이 부족] 제목이 너무 짧습니다 ({title_len}자).")
        elif title_len > 65:
            issues.append(f"[제목 너무 김] 모바일 화면 잘림 위험 ({title_len}자).")

        # 3. 소제목(##) 및 구조적 가독성 (체류시간 유도 구조 - 최소 2개 이상)
        subheadings = re.findall(r'##\s+([^\n\r]+)', content)
        stats["subheading_count"] = len(subheadings)
        if len(subheadings) < 2:
            issues.append(f"[소제목 부족] 독자 체류시간 확보를 위해 소제목(##)이 최소 2개 이상 필요합니다. (현재: {len(subheadings)}개)")

        # 4. 금지어 및 제휴 링크 검출 (승인 전 절대 금지)
        found_banned = [w for w in cls.BANNED_WORDS if w in content or w in title]
        if found_banned:
            issues.append(f"[승인 감점 위험 키워드 발견]: {', '.join(found_banned)} (애드포스트 승인 전에는 제휴/광고 문구 배제 필수)")

        # 5. 해시태그 수 검증 (최소 3개 이상)
        tag_count = len(tags) if tags else 0
        stats["tag_count"] = tag_count
        if tag_count < 3:
            issues.append(f"[태그 부족] 검색 유입을 위한 태그가 최소 3개 이상 필요합니다. (현재: {tag_count}개)")

        # 6. Q&A 또는 체크리스트 포함 여부 (정보성 문서 가점 요인)
        has_qa = bool(re.search(r'(Q\.|\?|자주 묻는 질문|체크리스트|주의사항)', content))
        stats["has_qa_or_checklist"] = has_qa
        if not has_qa:
            issues.append("[정보성 보완 권장] Q&A나 핵심 체크리스트 단락이 포함되어야 합니다.")

        # 필수 결격 사유 체크
        critical_issues = [i for i in issues if "[글자 수 미달]" in i or "[승인 감점" in i or "[제목 길이" in i or "[소제목 부족]" in i or "[태그 부족]" in i]
        is_passed = len(critical_issues) == 0

        return is_passed, issues, stats
