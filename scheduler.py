import time
import schedule
from datetime import datetime
from config import POSTING_SCHEDULE, NAVER_BLOG_ID
from trend_crawler import TrendCrawler
from content_generator import ContentGenerator
from naver_poster import NaverPoster


def job_post_realtime_issue(slot_name: str):
    """새벽, 아침, 점심, 오후 실시간 이슈를 포스팅하는 주기적 작업"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 60)
    print(f"[{now_str}] [{slot_name.upper()} 타임] 실시간 트렌드 포스팅 작업을 시작합니다.")
    print("=" * 60)

    # 1. 트렌드 키워드 크롤링
    crawler = TrendCrawler()
    trend_info = crawler.get_time_slot_trends(slot_name)
    keyword = trend_info["keyword"]
    category = trend_info["category"]
    context = trend_info["context"]

    print(f"[트렌드 분석] 선택된 키워드: {keyword} ({category})")
    print(f"[배경 정보] {context}")

    # 2. 고품질 원고 AI 생성
    generator = ContentGenerator()
    post_data = generator.generate_post(keyword, category, context)
    print(f"[원고 생성 완료] 제목: {post_data['title']}")
    print(f"[본문 길이] 공백 포함 {len(post_data['content'])}자, 태그 {len(post_data['tags'])}개")

    # 3. 애드포스트 심사 기준 사전 검증
    from adpost_validator import AdPostValidator
    is_passed, issues, stats = AdPostValidator.validate(
        title=post_data["title"],
        content=post_data["content"],
        tags=post_data.get("tags", [])
    )

    print("-" * 50)
    print(f"[애드포스트 품질 검증 - {slot_name.upper()} 타임]")
    print(f" - 글자 수(공백 제외): {stats.get('char_count_no_space')}자")
    print(f" - 소제목(##) 개수: {stats.get('subheading_count')}개")
    print(f" - 태그 개수: {stats.get('tag_count')}개")

    if not is_passed:
        print("[검증 실패] 애드포스트 기준에 미달하여 실시간 글 포스팅을 보류합니다:")
        for issue in issues:
            print(f"  * {issue}")
        return

    print("[검증 통과] 품질 검증 완료! 네이버 블로그에 공식 공개 발행합니다.")
    print("-" * 50)

    # 4. 네이버 블로그에 포스팅
    poster = NaverPoster(blog_id=NAVER_BLOG_ID)
    try:
        poster.init_driver()
        if not poster.check_login_status():
            print("[경고] 로그인이 풀려있습니다. 자동 포스팅을 중단합니다.")
            return

        success = poster.post_article(
            title=post_data["title"],
            content=post_data["content"],
            tags=post_data.get("tags", []),
            publish=True
        )
        if success:
            print(f"[성공] [{slot_name.upper()} 타임] 실시간 글 발행 완료!")
    except Exception as e:
        print(f"[오류] 포스팅 작업 중 예외 발생: {e}")
    finally:
        poster.close()


def start_realtime_scheduler():
    """4타임 (06:30 새벽, 09:00 아침, 12:30 점심, 18:00 오후) 스케줄러 등록 및 루프 실행"""
    schedule.every().day.at(POSTING_SCHEDULE["dawn"]).do(job_post_realtime_issue, slot_name="dawn")
    schedule.every().day.at(POSTING_SCHEDULE["morning"]).do(job_post_realtime_issue, slot_name="morning")
    schedule.every().day.at(POSTING_SCHEDULE["lunch"]).do(job_post_realtime_issue, slot_name="lunch")
    schedule.every().day.at(POSTING_SCHEDULE["evening"]).do(job_post_realtime_issue, slot_name="evening")

    print("=" * 60)
    print(" [네이버 블로그 실시간 이슈 4타임 자동 포스팅 스케줄러 가동] ")
    print(f" - 대상 블로그: https://blog.naver.com/{NAVER_BLOG_ID}")
    print(f" - 새벽 타임: 매일 {POSTING_SCHEDULE['dawn']}")
    print(f" - 아침 타임: 매일 {POSTING_SCHEDULE['morning']}")
    print(f" - 점심 타임: 매일 {POSTING_SCHEDULE['lunch']}")
    print(f" - 오후 타임: 매일 {POSTING_SCHEDULE['evening']}")
    print("스케줄러가 백그라운드에서 동작 중입니다... (종료: Ctrl + C)")
    print("=" * 60)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    start_realtime_scheduler()
