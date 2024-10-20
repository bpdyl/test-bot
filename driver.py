from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MEROSHARE_URL = "https://meroshare.cdsc.com.np/#/{}"

SUCCESSFUL_APPLICATION_TOAST = "Share has been applied successfully."


def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('-disable-dev-shn-usage')
    wd = webdriver.Chrome(options=chrome_options)
    return wd


def display_open_issues(open_issues):
    # using tabulate to format the data in terminal.
    # ref: https://stackoverflow.com/a/60635391/7429277
    import pandas as pd
    from tabulate import tabulate
    import numpy as np

    open_issues_df = pd.DataFrame(open_issues)
    open_issues_df.index = np.arange(1, len(open_issues_df) + 1)

    def tabulate_df(df):
        return tabulate(df,
                        headers='keys',
                        tablefmt='fancy_grid',
                        showindex=False)

    print(tabulate_df(open_issues_df))


class IpoBot:

    def __init__(self):
        self.__driver = get_driver()
        self.__driver.get(MEROSHARE_URL.format("login"))
        self.open_issues_selector = None
        self.open_issues = None

    def login(self, login_details, max_retry=10):
        # Wait until the loginForm is loaded.
        # Better approach than putting time.sleep()
        WebDriverWait(self.__driver, 30).until(
            EC.presence_of_all_elements_located((By.NAME, "loginForm")))

        # For DP ID selection
        self.__driver.find_element(By.ID, "selectBranch").click()
        dp_input = self.__driver.find_element(By.CLASS_NAME,
                                              "select2-search__field")
        dp_input.click()
        dp_input.send_keys(login_details["dp_id"])
        dp_input.send_keys(Keys.ENTER)

        # For username
        username_field = self.__driver.find_element(By.ID, "username")
        username_field.send_keys(login_details["username"])

        # For password
        password_field = self.__driver.find_element(By.ID, "password")
        password_field.send_keys(login_details["password"])

        # Login Button
        login_button = self.__driver.find_element(By.XPATH,
                                                  "//button[text()='Login']")
        login_button.click()

        # Wait for few seconds for error to show up if any
        self.__driver.implicitly_wait(1)

        if self.__driver.find_elements(By.CLASS_NAME, "toast-error"):
            max_retry -= 1
            if max_retry > 0:
                self.__driver.get(MEROSHARE_URL.format("login"))
                self.login(login_details)
            else:
                logger.error("Some error occurred while trying to login")
                return

        WebDriverWait(self.__driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "app-dashboard")))

        logger.info(f"Signed up successful for {login_details['alias']}")

    def navigate(self, path):
        self.__driver.get(MEROSHARE_URL.format(path))
        WebDriverWait(self.__driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "app-asba")))

        # Wait for few seconds for ipo to load
        self.__driver.implicitly_wait(3)

        WebDriverWait(self.__driver, 30).until(
            EC.presence_of_element_located(
                (By.TAG_NAME, "app-applicable-issue")))
        logger.info(f"Loaded ASBA...")

    def _get_open_issue_details(self, max_retries=3):
        open_issues_raw = [
            open_issue.text.split('\n')
            for open_issue in self.open_issues_selector
        ]
        open_issues = []
        if not open_issues_raw or not open_issues_raw[0][0]:
            # sometimes open issues doesn't load so retry thrice
            max_retries -= 1
            if max_retries > 0:
                self.navigate("asba")
                WebDriverWait(self.__driver, 30).until(
                    EC.presence_of_element_located(
                        (By.TAG_NAME, "app-applicable-issue")))
                self.open_issues_selector = self.__driver.find_elements(
                    By.CLASS_NAME, "company-list")
                self._get_open_issue_details()
            else:
                logger.warning("No open issues found")

        for idx, open_issue in enumerate(open_issues_raw, start=1):
            issue_for = open_issue[2].split('(')[0].strip()
            ticker = open_issue[2].split('(')[1].strip(')')
            open_issues.append({
                "index": idx,
                "Issue Name": open_issue[0].strip(),
                "Issued For": issue_for,
                "Ticker": ticker.strip(),
                "Type of Issue": open_issue[3].strip(),
                "Type of Share": open_issue[4].strip(),
                "Mode": open_issue[5 % len(open_issue)].strip(),
            })
        return open_issues

    def parse_open_issues(self, max_retries=3):
        WebDriverWait(self.__driver, 30).until(
            EC.presence_of_element_located(
                (By.TAG_NAME, "app-applicable-issue")))
        self.open_issues_selector = self.__driver.find_elements(
            By.CLASS_NAME, "company-list")
        self.open_issues = self._get_open_issue_details()
        display_open_issues(self.open_issues)

    def get_issue_indexes_for(self, share_type):
        if share_type == "all":
            return list(range(1, len(self.open_issues) + 1))
        elif share_type == "first":
            return [1] if self.open_issues else []
        else:
            return [
                int(d["index"]) for d in self.open_issues
                if d["Type of Share"] == share_type
            ]

    def _apply_individual_ipo(self, user_details):
        WebDriverWait(self.__driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "app-issue")))

        # Select the bank name
        self.__driver.find_element(By.XPATH,
                                   '//*[@id="selectBank"]/option[2]').click()

        # Number of units to apply
        units_to_apply = self.__driver.find_element(By.ID, "appliedKitta")
        units_to_apply.send_keys(user_details["apply_unit"])

        # Wait for few seconds for amount to auto-fill
        self.__driver.implicitly_wait(3)

        # CRN number
        crn_number = self.__driver.find_element(By.ID, "crnNumber")
        crn_number.send_keys(user_details["crn"])

        # Accept terms and conditions
        self.__driver.find_element(By.ID, "disclaimer").click()

        # Wait for Proceed button to be clickable and proceed to next page
        proceed_button_xpath = '//*[@id="main"]/div/app-issue/div/wizard/div/wizard-step[1]/form/div[2]/div/div[' \
                               '5]/div[2]/div/button[1] '
        WebDriverWait(self.__driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, proceed_button_xpath)))
        proceed_button = self.__driver.find_element(By.XPATH,
                                                    proceed_button_xpath)
        proceed_button.click()

        # Wait until the transaction pin is shown in the UI
        WebDriverWait(self.__driver, 30).until(
            EC.presence_of_element_located((By.ID, "transactionPIN")))

        # Transaction PIN
        transaction_pin = self.__driver.find_element(By.ID, "transactionPIN")
        transaction_pin.send_keys(user_details["txn_pin"])

        # Wait for Apply button to be clickable and then apply
        apply_button_xpath = '//*[@id="main"]/div/app-issue/div/wizard/div/wizard-step[2]/div[2]/div/form/div[' \
                             '2]/div/div/div/button[1] '
        WebDriverWait(self.__driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, apply_button_xpath)))
        apply_button = self.__driver.find_element(By.XPATH, apply_button_xpath)
        apply_button.click()

        # Wait for error to popup
        self.__driver.implicitly_wait(1)

        if self.__driver.find_elements(By.CLASS_NAME, "toast-error"):
            error_text = self.__driver.find_element(By.CLASS_NAME,
                                                    "toast-error").text
            logger.error("Some error occurred")
            logger.error(error_text)
            self.navigate("asba")
            return False

        if self.__driver.find_elements(By.CLASS_NAME, "toast-message"):
            toast_text = self.__driver.find_element(By.CLASS_NAME,
                                                    "toast-message").text
            if toast_text == SUCCESSFUL_APPLICATION_TOAST:
                logger.info(
                    f"Successfully applied ipo for {user_details['alias']}")
                self.navigate("asba")
                return True
        logger.warning(
            "Not able to capture the details. Please verify manually if the share is applied"
        )

    def apply_ipo(self, user_details, indices):
        success = []
        failed = []
        for index in indices:
            issue_to_apply = self.open_issues_selector[index - 1]
            if issue_to_apply.text.split('\n')[-1] != "Apply":
                logger.error("You have already applied to this IPO.")
                return
            applied_issue = issue_to_apply.text.split('\n')[2].split(
                '(')[1].strip(')')

            issue_to_apply.find_element(By.CLASS_NAME, "btn-issue").click()
            if self._apply_individual_ipo(user_details):
                # issue_to_apply = self.open_issues_selector[index-1]
                success.append([applied_issue, user_details['alias']])
            else:
                failed.append([applied_issue, user_details['alias']])
        if success:
            logger.info(f"Successful IPO applied: {success}")
        if failed:
            logger.info(f"Failed to apply IPO : {failed}")
        # return success,failed

    def quit(self):
        self.__driver.quit()


import requests
from typing import Dict, List


def fetch_investment_opportunities(category_id: int = 2) -> List[Dict]:
    params = {
    "stockSymbol": "",
    "pageNo": 1,
    "itemsPerPage": 30,
    "pagePerDisplay": 20
}
    url = "https://www.nepalipaisa.com/api/GetIpos"
    response = requests.get(url, params=params)
    if response.status_code == 200:
      ipo_data = response.json()["result"]["data"]
  
      latest_issues = []
  
      for ipo in ipo_data:
          ipo_info = {
              "id": ipo["ipoId"],
              "company_name": ipo["companyName"],
              "stock_symbol": ipo["stockSymbol"],
              "sector_name": ipo["sectorName"],
              "share_type":ipo["shareType"],
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

    # Sort the list of dictionaries based on the custom order
      sorted_ipo_data = sorted(latest_issues, key=lambda x: (custom_order.get(x["share_type"], 999), custom_order.get(x["status"], 999)))
      return sorted_ipo_data
      
    
    else:
      print(f"Request failed with status code: {response.status_code}")
