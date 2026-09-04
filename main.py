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
        
        # 4. Enter Title
        # 네이버 스마트에디터 ONE의 클래스명이 유동적이므로, contenteditable 속성으로 첫번째 입력창(제목)을 찾습니다.
        try:
            content_editables = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[contenteditable='true']")))
            if len(content_editables) >= 2:
                title_element = content_editables[0]
                body_element = content_editables[1]
            else:
                # 못 찾았을 경우 대비용 백업 셀렉터
                title_element = driver.find_element(By.CSS_SELECTOR, ".se-title-text, .se-documentTitle")
                body_element = None
        except Exception as e:
            print("contenteditable 요소를 찾지 못했습니다. 백업 셀렉터를 시도합니다.")
            title_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".se-title-text, .se-documentTitle, span.se-placeholder")))
            body_element = None
            
        print("제목 입력창을 찾았습니다. 클릭 및 내용 입력을 시작합니다.")
        ActionChains(driver).move_to_element(title_element).click().perform()
        time.sleep(1)
        
        # Select all and delete old auto-saved text
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
        time.sleep(1)
        
        # Type new title
        pyperclip.copy(title)
        driver.switch_to.active_element.send_keys(Keys.CONTROL, 'v')
        time.sleep(1)
        
        # 5. Enter Content
        if body_element:
            ActionChains(driver).move_to_element(body_element).click().perform()
        else:
            # Press TAB to move to the content area
            ActionChains(driver).send_keys(Keys.TAB).perform()
            
        time.sleep(1)
        
        # Select all and delete old auto-saved text
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
        time.sleep(1)
        
        pyperclip.copy(content)
        driver.switch_to.active_element.send_keys(Keys.CONTROL, 'v')
        time.sleep(2)
        
        # 6. Click Publish (발행)
        publish_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., '발행')]")))
        publish_btn.click()
        time.sleep(2)
        
        # Confirm publish button (발행 팝업 내의 최종 버튼)
        confirm_btns = driver.find_elements(By.XPATH, "//button[contains(., '발행')]")
        for btn in reversed(confirm_btns):
            if btn.is_displayed() and btn != publish_btn:
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", btn)
                break
        
        print("Naver Blog post created successfully!")
        time.sleep(5) # Wait a bit before closing
        
    except Exception as e:
        print(f"Failed to post to Naver: {e}")
        print(f"Current URL at failure: {driver.current_url}")
        
        print("\n--- [페이지 텍스트 내용] ---")
        try:
            print(driver.find_element(By.TAG_NAME, "body").text[:1000])
        except:
            print("(텍스트 추출 실패)")
            
        print("\n--- [페이지 소스 (일부)] ---")
        print(driver.page_source[:2000])
        
        # Dump HTML source for debugging
        with open("error_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
            
        driver.save_screenshot("error_screenshot.png")
        print("에러 화면이 error_screenshot.png 로, 페이지 소스가 error_page.html로 저장되었습니다!")
        
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
