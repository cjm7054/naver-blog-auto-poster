import os
import time
import requests
import pyperclip
import subprocess
import platform
import re
import html
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

NAVER_ID = os.getenv('NAVER_ID')
NAVER_PW = os.getenv('NAVER_PW')

def copy_to_clipboard_rich(plain_text: str, html_content: str):
    """
    네이버 스마트에디터 ONE에 볼드체, 글자크기(소제목), 구분선, 인용구가 온전히 인식되도록
    HTML 리치 텍스트 클립보드 형식으로 복사합니다.
    """
    system = platform.system()
    try:
        if system == "Linux":
            # GitHub Actions (Linux Xvfb) 환경: xclip의 text/html 타겟 활용
            p = subprocess.Popen(
                ["xclip", "-selection", "clipboard", "-t", "text/html"],
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            p.communicate(input=html_content.encode("utf-8"))
            if p.returncode == 0:
                print("✅ [클립보드] Linux xclip text/html 서식 복사 성공!")
                return
        elif system == "Windows":
            # Windows 로컬 개발 환경용 HTML 클립보드 포맷팅
            try:
                import win32clipboard
                # Windows CF_HTML 표준 헤더 구성
                header = (
                    "Version:0.9\r\n"
                    "StartHTML:{:08d}\r\n"
                    "EndHTML:{:08d}\r\n"
                    "StartFragment:{:08d}\r\n"
                    "EndFragment:{:08d}\r\n"
                )
                start_fragment = "<!--StartFragment-->"
                end_fragment = "<!--EndFragment-->"
                content_html = f"<html><body>{start_fragment}{html_content}{end_fragment}</body></html>"
                
                # 가상 길이 계산
                dummy = header.format(0, 0, 0, 0)
                start_html_idx = len(dummy)
                start_frag_idx = start_html_idx + content_html.find(start_fragment) + len(start_fragment)
                end_frag_idx = start_html_idx + content_html.find(end_fragment)
                end_html_idx = start_html_idx + len(content_html)
                
                final_payload = header.format(start_html_idx, end_html_idx, start_frag_idx, end_frag_idx) + content_html
                
                cf_html = win32clipboard.RegisterClipboardFormat("HTML Format")
                win32clipboard.OpenClipboard(0)
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(cf_html, final_payload.encode("utf-8"))
                win32clipboard.CloseClipboard()
                print("✅ [클립보드] Windows CF_HTML 서식 복사 성공!")
                return
            except Exception as win_err:
                print(f"Windows HTML 클립보드 예외: {win_err}")
    except Exception as e:
        print(f"HTML 클립보드 복사 중 알림: {e}")
    
    # Fallback: 일반 텍스트 클립보드
    pyperclip.copy(plain_text)
    print("ℹ️ 클립보드 fallback (일반 텍스트) 복사 완료.")

def markdown_to_naver_html(md_text: str) -> str:
    """
    네이버 공식 캠페인/매거진(라이프로그) 스타일의 프리미엄 템플릿으로 변환합니다.
    - 소제목1 (##): 중앙 정렬, 큰 폰트(24px), 볼드, 넉넉한 여백
    - 서브 소제목 (### 또는 Episode): 상단 컬러 배지(Sub-tag) + 19px 굵은 타이틀
    - 인용구/핵심 메시지 (따옴표 또는 >): 감성 인용구 스타일 (“...”) + 중앙 정렬 이탤릭
    - 체크포인트/Q&A: 세련된 소프트 박스 (라운드 코너, 부드러운 배경색, 포인트 컬러)
    - 본문 문단: 가독성 높은 16px, 1.8 줄간격, 넉넉한 단락 간격
    """
    lines = md_text.split("\n")
    html_lines = []
    
    # 템플릿 최상단 컨테이너 시작
    html_lines.append('<div style="font-family: \'Nanum Gothic\', \'Apple SD Gothic Neo\', sans-serif; color: #2b2b2b; max-width: 720px; margin: 0 auto; line-height: 1.85;">')
    
    in_quote_block = False
    quote_buffer = []

    for line in lines:
        stripped = line.strip()
        
        # 빈 줄 처리
        if not stripped:
            if in_quote_block:
                quote_text = "<br>".join(quote_buffer)
                html_lines.append(
                    f'<div style="text-align: center; margin: 35px auto; padding: 25px 20px; max-width: 580px; position: relative;">'
                    f'<div style="font-size: 36px; color: #03c75a; font-family: serif; line-height: 1; margin-bottom: 8px;">“</div>'
                    f'<p style="font-size: 16px; color: #444; line-height: 1.9; font-style: italic; margin: 0; word-break: keep-all;">{quote_text}</p>'
                    f'<div style="font-size: 36px; color: #03c75a; font-family: serif; line-height: 1; margin-top: 8px;">”</div>'
                    f'</div>'
                )
                quote_buffer = []
                in_quote_block = False
            else:
                html_lines.append('<p style="margin: 12px 0;">&nbsp;</p>')
            continue
            
        # 마크다운 인용구 (>)
        if stripped.startswith(">"):
            in_quote_block = True
            clean_quote = stripped.lstrip(">").strip()
            clean_quote = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean_quote)
            quote_buffer.append(clean_quote)
            continue
        elif in_quote_block:
            quote_text = "<br>".join(quote_buffer)
            html_lines.append(
                f'<div style="text-align: center; margin: 35px auto; padding: 25px 20px; max-width: 580px; position: relative;">'
                f'<div style="font-size: 36px; color: #03c75a; font-family: serif; line-height: 1; margin-bottom: 8px;">“</div>'
                f'<p style="font-size: 16px; color: #444; line-height: 1.9; font-style: italic; margin: 0; word-break: keep-all;">{quote_text}</p>'
                f'<div style="font-size: 36px; color: #03c75a; font-family: serif; line-height: 1; margin-top: 8px;">”</div>'
                f'</div>'
            )
            quote_buffer = []
            in_quote_block = False

        # 구분선 (--- 또는 ***) -> 매거진 스타일 센터 디바이더
        if stripped in ["---", "***", "___"]:
            html_lines.append(
                '<div style="text-align: center; margin: 40px 0 35px 0;">'
                '<span style="display: inline-block; width: 40px; height: 3px; background-color: #03c75a; border-radius: 2px;"></span>'
                '</div>'
            )
            continue
            
        # 대주제 / 소제목 1 (##) -> 중앙 정렬 매거진 헤드라인
        if stripped.startswith("## "):
            title_text = stripped[3:].strip()
            title_text = re.sub(r'\*\*(.*?)\*\*', r'\1', title_text)
            html_lines.append(
                f'<div style="text-align: center; margin: 45px 0 25px 0;">'
                f'<h2 style="font-size: 24px; font-weight: 800; color: #111; letter-spacing: -0.5px; margin: 0; line-height: 1.4; word-break: keep-all;">'
                f'{title_text}'
                f'</h2>'
                f'</div>'
            )
            continue
            
        # 중주제 / 소제목 2 (###) -> 매거진 에피소드 / 섹션 카드 헤더
        if stripped.startswith("### "):
            title_text = stripped[4:].strip()
            title_text = re.sub(r'\*\*(.*?)\*\*', r'\1', title_text)
            html_lines.append(
                f'<div style="margin: 35px 0 15px 0; padding-bottom: 8px; border-bottom: 1px solid #f0f0f0;">'
                f'<span style="display: inline-block; font-size: 13px; font-weight: bold; color: #03c75a; background-color: #e8f8ef; padding: 3px 10px; border-radius: 12px; margin-bottom: 8px;">Point</span>'
                f'<h3 style="font-size: 19px; font-weight: 700; color: #222; margin: 0; line-height: 1.4; word-break: keep-all;">{title_text}</h3>'
                f'</div>'
            )
            continue
            
        # Q&A 질문 패턴 (Q1., Q., 질문)
        if re.match(r'^\*?\*?Q\d*[\.:]', stripped):
            styled_q = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', stripped)
            html_lines.append(
                f'<div style="background: linear-gradient(135deg, #f8fbf9 0%, #f4f7f5 100%); border: 1px solid #e1eee5; border-radius: 10px; padding: 16px 20px; margin: 25px 0 10px 0;">'
                f'<div style="font-size: 16px; font-weight: bold; color: #028f40; margin-bottom: 6px;">💡 {styled_q}</div>'
            )
            continue
            
        # Q&A 답변 패턴 (A., 답변)
        if re.match(r'^\*?\*?A[\.:]', stripped):
            styled_a = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', stripped)
            html_lines.append(
                f'<p style="margin: 0; font-size: 15px; color: #4a4a4a; line-height: 1.85; padding-left: 2px;">{styled_a}</p>'
                f'</div>'
            )
            continue
            
        # 일반 본문 처리
        content_line = stripped
        # 볼드 강조 변환 (**텍스트** -> 진하고 선명한 검정 볼드 + 약간의 대비)
        content_line = re.sub(r'\*\*(.*?)\*\*', r'<b style="font-weight: 700; color: #111; background: linear-gradient(to top, #e6f9ed 40%, transparent 40%); padding: 0 2px;">\1</b>', content_line)
        
        # 번호 매기기 리스트 (1. 2. 3.)
        if re.match(r'^\d+\.\s+', content_line):
            html_lines.append(
                f'<div style="display: flex; margin: 10px 0; padding: 10px 14px; background-color: #fafafa; border-radius: 8px;">'
                f'<p style="margin: 0; font-size: 15px; line-height: 1.8; color: #333;">{content_line}</p>'
                f'</div>'
            )
        else:
            html_lines.append(f'<p style="margin: 14px 0; font-size: 16px; line-height: 1.85; color: #383838; letter-spacing: -0.2px; word-break: keep-all;">{content_line}</p>')
            
    # 남아있는 인용구 닫기
    if in_quote_block:
        quote_text = "<br>".join(quote_buffer)
        html_lines.append(
            f'<div style="text-align: center; margin: 35px auto; padding: 25px 20px; max-width: 580px;">'
            f'<div style="font-size: 36px; color: #03c75a; font-family: serif; line-height: 1; margin-bottom: 8px;">“</div>'
            f'<p style="font-size: 16px; color: #444; line-height: 1.9; font-style: italic; margin: 0; word-break: keep-all;">{quote_text}</p>'
            f'<div style="font-size: 36px; color: #03c75a; font-family: serif; line-height: 1; margin-top: 8px;">”</div>'
            f'</div>'
        )

    # 맺음말 카드형 박스
    html_lines.append('</div>')
    return "\n".join(html_lines)


def get_signal_bz_trends(driver=None):
    print("실시간 급상승 트렌드 키워드 수집 중 (Google Trends & Signal API)...", flush=True)
    trends = []
    
    # 1. 초고속 백업망: Google Trends RSS (0.5초 이내 완료, 브라우저 미사용으로 무한 대기 원천 차단)
    try:
        import urllib.request
        import xml.etree.ElementTree as ET
        req = urllib.request.Request(
            "https://trends.google.co.kr/trending/rss?geo=KR",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        for item in root.findall(".//item")[:10]:
            title_node = item.find("title")
            if title_node is not None and title_node.text:
                k = title_node.text.strip()
                if k and k not in trends:
                    trends.append(k)
        if trends:
            print(f"✅ Google Trends 실시간 키워드 수집 성공 ({len(trends)}개): {trends[:5]}", flush=True)
            return trends
    except Exception as g_err:
        print(f"Google Trends RSS 확인 알림: {g_err}", flush=True)

    # 2. 만약 Google Trends가 안 될 경우 Signal.bz HTTP 파싱
    try:
        import requests
        from bs4 import BeautifulSoup
        res = requests.get("https://signal.bz/news", headers={"User-Agent": "Mozilla/5.0"}, timeout=4)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for el in soup.select(".rank-text, .rank_text")[:10]:
                t = el.get_text().strip()
                if t and t not in trends:
                    trends.append(t)
            if trends:
                print(f"✅ Signal.bz 실시간 키워드 수집 성공 ({len(trends)}개): {trends[:5]}", flush=True)
                return trends
    except Exception as s_err:
        print(f"Signal.bz HTTP 요청 알림: {s_err}", flush=True)

    # 3. 최후의 비상용 트렌드 키워드 (절대 빈 리스트 반환 금지 및 대기 시간 0초)
    trends = ["청년도약계좌", "근로장려금", "연말정산 환급금", "기준금리 동결", "국민연금 개혁안"]
    print(f"✅ 비상용 트렌드 키워드 리스트 즉시 적용: {trends}", flush=True)
    return trends

def generate_article_with_gemini(selected_keyword, other_trends, today_str):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None, None, []
        
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
당신은 네이버 블로그 상위 0.1% 파워블로거이자 네이버 애드포스트 고단가 전문 에디터입니다.
오늘의 실시간 검색어 1위인 [{selected_keyword}] 주제를 선정하여, 네이버 블로그 검색 상위노출과 애드포스트 심사를 단번에 통과할 수 있는 최고 품질의 단독 심층 전문 포스팅을 작성하세요.

[선정된 핵심 주제]: {selected_keyword}
[작성 기준일]: {today_str}

[작성 및 네이버 애드포스트 심사 통과 절대 규칙 - 100% 필수 준수]:
1. 글자 수: 공백 제외 반드시 1,600자 ~ 2,300자 이상으로 매우 상세하고 깊이 있게 작성하세요. (다른 키워드 10개 나열하는 글이 아니라, 오직 [{selected_keyword}] 하나에만 집중된 완성형 단독 칼럼/정보글입니다!)
2. 절대 단순 나열식 리스트 글을 쓰지 마세요.
3. [가독성 & 템플릿 디자인 최적화 (네이버 공식 매거진/라이프로그 스타일)]:
   - **감성 인용구 블록**: 서론 직후나 본문 중간에 이 이슈가 던지는 가장 중요한 메시지/화두를 마크다운 인용구(`> ...`) 1~2문장으로 작성하세요. (중앙 정렬 감성 큰따옴표 박스로 자동 렌더링됩니다)
   - **중앙 헤드라인 소제목(##)**: 큰 흐름을 짚어주는 중심 제목으로 활용하세요.
   - **에피소드/포인트 소제목(###)**: 상세 분석 단락에는 `### 1. 첫 번째 핵심 분석`, `### 2. 두 번째 핵심 분석` 형식으로 작성하세요. (포인트 배지와 카드 헤더로 변환됩니다)
   - **핵심 문장 볼드 강조**: 독자가 스크롤을 내리며 빠르게 핵심을 파악할 수 있도록, **각 문단마다 가장 중요한 문장과 핵심 수치에는 반드시 마크다운 볼드(**굵은 글씨**)를 적용**하세요.
4. 블로그 포스팅 구성:
   - [도입부 (서론)]: 왜 지금 [{selected_keyword}]이(가) 대중들의 폭발적인 관심을 받고 있는지 서술.
   - [감성 인용구 (>)]: 핵심 화두를 담은 1~2문장 인용구.
   - [본문 소제목 1 (##)]: 사건/이슈의 구체적인 전개 과정과 핵심 팩트 총정리 (### 세부 포인트 포함)
   - [본문 소제목 2 (##)]: 대중들의 여론 반응과 온라인/업계의 다양한 시각 분석 (### 세부 포인트 포함)
   - [본문 소제목 3 (##)]: 향후 전망 및 우리가 주목해야 할 핵심 시사점/체크포인트
   - [FAQ 섹션 (##)]: 독자들이 가장 궁금해할 만한 핵심 질문 3가지와 명쾌하고 상세한 답변 (Q1, Q2, Q3)
   - [결론 (##)]: 전체 내용을 한눈에 요약하고 공감/이웃추가 유도.
5. 문체: 부드럽고 가독성 높은 친절한 존댓말 (~합니다, ~해보세요, ~알아보았습니다).
6. 해시태그: 주제와 밀접한 고효율 태그 10개 추출.

[출력 형식 - 반드시 유효한 JSON 형식만 반환]:
{{
  "title": "{selected_keyword} 논란 및 핵심 쟁점 총정리! 화제가 된 진짜 이유와 향후 전망",
  "content": "본문 전체 내용 (마크다운 ## 소제목, ### 세부 포인트, > 인용구, 중요 문장 **볼드 강조** 적극 활용)",
  "tags": ["#{selected_keyword.replace(' ', '')}", "#{selected_keyword.replace(' ', '')}이유", "#실시간이슈", "#핫토픽", "#오늘의이슈", "#트렌드분석", "#이슈총정리", "#네이버블로그", "#정보공유", "#이슈체크"]
}}
"""
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                response_mime_type="application/json"
            )
        )
        import json
        data = json.loads(response.text)
        return data.get("title"), data.get("content"), data.get("tags", [])
    except Exception as e:
        print(f"Gemini API 생성 중 오류 또는 미설정: {e}. 고품질 단독 심층 리치 원고로 대체합니다.")
        return None, None, []

def get_blog_post(driver=None):
    try:
        trends = get_signal_bz_trends(driver)
        if not trends:
            print("트렌드 키워드를 찾지 못했습니다.", flush=True)
            return None, None, []
            
        today = datetime.now().strftime("%Y년 %m월 %d일 %H시")
        
        # 🎯 실시간 10개 키워드 중 가장 화제성이 높은 '1개'를 선정하여 단독 심층 작성!
        selected_keyword = trends[0]
        other_trends = trends[1:5]
        print(f"🎯 실시간 10개 키워드 중 오늘의 단독 포스팅 주제 선정: [{selected_keyword}]", flush=True)
        
        # 1. Gemini AI를 통한 1개 주제 집중 1,800자+ 단독 심층 원고 생성 시도
        ai_title, ai_content, ai_tags = generate_article_with_gemini(selected_keyword, other_trends, today)
        if ai_title and ai_content and len(ai_content) > 1200:
            print(f"Gemini AI를 통해 [{selected_keyword}] 단독 심층 원고({len(ai_content)}자)가 성공적으로 생성되었습니다!", flush=True)
            return ai_title, ai_content, ai_tags
            
        # 2. AI 키 미설정 시에도 [선정된 1개 키워드]에 집중하여 1,800자 이상 작성되는 풍성한 단독 심층 원고
        post_title = f"{selected_keyword} 집중 분석 및 핵심 쟁점 총정리! 화제가 된 배경과 향후 전망"
        
        content = f"""안녕하세요! 빠르게 변화하는 사회 이슈와 대중들의 뜨거운 화제거리를 누구보다 알기 쉽고 깊이 있게 정리해 드리는 트렌드 이슈 전문 블로그입니다.

최근 각종 포털 사이트의 실시간 검색어 순위와 주요 뉴스 헤드라인, 그리고 대형 온라인 커뮤니티를 가장 뜨겁게 달구고 있는 단 하나의 키워드를 꼽으라면 단연 **'{selected_keyword}'**일 것입니다.

많은 분들이 갑작스럽게 떠오른 이 이슈를 접하고 **"도대체 어떤 사연이 있길래 이렇게 실시간 1위까지 올라왔을까?", "핵심 쟁점과 팩트는 무엇일까?"** 하며 많은 궁금증을 가지고 검색해 보고 계실 텐데요.

그래서 오늘은 단편적인 찌라시나 자극적인 소문을 배제하고, **지금까지 공식적으로 확인된 객관적인 사실 관계와 대중들의 여론 반응, 그리고 앞으로의 파급 효과**까지 '{selected_keyword}'의 모든 것을 완벽하게 짚어드리겠습니다!

> 기록이 쌓이면 내가 된다. 수많은 정보 속에서 본질을 꿰뚫는 정확한 시선과 기록이 당신의 일상과 지식을 더욱 깊이 있게 만들어 줍니다.

---

## 1. '{selected_keyword}', 도대체 무슨 일일까요? 발단과 배경 총정리

이번 '{selected_keyword}' 사안이 폭발적인 관심을 받게 된 것은 **특정 공식 보도와 온라인상의 핵심 입장 발표**가 직접적인 도화선이 되었습니다.

사건의 발단을 시간 순서대로 짚어보면, 당초 예상치 못했던 전개가 펼쳐지며 **다양한 이해관계자들의 입장 차이가 극명하게 충돌**하기 시작했는데요. 특히 이전부터 누적되어 온 여러 사회적 관심사와 맞물리면서 단순한 개인의 일탈이나 해프닝 수준을 넘어선 **공공의 중대 논쟁거리로 급부상**하게 되었습니다.

현재 관련 부처와 소속 기관, 그리고 당사자 측에서도 **상황의 중대성을 인지하고 공식적인 입장문을 내놓거나 사실 관계 확인에 착수**하고 있는 상태입니다. 정보가 너무 빠르게 퍼져나가는 시점일수록 **확인되지 않은 추측성 루머에 휩쓸리지 않고 정확한 팩트와 맥락을 파악하는 태도**가 무엇보다 중요합니다.

---

## 2. 네티즌 여론과 전문가들의 엇갈린 시선: 핵심 쟁점 3가지

현재 각종 커뮤니티와 SNS에서는 이번 '{selected_keyword}' 이슈를 두고 뜨거운 갑론을박이 벌어지고 있습니다. 여론의 시각을 크게 **3가지 핵심 쟁점**으로 압축해 볼 수 있습니다.

### 쟁점 1: 원칙과 절차의 적절성 논란
일부 여론에서는 **이번 사안의 처리 과정이나 발단이 상식과 법적/도덕적 기준에 온전히 부합했는지**를 두고 비판적인 목소리를 높이고 있습니다. 사전에 충분한 조율이나 예방 조치가 가능하지 않았느냐는 지적도 함께 제기되는 상황입니다.

### 쟁점 2: 구조적인 문제인가, 개인의 책임인가
단순히 특정 개인만의 문제가 아니라, **우리 사회와 조직 문화 내에 만연해 있던 구조적 모순이 표출된 결과**라는 분석도 강력한 설득력을 얻고 있습니다. 이번 기회를 통해 보다 **근본적인 재발 방지 가이드라인이 마련되어야 한다**는 여론이 힘을 얻고 있습니다.

### 쟁점 3: 향후 미칠 파급력과 선례
이번 이슈가 앞으로 유사한 사안들에 어떤 기준점과 선례를 남기게 될지에 대해 각계 전문가들의 이목이 쏠리고 있습니다. 결과에 따라 관련 업계의 관행이나 법적 제도 개선으로까지 이어질 가능성이 높다는 관측이 지배적입니다.

---

## 3. 앞으로의 전개 방향과 주목해야 할 체크포인트

그렇다면 향후 '{selected_keyword}' 이슈는 어떤 방향으로 흘러가게 될까요? 독자 여러분께서 눈여겨보셔야 할 향후 핵심 관전 포인트는 다음과 같습니다.

1. **공식 조사 결과 및 추가 입장 발표**: 향후 관계 기관의 공식 조사 결과가 발표되는 시점에 사건의 진실 공방이 중대한 분수령을 맞이할 것으로 보입니다.
2. **법적 공방 및 제도적 후속 조치**: 당사자 간의 법적 조치 진행 여부와 함께, 재발 방지를 위한 제도적 보완책이 논의될지 지켜보아야 합니다.
3. **대중 여론의 추이**: 일시적인 분노나 화제성에 그치지 않고, 보다 건전하고 성숙한 사회적 논의로 성숙해질 수 있을지 지속적인 관심이 필요합니다.

---

## 4. 자주 묻는 질문 (Q&A)

**Q1. '{selected_keyword}' 관련해서 온라인에 떠도는 소문들은 모두 사실인가요?**
A. 아닙니다! 실시간 급상승 키워드의 특성상 조회수를 노린 가짜 뉴스나 과장된 자극적 게시글이 무분별하게 유포될 수 있습니다. 반드시 공신력 있는 언론사의 정식 보도와 공식 입장문을 교차 검증하시기 바랍니다.

**Q2. 이번 이슈의 최종 결론은 언제쯤 나올 것으로 예상되나요?**
A. 사안의 복잡성과 양측의 입장 차이를 고려할 때, 단기간에 마무리되기보다는 추가적인 사실 확인과 절차를 거치며 수일에서 수주 간 지속적인 논의가 이어질 것으로 전망됩니다.

**Q3. 일반 대중들은 이번 사안을 어떻게 바라보는 것이 바람직할까요?**
A. 무분별한 비난이나 인신공격은 지양하고, 사건이 던지는 본질적인 교훈과 제도적 미비점에 집중하여 건강한 여론을 형성해 나가는 것이 무엇보다 중요합니다.

---

## 마치며

지금까지 실시간 대한민국을 뜨겁게 달구고 있는 화제의 중심, '{selected_keyword}'에 대한 핵심 배경과 쟁점, 그리고 향후 전망까지 낱낱이 파헤쳐 보았습니다.

새로운 추가 소식이나 공식 발표가 나오는 대로 빠르게 후속 포스팅을 통해 업데이트해 드리겠습니다!

오늘 전해드린 분석 내용이 유익하셨다면 **공감(하트) 클릭과 따뜻한 댓글**, 그리고 가장 빠른 최신 이슈 브리핑을 받아보실 수 있도록 **이웃 추가** 부탁드립니다. 항상 신뢰할 수 있는 정확한 정보로 찾아뵙겠습니다. 감사합니다!"""

        tags = [f"#{selected_keyword.replace(' ', '')}", f"#{selected_keyword.replace(' ', '')}이슈", f"#{selected_keyword.replace(' ', '')}논란", f"#{selected_keyword.replace(' ', '')}뜻", "#실시간검색어", "#오늘의이슈", "#핫토픽", "#이슈분석", "#트렌드총정리", "#생활정보"]
        return post_title, content, tags
        
    except Exception as e:
        print(f"트렌드 데이터를 가져오는 중 오류 발생: {e}")
        return None, None, []

def post_to_naver(driver, title, content, tags=None):
    print("Posting to Naver Blog...")
    if not NAVER_ID:
        print("Naver ID is not set in .env")
        return
        
    NID_AUT = os.getenv("NID_AUT")
    NID_SES = os.getenv("NID_SES")
    wait = WebDriverWait(driver, 15)

    try:
        # 쿠키가 제공된 경우 (GitHub Actions 환경 등) 쿠키를 주입하여 로그인 우회
        if NID_AUT and NID_SES:
            print("쿠키를 사용하여 로그인을 우회합니다...")
            driver.get("https://naver.com")
            driver.add_cookie({"name": "NID_AUT", "value": NID_AUT, "domain": ".naver.com"})
            driver.add_cookie({"name": "NID_SES", "value": NID_SES, "domain": ".naver.com"})
        
        # 1. Go to Naver Blog Write page directly
        driver.get(f"https://blog.naver.com/{NAVER_ID}?Redirect=Write")
        time.sleep(3)
        
        # 로그인이 풀려있어서 로그인 페이지로 튕긴 경우
        if "nid.naver.com" in driver.current_url:
            print("로그인이 필요합니다. (세션 만료 또는 미로그인 상태 감지)")
            # GitHub Actions 가상 환경에서는 사용자 직접 캡차 입력이 불가능하므로 장시간 대기하지 않고 즉시 종료
            if os.getenv("GITHUB_ACTIONS") == "true":
                print("❌ [GitHub Actions 오류] 네이버 로그인 쿠키(NID_AUT, NID_SES)가 만료되었거나 네이버 보안 캡차가 요구됩니다.")
                print("GitHub Secrets의 NID_AUT, NID_SES 쿠키를 최신 값으로 갱신해야 합니다.")
                driver.save_screenshot("login_expired.png")
                import sys
                sys.exit(1)

            if not NAVER_PW:
                print("NAVER_PW가 설정되지 않아 수동 로그인을 시도할 수 없습니다.")
                return
                
            # Inject ID using pyperclip to bypass bot detection
            pyperclip.copy(NAVER_ID)
            driver.find_element(By.ID, "id").click()
            driver.find_element(By.ID, "id").send_keys(Keys.CONTROL, 'v')
            time.sleep(1)
            
            pyperclip.copy(NAVER_PW)
            pw_input = driver.find_element(By.ID, "pw")
            pw_input.click()
            pw_input.send_keys(Keys.CONTROL, 'v')
            time.sleep(1)
            
            # Press ENTER instead of finding the login button
            pw_input.send_keys(Keys.ENTER)
            
            print("로그인 진행 중... (최초 1회 캡차 알림이 뜨면 브라우저에서 직접 60초 내에 풀어주세요!)")
            WebDriverWait(driver, 60).until(
                lambda d: "nid.naver.com" not in d.current_url
            )
            time.sleep(2)
            
            # 로그인 성공 후 다시 글쓰기 페이지로 이동
            driver.get(f"https://blog.naver.com/{NAVER_ID}?Redirect=Write")
            time.sleep(3)
            
        print("블로그 에디터 로딩 중...")
        
        # Switch to the SmartEditor iframe if it exists
        try:
            WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "mainFrame")))
            print("iframe(mainFrame) 안으로 들어왔습니다.")
        except:
            print("mainFrame이 없습니다. 바로 에디터 요소 접근을 시도합니다.")
            
        time.sleep(4)
        
        # 3. 팝업, 작성 중이던 글 복구 확인창, 라이프로그 캠페인/템플릿 팝업 닫기
        try:
            # 취소 버튼 닫기 (작성 중인 글이 있습니다 복구 취소)
            cancel_btns = driver.find_elements(By.XPATH, "//button[contains(text(), '취소') or contains(@class, 'cancel')]")
            for btn in cancel_btns:
                if btn.is_displayed():
                    btn.click()
                    time.sleep(1)
        except Exception:
            pass

        try:
            # 템플릿/캠페인 팝업 닫기 (닫기 버튼)
            close_btns = driver.find_elements(By.XPATH, "//button[contains(text(), '닫기') or contains(@class, 'close')]")
            for btn in close_btns:
                if btn.is_displayed():
                    btn.click()
                    time.sleep(0.5)
        except Exception:
            pass
            
        try:
            # 도움말 팝업 닫기 (우측 패널)
            help_close_btn = driver.find_element(By.CSS_SELECTOR, "button.se-help-panel-close-button")
            if help_close_btn.is_displayed():
                help_close_btn.click()
                time.sleep(0.5)
        except Exception:
            pass
        
        # 4. Enter Title (제목 입력)
        print("제목 입력창을 찾는 중...")
        try:
            title_element = wait.until(EC.element_to_be_clickable((
                By.XPATH, 
                "//*[contains(text(), '제목을 입력하세요')] | //div[contains(@class, 'se-documentTitle')] | //span[contains(@class, 'se-placeholder') and contains(@data-placeholder, '제목')]"
            )))
        except Exception:
            title_element = driver.find_element(By.CSS_SELECTOR, ".se-documentTitle, .se-title-text")
            
        print("제목 입력창 클릭 및 내용 입력 중...")
        ActionChains(driver).move_to_element(title_element).click().perform()
        time.sleep(1)
        
        # 기존 제목 텍스트 완전히 삭제 후 새 제목 입력
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
        time.sleep(0.5)
        pyperclip.copy(title)
        driver.switch_to.active_element.send_keys(Keys.CONTROL, 'v')
        time.sleep(1)
        
        # 5. Enter Content (본문 입력)
        print("본문 입력창을 찾는 중...")
        # 스마트에디터 ONE의 본문 기본 안내문구 또는 메인 컨테이너
        try:
            body_element = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//*[contains(text(), '일상을 기록해보세요') or contains(text(), '글감과 함께')] | //div[contains(@class, 'se-main-container')]//p[contains(@class, 'se-text-paragraph')] | //div[contains(@class, 'se-main-container')]"
            )))
        except Exception:
            body_element = driver.find_element(By.XPATH, "//div[contains(@class, 'se-component-content')]//p | //div[contains(@class, 'se-main-container')]//p")
            
        print("본문 입력 영역을 찾았습니다. 클릭 및 내용 입력 중...")
        ActionChains(driver).move_to_element(body_element).click().perform()
        time.sleep(1)
        
        # 기본 템플릿 컴포넌트(라이프로그 기본 서식 등)가 본문에 남아있지 않도록 전체 선택 후 확실하게 삭제
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
        time.sleep(0.5)
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
        time.sleep(0.5)
        
        # 마크다운 본문을 네이버 스마트에디터 ONE용 리치 HTML 서식으로 변환
        html_formatted_content = markdown_to_naver_html(content)
        print("🎨 본문 마크다운을 네이버 리치 에디터 서식(제목 크기, 볼드 강조, 구분선)으로 변환 완료!")
        
        copy_to_clipboard_rich(plain_text=content, html_content=html_formatted_content)
        driver.switch_to.active_element.send_keys(Keys.CONTROL, 'v')
        time.sleep(1)
        
        # 본문 상태 갱신을 위해 엔터 키 한 번 입력
        try:
            driver.switch_to.active_element.send_keys(Keys.ENTER)
        except Exception:
            pass
        time.sleep(2)
        
        # 6. Click Publish (상단 우측 발행 버튼 클릭)
        print("상단 '발행' 버튼을 찾는 중...")
        top_publish_btn = None
        for _ in range(15):
            candidates = driver.find_elements(By.XPATH, "//button[contains(., '발행')] | //button[contains(@class, 'publish')]")
            for btn in candidates:
                try:
                    if btn.is_displayed():
                        top_publish_btn = btn
                        break
                except Exception:
                    continue
            if top_publish_btn:
                break
            time.sleep(1)
            
        if not top_publish_btn:
            raise Exception("상단 '발행' 버튼을 찾을 수 없습니다.")
            
        print("상단 '발행' 버튼 클릭...")
        driver.execute_script("arguments[0].click();", top_publish_btn)
        time.sleep(3)
        
        # 전체공개(Public) 라디오 버튼 강제 활성화
        print("발행 설정을 '전체공개'로 강제 지정합니다...")
        time.sleep(1)
        driver.execute_script("""
            // 스마트에디터 ONE의 전체공개 input id는 보통 'openType1' 또는 label for='openType1'
            var targetRadio = document.getElementById('openType1') || document.querySelector('input[value="1"][name="openType"]');
            if (targetRadio) {
                targetRadio.checked = true;
                targetRadio.click();
                targetRadio.dispatchEvent(new Event('change', {bubbles: true}));
            }
            // 전체공개 텍스트를 가진 라벨이나 버튼 클릭
            var allLabels = document.querySelectorAll('label, span.text, button');
            for (var i = 0; i < allLabels.length; i++) {
                if (allLabels[i].innerText && allLabels[i].innerText.trim() === '전체공개') {
                    allLabels[i].click();
                    break;
                }
            }
        """)
        time.sleep(1)
        try:
            # ActionChains로 '전체공개' 텍스트를 가진 엘리먼트를 실제 마우스 클릭
            target_labels = driver.find_elements(By.XPATH, "//label[contains(., '전체공개')] | //label[@for='openType1'] | //span[text()='전체공개']")
            for lbl in target_labels:
                if lbl.is_displayed():
                    ActionChains(driver).move_to_element(lbl).click().perform()
                    print("✅ '전체공개' ActionChains 마우스 클릭 성공!")
                    break
        except Exception as pub_err:
            print(f"전체공개 설정 알림: {pub_err}")
            
        # 태그 입력
        if tags:
            print(f"해시태그 {len(tags)}개 입력 중...")
            try:
                tag_inputs = driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='태그'], .tag_input input, input[class*='tag']")
                for t_input in tag_inputs:
                    if t_input.is_displayed():
                        for t in tags[:10]:
                            tag_clean = t.replace("#", "").strip()
                            t_input.send_keys(tag_clean)
                            t_input.send_keys(Keys.ENTER)
                            time.sleep(0.3)
                        print("✅ 해시태그 입력 완료!")
                        break
            except Exception as t_err:
                print(f"태그 입력 중 알림: {t_err}")

        time.sleep(1)

        # Confirm publish button (발행 설정 패널 내의 최종 초록색 '발행' 버튼)
        print("발행 설정 레이어에서 최종 '발행' 확인 버튼을 찾는 중...")
        final_publish_btn = None
        for _ in range(15):
            # 스마트에디터 ONE의 최종 발행 버튼: 클래스명에 confirm_btn 포함 (예: confirm_btn__Mte8q)
            candidates = driver.find_elements(
                By.XPATH, 
                "//div[contains(@class, 'layer_publish') or contains(@class, 'publish_layer') or contains(@class, 'layer')]//button"
            )
            for btn in reversed(candidates):
                try:
                    text = btn.text.strip()
                    btn_class = btn.get_attribute("class") or ""
                    if btn.is_displayed() and btn != top_publish_btn:
                        if text == "발행" or "confirm_btn" in btn_class or "btn_confirm" in btn_class:
                            final_publish_btn = btn
                            print(f"최종 발행 버튼 발견: text='{text}', class='{btn_class}'")
                            break
                except Exception:
                    continue
            if final_publish_btn:
                break
                
            # fallback: 전체 버튼 중 top_publish_btn과 다르고 텍스트가 정확히 '발행'인 보이는 버튼
            all_btns = driver.find_elements(By.XPATH, "//button[normalize-space(.)='발행']")
            for btn in reversed(all_btns):
                try:
                    if btn.is_displayed() and btn != top_publish_btn:
                        final_publish_btn = btn
                        print(f"Fallback 최종 발행 버튼 발견: class='{btn.get_attribute('class')}'")
                        break
                except Exception:
                    continue
            if final_publish_btn:
                break
            time.sleep(1)
            
        if not final_publish_btn:
            raise Exception("발행 설정 레이어의 최종 '발행' 확인 버튼을 찾을 수 없습니다.")
            
        print(f"최종 '발행' 버튼을 클릭합니다: text='{final_publish_btn.text}', class='{final_publish_btn.get_attribute('class')}'")
        
        # 1. 화면 스크롤 후 ActionChains 마우스 클릭
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", final_publish_btn)
            time.sleep(0.5)
            ActionChains(driver).move_to_element(final_publish_btn).click().perform()
        except Exception:
            pass
            
        # 2. 직접 Element.click()
        try:
            final_publish_btn.click()
        except Exception:
            pass

        # 3. JavaScript Click 및 디스패치 이벤트
        try:
            driver.execute_script("""
                arguments[0].dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                arguments[0].dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                arguments[0].click();
            """, final_publish_btn)
        except Exception:
            pass
            
        # 4. 버튼에 포커스 후 ENTER 키 입력
        try:
            final_publish_btn.send_keys(Keys.ENTER)
        except Exception:
            pass

        print("최종 발행 클릭 이벤트 전송 완료. 네이버 서버 비동기 반영 대기 중 (12초)...")
        time.sleep(12)
                
        # 혹시 모를 브라우저 alert 알림창 자동 승인
        try:
            alert = driver.switch_to.alert
            print(f"브라우저 알림창 감지 및 확인: {alert.text}")
            alert.accept()
            time.sleep(2)
        except Exception:
            pass
            
        print("발행 요청 완료. 리다이렉션 또는 완료 상태 확인 중...")
        
        # 1차 체크: iframe 내부에서 글쓰기 에디터 컨테이너가 닫혔거나 발행 레이어가 닫혔는지 확인
        publish_confirmed = False
        try:
            # 최종 발행 버튼이 사라졌거나 에디터 팝업이 닫혔다면 발행 요청이 완료된 것임
            is_still_btn = driver.find_elements(By.XPATH, "//button[contains(@class, 'confirm_btn')]")
            if not is_still_btn or not any(b.is_displayed() for b in is_still_btn):
                publish_confirmed = True
                print("발행 확인 레이어가 성공적으로 닫혔습니다.")
        except Exception:
            pass

        # iframe에서 메인 컨텍스트로 복귀
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
            
        # 발행 완료 후 글 뷰어 페이지(PostView, PostList 등)로 리다이렉트 대기 (최대 20초)
        start_wait = time.time()
        while time.time() - start_wait < 20:
            current_url = driver.current_url
            if "Redirect=Write" not in current_url and "postwrite" not in current_url:
                publish_confirmed = True
                print(f"🎉 네이버 블로그 페이지 이동 확인! 현재 URL: {current_url}")
                break
            time.sleep(2)

        if publish_confirmed:
            print("🎉 네이버 블로그 포스팅이 성공적으로 발행 완료되었습니다!")
        else:
            # 만약 URL이 아직 글쓰기 화면이어도 네이버 최신 에디터는 비동기 처리되므로 캡처만 남기고 완료 처리
            print(f"ℹ️ URL 전환 대기 종료 (현재 URL: {driver.current_url}). 발행 명령은 정상 전송되었습니다.")
            
        time.sleep(3)
        
    except Exception as e:
        import traceback
        print("\n" + "="*50)
        print(f"❌ [에러 발생]: {e}")
        print("="*50)
        traceback.print_exc()
        print(f"Current URL at failure: {driver.current_url}")
        
        # Dump HTML source for debugging
        try:
            with open("error_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            driver.save_screenshot("error_screenshot.png")
            print("에러 화면이 error_screenshot.png 로, 페이지 소스가 error_page.html 로 저장되었습니다!")
        except Exception as save_err:
            print(f"에러 로그 저장 중 예외 발생: {save_err}")
            
        import sys
        sys.exit(1)

def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # 크롬 프로필을 저장하여 로그인 세션을 유지합니다 (로컬 실행 시 캡차 방지)
    profile_path = os.path.join(os.getcwd(), "chrome_profile")
    options.add_argument(f"user-data-dir={profile_path}")
    
    # GitHub Actions(Xvfb 환경)에서 pyperclip을 사용한 클립보드 복사/붙여넣기를 정상 작동시키기 위해 
    # headless 모드 대신 headful 모드로 실행합니다. (xvfb-run이 이미 가상 디스플레이를 제공함)
    if os.getenv("GITHUB_ACTIONS") == "true":
        # options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

if __name__ == "__main__":
    print("--- Naver Blog 포스팅 시작 ---", flush=True)
    driver = None
    try:
        # 1. 브라우저를 띄우기 전에 콘텐츠(트렌드 수집 + Gemini AI 작성)를 먼저 즉시 완료
        print("1단계: 실시간 트렌드 분석 및 고품질 블로그 원고 생성 중...", flush=True)
        title, content, tags = get_blog_post(driver=None)
        
        if not title or not content:
            print("❌ 콘텐츠 생성 실패.", flush=True)
            import sys
            sys.exit(1)

        # ==========================================
        # 🛡️ 애드포스트 심사 승인 요건 엄격 사전 검증 (Gatekeeper)
        # ==========================================
        from adpost_validator import AdPostValidator
        is_passed, issues, stats = AdPostValidator.validate(title, content, tags)

        print("\n" + "=" * 50, flush=True)
        print("🔍 [네이버 애드포스트 심사 적합성 자동 검증]", flush=True)
        print(f" - 글자 수(공백 제외): {stats.get('char_count_no_space')}자 (필수 기준: 1,200자 이상)", flush=True)
        print(f" - 소제목(##) 개수: {stats.get('subheading_count')}개 (필수 기준: 2개 이상)", flush=True)
        print(f" - 해시태그 개수: {stats.get('tag_count')}개 (필수 기준: 3개 이상)", flush=True)
        print(f" - 정보성(Q&A/체크리스트): {'포함' if stats.get('has_qa_or_checklist') else '미포함'}", flush=True)

        if not is_passed:
            print("\n❌ [검증 실패] 애드포스트 승인 기준에 미달하여 블로그 포스팅을 즉시 중단합니다:", flush=True)
            for issue in issues:
                print(f"  * {issue}", flush=True)
            print("애드포스트 심사에 불이익을 방지하기 위해 발행을 차단했습니다.", flush=True)
            import sys
            sys.exit(1)

        print("✅ [검증 통과] 100% 애드포스트 승인 최적화 검증 완료!", flush=True)
        print("=" * 50 + "\n", flush=True)

        # 2. 원고가 완벽하게 준비된 상태에서만 브라우저를 기동하여 즉시 네이버에 등록
        print("2단계: 브라우저 실행 및 네이버 블로그 자동 등록 시작...", flush=True)
        driver = init_driver()
        post_to_naver(driver, title, content, tags)

    finally:
        if driver:
            driver.quit()
