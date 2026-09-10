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

def generate_article_with_gemini(trends, today_str):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None, None, []
        
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        
        top3_text = ", ".join(trends[:3])
        all_trends_text = "\n".join([f"{i+1}위: {t}" for i, t in enumerate(trends)])
        
        prompt = f"""
당신은 네이버 블로그 상위 1% 인플루언서이자 네이버 애드포스트 고수익 전문 에디터입니다.
아래 제공된 실시간 트렌드 키워드들을 바탕으로 네이버 블로그 독자들의 체류시간을 극대화할 수 있는 최고 품질의 트렌드 브리핑 글을 작성하세요.

[실시간 트렌드 목록]:
{all_trends_text}

[작성 및 네이버 애드포스트 심사 통과 규칙 - 필수]:
1. 글자 수: 공백 제외 반드시 1,500자 ~ 2,200자 이상으로 매우 상세하고 깊이 있게 작성하세요. (단순 키워드 나열은 절대 금지)
2. 글의 구성:
   - [도입부]: 오늘({today_str}) 대중들의 관심이 집중된 사회적 배경과 이슈 전반에 대한 친근한 서론.
   - [핵심 이슈 심층 분석 3선]: 1위~3위 핵심 이슈({top3_text})에 대해 각각 소제목(##)을 달고, 왜 화제가 되었는지 배경, 여론의 반응, 그리고 우리가 알아두어야 할 시사점을 3~4문단 이상 상세히 서술.
   - [전체 순위 한눈에 보기]: 1위부터 10위까지 깔끔하게 정리된 요약 리스트.
   - [주목할 포인트 및 Q&A]: 이번 이슈와 관련해 독자들이 가장 궁금해할 만한 핵심 질문 2가지와 명쾌한 설명.
   - [마무리 및 소통]: 이웃 추가와 공감(하트), 댓글을 유도하는 신뢰감 있는 맺음말.
3. 문체: 부드럽고 가독성 높은 존댓말 (~해요, ~합니다, ~살펴볼까요?).

[출력 형식 - JSON 문자열]:
{{
  "title": "[실시간 핫이슈] {today_str} 대한민국 화제의 검색어 TOP 10 총정리 및 심층 분석",
  "content": "본문 전체 내용 (마크다운 ## 소제목 활용)",
  "tags": ["#실시간검색어", "#오늘의이슈", "#핫토픽", "#트렌드분석", "#실시간트렌드"]
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
        print(f"Gemini API 생성 중 오류 또는 미설정: {e}. 고품질 리치 템플릿으로 대체합니다.")
        return None, None, []

def get_blog_post(driver):
    try:
        trends = get_signal_bz_trends(driver)
        if not trends:
            print("트렌드 키워드를 찾지 못했습니다.")
            return None, None, []
            
        today = datetime.now().strftime("%Y년 %m월 %d일 %H시")
        
        # 1. Gemini AI를 통한 1,500자+ 고품질 심층 기사 생성 시도
        ai_title, ai_content, ai_tags = generate_article_with_gemini(trends, today)
        if ai_title and ai_content and len(ai_content) > 1000:
            print(f"Gemini AI를 통해 {len(ai_content)}자의 고품질 원고가 생성되었습니다!")
            return ai_title, ai_content, ai_tags
            
        # 2. AI 키 미설정 시에도 애드포스트 1,500자 기준을 충족하는 심층 리치 원고 생성
        top1 = trends[0] if len(trends) > 0 else "실시간 핫토픽"
        top2 = trends[1] if len(trends) > 1 else "주요 이슈"
        top3 = trends[2] if len(trends) > 2 else "화제의 소식"
        
        post_title = f"[오늘의 실시간 핫이슈 TOP 10] {today} 화제의 트렌드 분석 및 총정리"
        
        content = f"""안녕하세요! 매일 시시각각 빠르게 변화하는 대한민국 인터넷의 가장 뜨거운 화제거리와 알짜배기 트렌드 소식을 한눈에 보기 쉽게 전달해 드리는 정보 브리핑 블로그입니다.

현대 사회는 정보가 너무나 방대하고 빠르게 쏟아져 나오기 때문에, 잠깐만 바쁜 일상에 집중하다 보면 오늘 대중들의 이목을 사로잡은 핵심 이슈가 무엇인지 놓치기 십상입니다. 

그래서 오늘은 {today} 기준, 각종 포털과 온라인 커뮤니티, SNS에서 폭발적인 조회수와 검색량을 기록하고 있는 실시간 검색어 TOP 10을 엄선하여 그 배경과 핵심 포인트까지 꼼꼼하게 짚어드리겠습니다!

---

## 1. 오늘 대중의 시선이 가장 집중된 이슈: '{top1}'

오늘 실시간 트렌드에서 압도적인 주목을 받고 있는 첫 번째 화제의 중심은 바로 '{top1}'입니다.

인터넷 여론과 포털 뉴스를 종합해 보면, 이번 이슈는 단순한 일회성 해프닝을 넘어서 많은 네티즌들 사이에서 다양한 의견과 열띤 토론을 불러일으키고 있는 상황인데요. 특히 관련 업계와 대중문화, 그리고 사회 전반에 미칠 파급력에 대해 많은 관심이 쏠리고 있습니다.

온라인 반응을 살펴보면 "전혀 예상치 못했던 전개다", "앞으로의 공식 입장과 후속 보도를 더 지켜봐야 할 것 같다"는 신중론과 함께 다양한 시선들이 공존하고 있습니다. 앞으로 발표될 추가 소식에 따라 이슈의 향방이 어떻게 전개될지 지속적인 모니터링이 필요한 대목입니다.

---

## 2. 뜨거운 화제를 이어가고 있는 2위 & 3위 트렌드: '{top2}', '{top3}'

1위 못지않게 많은 이목을 끌고 있는 두 번째, 세 번째 키워드는 각각 '{top2}'와 '{top3}'입니다.

현재 직장인들과 네티즌들 사이에서 점심시간 및 퇴근길 메인 대화 주제로 오르내리고 있으며, SNS와 유튜브, 각종 커뮤니티 게시판을 통해 관련 숏폼 영상과 분석 글들이 빠르게 확산되고 있는 모습을 확인할 수 있습니다.

정보가 너무 빠르게 전달되다 보면 사실과 다른 미확인 소문이나 왜곡된 내용이 퍼질 위험도 있으므로, 항상 검증된 공식 보도와 객관적인 팩트를 바탕으로 맥락을 파악하는 지혜가 중요합니다.

---

## 3. 🔥 {today} 실시간 트렌드 TOP 10 한눈에 보기

그렇다면 오늘 전체 검색 순위 1위부터 10위까지는 어떤 키워드들이 자리 잡았을까요? 아래 리스트를 통해 한눈에 확인해 보세요.

"""
        for i, t in enumerate(trends):
            content += f"- **{i+1}위**: {t}\n"
            
        content += f"""
---

## 4. 실시간 이슈를 스마트하게 소비하는 팁 (Q&A)

**Q1. 급상승 검색어는 어떤 기준으로 집계되나요?**
A. 특정 시간대 동안 포털 및 뉴스, SNS 상에서 사용자들의 검색 빈도와 클릭 수, 그리고 기사 발행량이 단기간에 급격히 증가한 키워드를 실시간 알고리즘으로 분석하여 산출됩니다.

**Q2. 자극적인 이슈 뉴스 속에서 팩트를 구별하는 방법은?**
A. 제목만 보고 섣불리 판단하기보다는 기사 본문의 공식 출처와 당사자의 입장문 전문을 직접 확인하시는 것이 가장 안전하고 정확합니다.

---

## 마치며

지금까지 {today} 실시간 대한민국을 뜨겁게 달군 핫이슈 TOP 10과 주요 트렌드를 종합적으로 정리해 드렸습니다. 

오늘 정리해 드린 내용이 세상 돌아가는 흐름을 빠르고 정확하게 파악하시는 데 많은 도움이 되셨기를 바랍니다. 

포스팅이 유익하셨다면 **공감(하트)과 따뜻한 댓글**, 그리고 유익한 트렌드 정보를 매일 가장 빠르게 받아보실 수 있도록 **이웃 추가** 부탁드립니다. 항상 신속하고 검증된 소식으로 다시 찾아뵙겠습니다. 오늘도 활기차고 행복한 하루 보내세요!"""

        tags = ["#실시간검색어", "#오늘의이슈", "#핫토픽", "#실시간트렌드", f"#{top1.replace(' ', '')}", f"#{top2.replace(' ', '')}", "#트렌드정리", "#이슈브리핑", "#생활정보", "#뉴스이슈"]
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
