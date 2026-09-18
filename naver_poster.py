import time
import os
import pyperclip
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from config import CHROME_PROFILE_DIR, NAVER_BLOG_ID


class NaverPoster:
    """네이버 스마트에디터 ONE 자동 포스팅 엔진 (크롬 세션 유지형)"""

    def __init__(self, blog_id: str = NAVER_BLOG_ID, headless: bool = False):
        self.blog_id = blog_id
        self.headless = headless
        self.driver = None

    def init_driver(self):
        """사용자 Chrome 프로필을 물고 실행되는 안전한 웹드라이버 생성"""
        chrome_options = Options()
        # 로그인 세션이 보존되는 전용 프로필 폴더 지정
        chrome_options.add_argument(f"--user-data-dir={str(CHROME_PROFILE_DIR)}")
        chrome_options.add_argument("--profile-directory=Default")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        if self.headless:
            chrome_options.add_argument("--headless=new")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def check_login_status(self) -> bool:
        """현재 크롬 브라우저가 네이버에 로그인되어 있는지 확인"""
        if not self.driver:
            self.init_driver()

        self.driver.get("https://www.naver.com")
        time.sleep(2)
        
        # 환경변수에 로그인 쿠키가 설정되어 있다면 주입 (GitHub Actions 용)
        nid_aut = os.getenv("NID_AUT")
        nid_ses = os.getenv("NID_SES")
        if nid_aut and nid_ses:
            print("[안내] 환경변수에서 네이버 로그인 쿠키를 발견하여 주입합니다.")
            self.driver.add_cookie({"name": "NID_AUT", "value": nid_aut, "domain": ".naver.com"})
            self.driver.add_cookie({"name": "NID_SES", "value": nid_ses, "domain": ".naver.com"})
            self.driver.refresh()
            time.sleep(2)

        # 네이버 메인에서 로그인 쿠키(NID_AUT, NID_SES) 존재 여부 확인
        cookies = {c["name"]: c["value"] for c in self.driver.get_cookies()}
        if "NID_AUT" in cookies or "NID_SES" in cookies:
            return True

        # 2차 확인: 블로그 글쓰기 페이지 진입 시도
        self.driver.get(f"https://blog.naver.com/{self.blog_id}/postwrite")
        time.sleep(3)
        if "nidlogin" not in self.driver.current_url:
            return True

        return False

    def wait_for_user_manual_login(self, timeout_sec: int = 180) -> bool:
        """최초 1회 사용자가 직접 네이버 브라우저에서 로그인할 때까지 대기"""
        if not self.driver:
            self.init_driver()

        self.driver.get("https://nid.naver.com/nidlogin.login")
        print("=" * 60)
        print("[안내] 브라우저 창이 열렸습니다.")
        print("네이버 계정(cjm7054)으로 로그인해 주세요! (로그인 완료 후 네이버 메인으로 이동하면 자동 감지됩니다)")
        print(f"제한 시간: {timeout_sec}초")
        print("=" * 60)

        start = time.time()
        while time.time() - start < timeout_sec:
            try:
                cookies = {c["name"]: c["value"] for c in self.driver.get_cookies()}
                if "NID_AUT" in cookies or "NID_SES" in cookies:
                    print("[성공] 네이버 로그인 쿠키가 확인되었습니다! 세션이 영구 저장됩니다.")
                    time.sleep(2)
                    return True
                if "nidlogin" not in self.driver.current_url and "naver.com" in self.driver.current_url:
                    print("[성공] 네이버 로그인이 확인되었습니다!")
                    time.sleep(2)
                    return True
            except Exception:
                pass
            time.sleep(2)

        print("[타임아웃] 로그인 대기 시간이 초과되었습니다.")
        return False

    def post_article(self, title: str, content: str, tags: list = None, publish: bool = False) -> bool:
        """스마트에디터 ONE에 글 작성 및 발행 (또는 임시저장)"""
        if not self.driver:
            self.init_driver()

        write_url = f"https://blog.naver.com/{self.blog_id}/postwrite"
        self.driver.get(write_url)
        time.sleep(4)

        # 로그인 풀림 체크
        if "nidlogin" in self.driver.current_url:
            print("[오류] 네이버 로그인이 풀려있습니다. 먼저 로그인을 완료해야 합니다.")
            return False

        try:
            # 1. 팝업 / 도움말 창 닫기 처리 (스마트에디터 작성 시 뜨는 팝업)
            self._close_popups()

            # 2. 제목 입력
            print(f"[진행] 제목 입력 중: {title}")
            from selenium.webdriver.common.action_chains import ActionChains
            
            # 스마트에디터 ONE의 제목 영역 클릭 및 붙여넣기
            self.driver.execute_script("""
                var titleEl = document.querySelector('.se-documentTitle p, .se-documentTitle textarea, .se-title-text, .se-documentTitle');
                if (titleEl) {
                    titleEl.focus();
                    titleEl.click();
                }
            """)
            time.sleep(1)
            pyperclip.copy(title)
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(1)

            # 3. 본문 입력
            print("[진행] 본문 내용 입력 중...")
            ActionChains(self.driver).send_keys(Keys.TAB).perform()
            time.sleep(0.5)
            # 본문 포커스 직접 부여
            self.driver.execute_script("""
                var contentEl = document.querySelector('.se-main-container [contenteditable="true"], .se-component-content [contenteditable="true"], .se-main-container');
                if (contentEl) {
                    contentEl.focus();
                    contentEl.click();
                }
            """)
            time.sleep(1)
            pyperclip.copy(content)
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(2)

            # 4. 발행 버튼 또는 임시저장 버튼 클릭
            if publish:
                print("[진행] 네이버 블로그에 공식 발행(Publish)을 진행합니다.")
                publish_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn_publish') or contains(., '발행')]"))
                )
                self.driver.execute_script("arguments[0].click();", publish_btn)
                time.sleep(3)

                # 태그 입력 (발행 레이어 팝업 내)
                if tags:
                    try:
                        tag_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder*='태그'], .tag_input input")
                        for t in tags[:10]:
                            tag_clean = t.replace("#", "").strip()
                            tag_input.send_keys(tag_clean)
                            tag_input.send_keys(Keys.ENTER)
                            time.sleep(0.3)
                    except Exception as tag_err:
                        print(f"[알림] 태그 입력 건너뜀: {tag_err}")

                # 최종 발행 확인 버튼 클릭
                confirm_btn = None
                confirm_selectors = [
                    "button.confirm_btn",
                    "button[data-action='publish']",
                    "button[class*='btn_confirm']",
                    "button[class*='button_apply']",
                    "button[class*='btn_apply']",
                    ".publish_btn_box button",
                    "div[class*='layer_publish'] button[class*='confirm']",
                    "div[class*='publish_layer'] button[class*='confirm']"
                ]
                
                for c_sel in confirm_selectors:
                    try:
                        btn = self.driver.find_element(By.CSS_SELECTOR, c_sel)
                        if btn.is_displayed():
                            confirm_btn = btn
                            break
                    except Exception:
                        continue
                        
                if not confirm_btn:
                    # fallback: 화면에 보이는 '발행' 텍스트를 가진 마지막 버튼 찾기
                    confirm_btns = self.driver.find_elements(By.XPATH, "//button[contains(., '발행')]")
                    for btn in reversed(confirm_btns):
                        if btn.is_displayed() and btn != publish_btn:
                            confirm_btn = btn
                            break
                            
                if confirm_btn:
                    self.driver.execute_script("arguments[0].click();", confirm_btn)
                    print("[완료] 글이 성공적으로 발행되었습니다!")
                    time.sleep(5)
                else:
                    raise Exception("최종 발행 확인 버튼을 찾을 수 없습니다.")
            else:
                # 안전한 임시저장
                print("[진행] 테스트 모드: 본문을 임시저장합니다.")
                save_btn = self.driver.find_element(By.CSS_SELECTOR, "button.btn_save, button[data-click-area*='save']")
                self.driver.execute_script("arguments[0].click();", save_btn)
                time.sleep(2)
                print("[완료] 글이 임시저장되었습니다.")

            return True

        except Exception as e:
            print(f"[오류] 포스팅 중 에러 발생: {e}")
            return False

    def _close_popups(self):
        """글쓰기 시 등장하는 '작성 중인 글이 있습니다' or '도움말' 팝업 자동 취소"""
        time.sleep(2)
        # 스마트에디터 레이어 팝업(이어쓰기 취소 등)
        popup_selectors = [
            ".se-popup-button-cancel",
            "button.se-popup-button-cancel",
            ".se-help-panel-close-button",
            "button.btn_close",
            ".pop_close"
        ]
        for sel in popup_selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for btn in buttons:
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
            except:
                pass

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None


if __name__ == "__main__":
    poster = NaverPoster()
    poster.init_driver()
    if not poster.check_login_status():
        poster.wait_for_user_manual_login(60)
    poster.close()
