import argparse
import sys
from run_approval_posts import generate_all_approval_posts, publish_pending_approval_post
from scheduler import start_realtime_scheduler, job_post_realtime_issue
from trend_crawler import TrendCrawler


def main():
    parser = argparse.ArgumentParser(description="네이버 블로그 애드포스트 승인 & 4타임 실시간 자동 포스터")
    parser.add_argument(
        "--mode",
        choices=["generate-approval", "publish-approval", "run-scheduler", "test-realtime", "show-trends"],
        default="generate-approval",
        help="실행할 작업 모드를 선택합니다."
    )
    parser.add_argument("--count", type=int, default=1, help="승인용 글 발행 개수 (기본값: 1)")
    parser.add_argument("--draft", action="store_true", help="발행 대신 임시저장으로 동작")

    args = parser.parse_args()

    if args.mode == "generate-approval":
        # 1. 30개 승인용 고품질 원고 일괄 생성
        generate_all_approval_posts()

    elif args.mode == "publish-approval":
        # 2. 승인용 글 발행
        publish_pending_approval_post(count=args.count, publish_now=not args.draft)

    elif args.mode == "run-scheduler":
        # 3. 4타임 실시간 스케줄러 가동 (새벽/아침/점심/오후)
        start_realtime_scheduler()

    elif args.mode == "test-realtime":
        # 4. 실시간 이슈 글 1회 즉시 테스트 실행
        job_post_realtime_issue("morning")

    elif args.mode == "show-trends":
        # 5. 현재 실시간 급상승 키워드 조회
        crawler = TrendCrawler()
        trends = crawler.get_google_trends(10)
        print("\n=== 현재 대한민국 실시간 급상승 트렌드 ===")
        for idx, t in enumerate(trends, 1):
            print(f"{idx:02d}. {t['keyword']} (관련 헤드라인: {', '.join(t['news_headlines'][:2])})")


if __name__ == "__main__":
    main()
