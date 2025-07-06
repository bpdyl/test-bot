from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, WebDriverException
import logging
from typing import Dict, List, Optional, Tuple
from config import config
from screenshot_utils import screenshot_manager
from cache_manager import cache_manager

logger = logging.getLogger(__name__)

MEROSHARE_URL = "https://meroshare.cdsc.com.np/#/{}"
SUCCESSFUL_APPLICATION_TOAST = "Share has been applied successfully."

class EnhancedIpoBot:
    """Enhanced IPO Bot with dry run mode, caching, and screenshot capabilities"""

    def __init__(self, dry_run: bool = None):
        self.dry_run = dry_run if dry_run is not None else config.DRY_RUN_MODE
        self.__driver = None
        self.open_issues_selector = None
        self.open_issues = None
        self.current_user = None
        self.current_company = None
        
        if self.dry_run:
            logger.info("🚀 Starting IPO Bot in DRY RUN MODE - No actual applications will be made")
        else:
            logger.info("🚀 Starting IPO Bot in LIVE MODE - Applications will be processed")
            
    def _get_driver(self):
        """Get WebDriver with enhanced options"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        return webdriver.Chrome(options=chrome_options)

    def start_session(self):
        """Start a new browser session"""
        try:
            self.__driver = self._get_driver()
            self.__driver.get(MEROSHARE_URL.format("login"))
            logger.info("Browser session started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start browser session: {e}")
            return False

    def login(self, login_details: Dict, max_retry: int = 3) -> bool:
        """Enhanced login with better error handling and screenshots"""
        self.current_user = login_details.get('alias', 'Unknown')
        
        try:
            # Wait for login form
            WebDriverWait(self.__driver, 30).until(
                EC.presence_of_all_elements_located((By.NAME, "loginForm")))

            # DP ID selection
            self.__driver.find_element(By.ID, "selectBranch").click()
            dp_input = self.__driver.find_element(By.CLASS_NAME, "select2-search__field")
            dp_input.click()
            dp_input.send_keys(login_details["dp_id"])
            dp_input.send_keys(Keys.ENTER)

            # Username
            username_field = self.__driver.find_element(By.ID, "username")
            username_field.send_keys(login_details["username"])

            # Password
            password_field = self.__driver.find_element(By.ID, "password")
            password_field.send_keys(login_details["password"])

            # Login button
            login_button = self.__driver.find_element(By.XPATH, "//button[text()='Login']")
            
            if self.dry_run:
                logger.info(f"🔍 DRY RUN: Would click login button for user {self.current_user}")
                screenshot_manager.take_dry_run_screenshot(self.__driver, f"login_{self.current_user}")
            login_button.click()

            # Check for errors
            self.__driver.implicitly_wait(2)
            if self.__driver.find_elements(By.CLASS_NAME, "toast-error"):
                error_text = self.__driver.find_element(By.CLASS_NAME, "toast-error").text
                logger.error(f"Login error for {self.current_user}: {error_text}")
                screenshot_manager.take_error_screenshot(self.__driver, f"login_error_{self.current_user}")
                return False

            # Wait for dashboard
            WebDriverWait(self.__driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "app-dashboard")))

            logger.info(f"✅ Successfully logged in for {self.current_user}")
            return True

        except TimeoutException as e:
            logger.error(f"Timeout during login for {self.current_user}: {e}")
            screenshot_manager.take_error_screenshot(self.__driver, f"login_timeout_{self.current_user}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during login for {self.current_user}: {e}")
            screenshot_manager.take_error_screenshot(self.__driver, f"login_exception_{self.current_user}")
            return False

    def navigate(self, path: str) -> bool:
        """Enhanced navigation with error handling"""
        try:
            self.__driver.get(MEROSHARE_URL.format(path))
            WebDriverWait(self.__driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "app-asba")))

            self.__driver.implicitly_wait(3)
            WebDriverWait(self.__driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "app-applicable-issue")))
            
            logger.info(f"✅ Successfully navigated to {path}")
            return True

        except Exception as e:
            logger.error(f"Navigation error to {path}: {e}")
            screenshot_manager.take_error_screenshot(self.__driver, f"navigation_error_{path}")
            return False

    def parse_open_issues(self, max_retries: int = 3) -> bool:
        """Enhanced issue parsing with caching"""
        cache_key = f"open_issues_{self.current_user}"
        
        # Try to get from cache first
        cached_issues = cache_manager.get(cache_key)
        if cached_issues:
            self.open_issues = cached_issues
            logger.info(f"📋 Using cached open issues for {self.current_user}")
            return True

        for attempt in range(max_retries):
            try:
                WebDriverWait(self.__driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "app-applicable-issue")))
                
                self.open_issues_selector = self.__driver.find_elements(By.CLASS_NAME, "company-list")
                
                if not self.open_issues_selector:
                    logger.warning(f"No open issues found for {self.current_user}")
                    return False

                # Parse issues
                open_issues_raw = [issue.text.split('\n') for issue in self.open_issues_selector]
                self.open_issues = []
                
                for idx, issue in enumerate(open_issues_raw, start=1):
                    if not issue or not issue[0]:
                        continue
                        
                    issue_for = issue[2].split('(')[0].strip() if len(issue) > 2 else ""
                    ticker = issue[2].split('(')[1].strip(')') if len(issue) > 2 and '(' in issue[2] else ""
                    
                    self.open_issues.append({
                        "index": idx,
                        "Issue Name": issue[0].strip(),
                        "Issued For": issue_for,
                        "Ticker": ticker,
                        "Type of Issue": issue[3].strip() if len(issue) > 3 else "",
                        "Type of Share": issue[4].strip() if len(issue) > 4 else "",
                        "Mode": issue[5].strip() if len(issue) > 5 else "",
                    })

                # Cache the results
                cache_manager.set(cache_key, self.open_issues)
                logger.info(f"📋 Successfully parsed {len(self.open_issues)} open issues for {self.current_user}")
                return True

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed to parse issues: {e}")
                if attempt == max_retries - 1:
                    screenshot_manager.take_error_screenshot(self.__driver, f"parse_issues_error_{self.current_user}")
                    return False
                continue

        return False

    def get_issue_indexes_for(self, share_type: str) -> List[int]:
        """Get issue indexes for specific share type"""
        if not self.open_issues:
            return []
            
        if share_type == "all":
            return list(range(1, len(self.open_issues) + 1))
        elif share_type == "first":
            return [1] if self.open_issues else []
        else:
            return [
                int(d["index"]) for d in self.open_issues
                if d["Type of Share"] == share_type
            ]

    def apply_ipo(self, user_details: Dict, indices: List[int], company_name: str = "") -> Tuple[List, List]:
        """Enhanced IPO application with dry run mode and screenshots"""
        self.current_company = company_name
        success = []
        failed = []
        
        logger.info(f"🎯 Starting IPO application for {self.current_user} - Company: {company_name}")
        logger.info(f"📊 Dry run mode: {self.dry_run}")
        
        for index in indices:
            try:
                issue_to_apply = self.open_issues_selector[index - 1]
                issue_name = issue_to_apply.text.split('\n')[0] if issue_to_apply.text else "Unknown"
                
                logger.info(f"📝 Processing issue {index}: {issue_name}")
                
                # Check if already applied
                if issue_to_apply.text.split('\n')[-1] != "Apply":
                    logger.warning(f"⚠️ Already applied to issue {index}: {issue_name}")
                    continue

                # Click apply button
                if self.dry_run:
                    logger.info(f"🔍 DRY RUN: Would click apply button for issue {index}: {issue_name}")
                    screenshot_manager.take_dry_run_screenshot(self.__driver, f"apply_{index}_{self.current_user}")
                issue_to_apply.find_element(By.CLASS_NAME, "btn-issue").click()

                # Apply individual IPO
                if self._apply_individual_ipo(user_details, issue_name):
                    success.append([issue_name, user_details['alias']])
                    logger.info(f"✅ Successfully applied to {issue_name}")
                else:
                    failed.append([issue_name, user_details['alias']])
                    logger.error(f"❌ Failed to apply to {issue_name}")

            except Exception as e:
                logger.error(f"❌ Error processing issue {index}: {e}")
                screenshot_manager.take_error_screenshot(self.__driver, f"apply_error_{index}_{self.current_user}")
                failed.append([f"Issue {index}", user_details['alias']])

        logger.info(f"📊 Application Summary for {self.current_user}:")
        logger.info(f"   ✅ Successful: {len(success)}")
        logger.info(f"   ❌ Failed: {len(failed)}")
        
        return success, failed

    def _apply_individual_ipo(self, user_details: Dict, issue_name: str) -> bool:
        """Apply individual IPO with enhanced error handling"""
        try:
            WebDriverWait(self.__driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "app-issue")))

            # Select bank
            self.__driver.find_element(By.XPATH, '//*[@id="selectBank"]/option[2]').click()

            # select account number
            account_number_dropdown = WebDriverWait(self.__driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="accountNumber"]'))
                )
            account_number_dropdown.click()

            account_number_select = WebDriverWait(self.__driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="accountNumber"]/option[2]'))
            )
            account_number_select.click()
            
            # Units to apply
            units_field = self.__driver.find_element(By.ID, "appliedKitta")
            if self.dry_run:
                logger.info(f"🔍 DRY RUN: Would enter {user_details['apply_unit']} units")
            units_field.send_keys(user_details["apply_unit"])

            self.__driver.implicitly_wait(3)

            # CRN number
            crn_field = self.__driver.find_element(By.ID, "crnNumber")
            if self.dry_run:
                logger.info(f"🔍 DRY RUN: Would enter CRN: {user_details['crn']}")
            crn_field.send_keys(user_details["crn"])

            # Accept terms
            disclaimer_checkbox = self.__driver.find_element(By.ID, "disclaimer")
            if self.dry_run:
                logger.info("🔍 DRY RUN: Would accept terms and conditions")
            disclaimer_checkbox.click()

            # Proceed button
            proceed_button_xpath = '//*[@id="main"]/div/app-issue/div/wizard/div/wizard-step[1]/form/div[2]/div/div[5]/div[2]/div/button[1]'
            WebDriverWait(self.__driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, proceed_button_xpath)))
            
            if self.dry_run:
                logger.info("🔍 DRY RUN: Would click proceed button")
                screenshot_manager.take_dry_run_screenshot(self.__driver, f"proceed_{self.current_user}")
            proceed_button = self.__driver.find_element(By.XPATH, proceed_button_xpath)
            proceed_button.click()

            # Transaction PIN
            WebDriverWait(self.__driver, 30).until(
                EC.presence_of_element_located((By.ID, "transactionPIN")))
            
            txn_pin_field = self.__driver.find_element(By.ID, "transactionPIN")
            if self.dry_run:
                logger.info(f"🔍 DRY RUN: Would enter transaction PIN")
            txn_pin_field.send_keys(user_details["txn_pin"])

            # Apply button
            apply_button_xpath = '//*[@id="main"]/div/app-issue/div/wizard/div/wizard-step[2]/div[2]/div/form/div[2]/div/div/div/button[1]'
            WebDriverWait(self.__driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, apply_button_xpath)))
            
            if self.dry_run:
                logger.info("🔍 DRY RUN: Would click apply button")
                screenshot_manager.take_dry_run_screenshot(self.__driver, f"apply_final_{self.current_user}")
            else:
                apply_button = self.__driver.find_element(By.XPATH, apply_button_xpath)
                apply_button.click()

            # Check for errors
            self.__driver.implicitly_wait(2)
            if self.__driver.find_elements(By.CLASS_NAME, "toast-error"):
                error_text = self.__driver.find_element(By.CLASS_NAME, "toast-error").text
                logger.error(f"Application error: {error_text}")
                screenshot_manager.take_error_screenshot(self.__driver, f"apply_error_{self.current_user}")
                self.navigate("asba")
                return False

            # Check for success
            if self.__driver.find_elements(By.CLASS_NAME, "toast-message"):
                toast_text = self.__driver.find_element(By.CLASS_NAME, "toast-message").text
                if toast_text == SUCCESSFUL_APPLICATION_TOAST:
                    logger.info(f"✅ Successfully applied IPO for {user_details['alias']}")
                    self.navigate("asba")
                    return True

            logger.warning("⚠️ Could not determine application status")
            screenshot_manager.take_debug_screenshot(self.__driver, f"unknown_status_{self.current_user}")
            self.navigate("asba")
            return False

        except Exception as e:
            logger.error(f"❌ Error in individual IPO application: {e}")
            screenshot_manager.take_error_screenshot(self.__driver, f"individual_apply_error_{self.current_user}")
            return False

    def quit(self):
        """Safely quit the driver"""
        if self.__driver:
            try:
                self.__driver.quit()
                logger.info("Browser session closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser session: {e}")

# Enhanced fetch function with caching
def fetch_investment_opportunities_enhanced(category_id: int = 2) -> List[Dict]:
    """Enhanced fetch function with caching"""
    cache_key = "investment_opportunities"
    
    # Try to get from cache first
    cached_data = cache_manager.get(cache_key)
    if cached_data:
        logger.info("📋 Using cached investment opportunities")
        return cached_data

    # Fetch fresh data
    import requests
    params = {
        "stockSymbol": "",
        "pageNo": 1,
        "itemsPerPage": 30,
        "pagePerDisplay": 20
    }
    
    url = "https://www.nepalipaisa.com/api/GetIpos"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            ipo_data = response.json()["result"]["data"]
            
            latest_issues = []
            
            for ipo in ipo_data:
                ipo_info = {
                    "id": ipo["ipoId"],
                    "company_name": ipo["companyName"],
                    "stock_symbol": ipo["stockSymbol"],
                    "sector_name": ipo["sectorName"],
                    "share_type": ipo["shareType"],
                    "price_per_unit": ipo["pricePerUnit"],
                    "units": ipo["units"],
                    "start_date": ipo["openingDateAD"],
                    "end_date": ipo["closingDateAD"],
                    "status": ipo["status"]
                }
                latest_issues.append(ipo_info)
                
            custom_order = {
                'ordinary': 0,
                'Open': 0,
                'Nearing': 1,
                'Closed': 2,
            }
            
            sorted_ipo_data = sorted(
                latest_issues, 
                key=lambda x: (custom_order.get(x["share_type"], 999), custom_order.get(x["status"], 999))
            )
            
            # Cache the results
            cache_manager.set(cache_key, sorted_ipo_data)
            logger.info(f"📊 Fetched {len(sorted_ipo_data)} investment opportunities")
            
            return sorted_ipo_data
        else:
            logger.error(f"Request failed with status code: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching investment opportunities: {e}")
        return [] 