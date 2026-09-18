import os
import json
import time
from pathlib import Path
from config import APPROVAL_KEYWORDS, QUEUE_DIR, NAVER_BLOG_ID
from content_generator import ContentGenerator
from naver_poster import NaverPoster


def generate_all_approval_posts():
    """애드포스트 승인용 30개 고품질 원고를 일괄 생성하여 로컬 큐(JSON)로 저장"""
    generator = ContentGenerator()
    print("=" * 60)
    print(f"[시작] 네이버 블로그({NAVER_BLOG_ID}) 애드포스트 승인용 30개 원고 생성을 시작합니다.")
    print("=" * 60)

    for idx, item in enumerate(APPROVAL_KEYWORDS, 1):
        file_path = QUEUE_DIR / f"approval_post_{idx:02d}.json"
        if file_path.exists():
            print(f"[{idx:02d}/30] 이미 생성된 원고가 존재하여 건너뜁니다: {item['topic']}")
            continue

        print(f"[{idx:02d}/30] 원고 작성 중: {item['topic']} ({item['category']})")
        post_data = generator.generate_post(item["topic"], item["category"])
        post_data["id"] = idx
        post_data["status"] = "pending"  # pending, published

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(post_data, f, ensure_ascii=False, indent=2)

        print(f"     => 완료! 글자 수: {len(post_data['content'])}자, 태그: {len(post_data['tags'])}개")
        time.sleep(0.5)

    print("\n[완료] 30개 승인용 원고 작성이 모두 완료되어 posts_queue/ 폴더에 저장되었습니다!")


def publish_pending_approval_post(count: int = 1, publish_now: bool = True):
    """대기 중인 승인용 글 중 count개 만큼 순차 발행"""
    files = sorted(list(QUEUE_DIR.glob("approval_post_*.json")))
    pending_files = []

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                if data.get("status") == "pending":
                    pending_files.append((f, data))
        except Exception:
            continue

    if not pending_files:
        print("[안내] 대기 중인 승인용 원고가 없습니다. 먼저 원고를 생성하세요.")
        return

    print(f"\n[발행 대상] 현재 대기 중인 원고 {len(pending_files)}개 중 {min(count, len(pending_files))}개를 포스팅합니다.")
    
    poster = NaverPoster()
    poster.init_driver()

    if not poster.check_login_status():
        print("[경고] 네이버 로그인이 필요합니다.")
        login_success = poster.wait_for_user_manual_login(180)
        if not login_success:
            poster.close()
            return

    published_count = 0
    for file_path, data in pending_files[:count]:
        print(f"\n[포스팅 진행] ({data['id']}/30) {data['title']}")

        # 1. 애드포스트 심사 기준 자동 검증
        from adpost_validator import AdPostValidator
        is_passed, issues, stats = AdPostValidator.validate(
            title=data["title"],
            content=data["content"],
            tags=data.get("tags", [])
        )

        print("-" * 50)
        print(f"[애드포스트 사전 품질 검증 결과]")
        print(f" - 글자 수(공백 제외): {stats.get('char_count_no_space')}자 (기준: 1,200자 이상)")
        print(f" - 소제목(##) 개수: {stats.get('subheading_count')}개")
        print(f" - 태그 개수: {stats.get('tag_count')}개")
        print(f" - 정보성(Q&A/체크리스트): {'포함' if stats.get('has_qa_or_checklist') else '미포함'}")

        if not is_passed:
            print("[검증 실패] 애드포스트 승인 기준에 미달하여 포스팅을 중단합니다:")
            for issue in issues:
                print(f"  * {issue}")
            continue

        print("[검증 통과] 애드포스트 승인 최적화 검증 완료! 블로그에 즉시 공개 발행합니다.")
        print("-" * 50)

        # 2. 블로그에 실제 공개 발행 (Publish)
        success = poster.post_article(
            title=data["title"],
            content=data["content"],
            tags=data.get("tags", []),
            publish=True
        )
        if success:
            data["status"] = "published"
            data["published_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            data["adpost_validated"] = True
            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
            published_count += 1
            time.sleep(5)
        else:
            print("[실패] 포스팅 실패로 다음 글로 넘어가지 않습니다.")
            break

    poster.close()
    print(f"\n[완료] 총 {published_count}개의 글이 네이버 블로그에 포스팅되었습니다.")


if __name__ == "__main__":
    import sys
    # 1. 30개 원고 생성
    generate_all_approval_posts()
    
    # 인자로 run이 넘어오면 1개 테스트 포스팅
    if len(sys.argv) > 1 and sys.argv[1] == "--post":
        publish_pending_approval_post(count=1, publish_now=False)
