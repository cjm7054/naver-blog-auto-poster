import urllib.request
import xml.etree.ElementTree as ET
import json
from typing import List, Dict


class TrendCrawler:
    """실시간 트렌드 및 핫이슈 수집기 (구글 트렌드, 네이버 뉴스 등)"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        }

    def get_google_trends(self, limit: int = 10) -> List[Dict]:
        """구글 트렌드 대한민국 실시간 급상승 검색어 및 관련 뉴스 추출"""
        url = "https://trends.google.co.kr/trending/rss?geo=KR"
        trends = []
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_data = resp.read()
            
            root = ET.fromstring(xml_data)
            items = root.findall(".//item")
            for item in items[:limit]:
                title = item.find("title").text if item.find("title") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                
                # HT:news_item 뉴스 헤드라인 파싱
                news_titles = []
                for news_node in item.findall("{https://trends.google.com/trends/trendingterms/daily}news_item"):
                    news_title = news_node.find("{https://trends.google.com/trends/trendingterms/daily}news_item_title")
                    if news_title is not None and news_title.text:
                        news_titles.append(news_title.text)

                trends.append({
                    "keyword": title,
                    "description": desc or " ".join(news_titles),
                    "news_headlines": news_titles,
                    "pub_date": pub_date
                })
        except Exception as e:
            print(f"[경고] 구글 트렌드 크롤링 실패: {e}")
        return trends

    def get_time_slot_trends(self, slot_name: str) -> Dict:
        """시간대(dawn, morning, lunch, evening)별 성격에 맞는 추천 키워드 및 트렌드 선택"""
        trends = self.get_google_trends(limit=10)
        if trends:
            # 첫 번째 또는 두 번째 트렌드 선택
            selected = trends[0]
            keyword = selected["keyword"]
            context = f"관련 헤드라인: {', '.join(selected['news_headlines'])}" if selected['news_headlines'] else selected['description']
            category = "실시간이슈/트렌드"
        else:
            # fallback 이슈
            fallbacks = {
                "dawn": ("밤사이 주요 경제·사회 소식 및 오늘 날씨 예보", "생활/날씨"),
                "morning": ("오늘 증시 개장 체크포인트 및 직장인 필수 모닝 브리핑", "경제/비즈니스"),
                "lunch": ("점심시간 화제! 직장인 추천 맛집 꿀팁 및 오후 집중력 높이는 스트레칭", "건강/라이프"),
                "evening": ("오늘 하루 주요 이슈 총정리 및 내일 꼭 알아둘 혜택", "시사/정보")
            }
            keyword, category = fallbacks.get(slot_name, ("오늘의 주요 실시간 트렌드 분석", "일반상식"))
            context = "최신 트렌드와 독자들의 높은 관심사"

        return {
            "slot": slot_name,
            "keyword": keyword,
            "category": category,
            "context": context
        }


if __name__ == "__main__":
    crawler = TrendCrawler()
    trends = crawler.get_google_trends(5)
    print(f"수집된 실시간 키워드 수: {len(trends)}")
    for t in trends:
        print(f"- {t['keyword']} : {t['news_headlines'][:2]}")
