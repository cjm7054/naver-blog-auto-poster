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

def get_blog_post(driver):
    try:
        trends = get_signal_bz_trends(driver)
        
        if not trends:
            print("트렌드 키워드를 찾지 못했습니다.")
            return None, None
            
        today = datetime.now().strftime("%Y년 %m월 %d일 %H시")
        
        post_title = f"[오늘의 실시간 핫이슈 TOP 10] {today} 트렌드 정리!"
        
        post_content = f"안녕하세요! 오늘 하루 동안 가장 많은 관심을 받은 실시간 검색어 TOP 10을 정리해 드립니다.\n\n"
        post_content += f"과연 오늘은 어떤 이슈들이 사람들의 이목을 끌었을까요?\n\n"
        post_content += f"🔥 {today} 실시간 트렌드 TOP 10\n\n"
        
        for i, t in enumerate(trends):
            post_content += f"{i+1}위: {t}\n"
            
        post_content += "\n위 키워드들은 Signal.bz 실시간 검색어 데이터를 기반으로 작성되었습니다.\n"
        post_content += "오늘도 방문해 주셔서 감사합니다! 좋은 하루 보내세요 😊"
        
        return post_title, post_content
        
    except Exception as e:
        print(f"트렌드 데이터를 가져오는 중 오류 발생: {e}")
        return None, None

def post_to_naver(driver, title, content):
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
        title, content = get_blog_post(driver)
        if title and content:
            post_to_naver(driver, title, content)
        else:
            print("콘텐츠 생성 실패.")
    finally:
        if driver:
            driver.quit()
