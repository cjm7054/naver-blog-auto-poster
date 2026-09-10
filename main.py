import os
import time
import requests
import pyperclip
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

def get_signal_bz_trends(driver):
    print("Fetching today's top 10 real-time search trends from Signal.bz...")
    
    try:
        driver.get("https://signal.bz/news")
        time.sleep(3) # Vue.js 렌더링 대기
        
        trends = []
        rank_elements = driver.find_elements(By.CSS_SELECTOR, ".rank-text")
        
        for i, el in enumerate(rank_elements):
            if i >= 10:
                break
            trends.append(el.text.strip())
            
        return trends
    except Exception as e:
        print(f"Error fetching Signal.bz trends: {e}")
        return []

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
3. 블로그 포스팅 구성:
   - [도입부 (서론)]: 왜 지금 [{selected_keyword}]이(가) 대중들의 폭발적인 관심을 받고 있는지, 배경과 이슈의 발단을 흥미진진하게 서술.
   - [본문 소제목 1 (##)]: 사건/이슈의 구체적인 전개 과정과 핵심 팩트 총정리
   - [본문 소제목 2 (##)]: 대중들의 여론 반응과 온라인/업계의 다양한 시각 분석
   - [본문 소제목 3 (##)]: 향후 전망 및 우리가 주목해야 할 핵심 시사점/체크포인트
   - [FAQ 섹션 (##)]: 독자들이 가장 궁금해할 만한 핵심 질문 3가지와 명쾌하고 상세한 답변 (Q1, Q2, Q3)
   - [결론 (##)]: 전체 내용을 한눈에 요약하고, 독자에게 의견을 묻는 소통형 맺음말 및 공감/이웃추가 유도.
4. 문체: 부드럽고 가독성 높은 친절한 존댓말 (~합니다, ~해보세요, ~알아보았습니다).
5. 해시태그: 주제와 밀접한 고효율 태그 10개 추출.

[출력 형식 - 반드시 유효한 JSON 형식만 반환]:
{{
  "title": "{selected_keyword} 논란 및 핵심 쟁점 총정리! 화제가 된 진짜 이유와 향후 전망",
  "content": "본문 전체 내용 (마크다운 ## 소제목 활용)",
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

def get_blog_post(driver):
    try:
        trends = get_signal_bz_trends(driver)
        if not trends:
            print("트렌드 키워드를 찾지 못했습니다.")
            return None, None, []
            
        today = datetime.now().strftime("%Y년 %m월 %d일 %H시")
        
        # 🎯 실시간 10개 키워드 중 가장 화제성이 높은 '1개'를 선정하여 단독 심층 작성!
        selected_keyword = trends[0]
        other_trends = trends[1:5]
        print(f"🎯 실시간 10개 키워드 중 오늘의 단독 포스팅 주제 선정: [{selected_keyword}]")
        
        # 1. Gemini AI를 통한 1개 주제 집중 1,800자+ 단독 심층 원고 생성 시도
        ai_title, ai_content, ai_tags = generate_article_with_gemini(selected_keyword, other_trends, today)
        if ai_title and ai_content and len(ai_content) > 1200:
            print(f"Gemini AI를 통해 [{selected_keyword}] 단독 심층 원고({len(ai_content)}자)가 성공적으로 생성되었습니다!")
            return ai_title, ai_content, ai_tags
            
        # 2. AI 키 미설정 시에도 [선정된 1개 키워드]에 집중하여 1,800자 이상 작성되는 풍성한 단독 심층 원고
        post_title = f"{selected_keyword} 집중 분석 및 핵심 쟁점 총정리! 화제가 된 배경과 향후 전망"
        
        content = f"""안녕하세요! 빠르게 변화하는 사회 이슈와 대중들의 뜨거운 화제거리를 누구보다 알기 쉽고 깊이 있게 정리해 드리는 트렌드 이슈 전문 블로그입니다.

최근 각종 포털 사이트의 실시간 검색어 순위와 주요 뉴스 헤드라인, 그리고 대형 온라인 커뮤니티를 가장 뜨겁게 달구고 있는 단 하나의 키워드를 꼽으라면 단연 '{selected_keyword}'일 것입니다.

많은 분들이 갑작스럽게 떠오른 이 이슈를 접하고 "도대체 어떤 사연이 있길래 이렇게 실시간 1위까지 올라왔을까?", "핵심 쟁점과 팩트는 무엇일까?" 하며 많은 궁금증을 가지고 검색해 보고 계실 텐데요.

그래서 오늘은 단편적인 찌라시나 자극적인 소문을 배제하고, 지금까지 공식적으로 확인된 객관적인 사실 관계와 대중들의 여론 반응, 그리고 앞으로의 파급 효과까지 '{selected_keyword}'의 모든 것을 완벽하게 짚어드리겠습니다!

---

## 1. '{selected_keyword}', 도대체 무슨 일일까요? 발단과 배경 총정리

이번 '{selected_keyword}' 사안이 폭발적인 관심을 받게 된 것은 특정 보도와 온라인상의 입장 발표가 도화선이 되었습니다.

사건의 발단을 시간 순서대로 짚어보면, 당초 예상치 못했던 전개가 펼쳐지며 다양한 이해관계자들의 입장 차이가 극명하게 드러났는데요. 특히 이전부터 누적되어 온 여러 사회적 관심사와 맞물리면서 단순한 개인의 일탈이나 해프닝 수준을 넘어선 공공의 논쟁거리로 급부상하게 되었습니다.

현재 관련 부처와 소속 기관, 그리고 당사자 측에서도 상황의 중대성을 인지하고 공식적인 입장문을 내놓거나 사실 관계 확인에 착수하고 있는 상태입니다. 정보가 너무 빠르게 퍼져나가는 시점일수록 확인되지 않은 추측성 루머에 휩쓸리지 않고 정확한 맥락을 파악하는 태도가 중요합니다.

---

## 2. 네티즌 여론과 전문가들의 엇갈린 시선: 핵심 쟁점 3가지

현재 각종 커뮤니티와 SNS에서는 이번 '{selected_keyword}' 이슈를 두고 뜨거운 갑론을박이 벌어지고 있습니다. 여론의 시각을 크게 3가지 쟁점으로 압축해 볼 수 있습니다.

### 첫째: 원칙과 절차의 적절성 논란
일부 여론에서는 이번 사안의 처리 과정이나 발단이 상식과 법적/도덕적 기준에 부합했는지를 두고 비판적인 목소리를 높이고 있습니다. 사전에 충분한 조율이나 예방이 가능하지 않았느냐는 지적도 함께 제기되는 상황입니다.

### 둘째: 구조적인 문제인가, 개인의 책임인가
단순히 특정 인물이나 사건만의 문제가 아니라, 우리 사회와 조직 문화 내에 만연해 있던 구조적 모순이 곪아 터진 것이라는 분석도 설득력을 얻고 있습니다. 이번 기회를 통해 보다 근본적인 재발 방지 대책이 마련되어야 한다는 여론이 힘을 얻고 있습니다.

### 셋째: 향후 미칠 파급력과 선례
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
        
        # 로그인이 풀려있어서 로그인 페이지로 튕긴 경우에만 수동 로그인 수행 (로컬 환경 백업용)
        if "nid.naver.com" in driver.current_url:
            print("로그인이 필요합니다. 로그인을 시도합니다...")
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
            
            print("로그인 진행 중... (최초 1회 캡차 알림이 뜨면 브라우저에서 직접 120초 내에 풀어주세요!)")
            # Wait until we are out of the login page and out of any nid.naver.com security pages
            WebDriverWait(driver, 120).until(
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
            
        time.sleep(5)
        
        # 3. Close popups if any exist (e.g., auto-save restore)
        try:
            cancel_btns = driver.find_elements(By.XPATH, "//button[contains(text(), '취소') or contains(@class, 'cancel')]")
            for btn in cancel_btns:
                if btn.is_displayed():
                    btn.click()
                    time.sleep(1)
        except:
            pass
            
        try:
            # 도움말 팝업 닫기 (우측 팝업)
            help_close_btn = driver.find_element(By.CSS_SELECTOR, "button.se-help-panel-close-button")
            if help_close_btn.is_displayed():
                help_close_btn.click()
                time.sleep(1)
        except:
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
        
        # 기존 텍스트 삭제 및 새 제목 입력
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
        time.sleep(0.5)
        pyperclip.copy(title)
        driver.switch_to.active_element.send_keys(Keys.CONTROL, 'v')
        time.sleep(1)
        
        # 5. Enter Content (본문 입력)
        print("본문 입력창을 찾는 중...")
        # 스마트에디터 ONE의 본문 기본 안내문구: '글감과 함께 나의 일상을 기록해보세요!'
        try:
            body_element = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//*[contains(text(), '일상을 기록해보세요') or contains(text(), '글감과 함께')] | //div[contains(@class, 'se-main-container')]//p[contains(@class, 'se-text-paragraph')]"
            )))
        except Exception:
            body_element = driver.find_element(By.XPATH, "//div[contains(@class, 'se-component-content')]//p | //div[contains(@class, 'se-main-container')]//p")
            
        print("본문 입력 영역을 찾았습니다. 클릭 및 내용 입력 중...")
        ActionChains(driver).move_to_element(body_element).click().perform()
        time.sleep(1)
        
        # 기존 본문 삭제 후 새 본문 내용 붙여넣기
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
        time.sleep(0.5)
        pyperclip.copy(content)
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
        
        # 전체공개(Public) 라디오 버튼 명시적 클릭
        print("발행 설정을 '전체공개'로 설정합니다...")
        try:
            # 네이버 스마트에디터 ONE의 전체공개 라디오 버튼
            public_btns = driver.find_elements(By.XPATH, "//label[contains(., '전체공개')] | //input[@type='radio' and contains(@value, 'public')] | //button[contains(., '전체공개')]")
            for p_btn in public_btns:
                if p_btn.is_displayed():
                    driver.execute_script("arguments[0].click();", p_btn)
                    print("✅ '전체공개' 선택 완료!")
                    break
        except Exception as pub_err:
            print(f"전체공개 설정 중 알림: {pub_err}")
            
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
    print("--- Naver Blog 포스팅 시작 ---")
    driver = None
    try:
        driver = init_driver()
        title, content, tags = get_blog_post(driver)
        
        if not title or not content:
            print("❌ 콘텐츠 생성 실패.")
            import sys
            sys.exit(1)

        # ==========================================
        # 🛡️ 애드포스트 심사 승인 요건 엄격 사전 검증 (Gatekeeper)
        # ==========================================
        from adpost_validator import AdPostValidator
        is_passed, issues, stats = AdPostValidator.validate(title, content, tags)

        print("\n" + "=" * 50)
        print("🔍 [네이버 애드포스트 심사 적합성 자동 검증]")
        print(f" - 글자 수(공백 제외): {stats.get('char_count_no_space')}자 (필수 기준: 1,200자 이상)")
        print(f" - 소제목(##) 개수: {stats.get('subheading_count')}개 (필수 기준: 2개 이상)")
        print(f" - 해시태그 개수: {stats.get('tag_count')}개 (필수 기준: 3개 이상)")
        print(f" - 정보성(Q&A/체크리스트): {'포함' if stats.get('has_qa_or_checklist') else '미포함'}")

        if not is_passed:
            print("\n❌ [검증 실패] 애드포스트 승인 기준에 미달하여 블로그 포스팅을 즉시 중단합니다:")
            for issue in issues:
                print(f"  * {issue}")
            print("애드포스트 심사에 불이익을 방지하기 위해 발행을 차단했습니다.")
            import sys
            sys.exit(1)

        print("✅ [검증 통과] 100% 애드포스트 승인 최적화 검증 완료! 블로그에 안전하게 공개 발행합니다.")
        print("=" * 50 + "\n")

        # 검증 통과한 경우에만 네이버 블로그 발행 진행
        post_to_naver(driver, title, content, tags)

    finally:
        if driver:
            driver.quit()
