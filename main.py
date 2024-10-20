from driver import get_driver, display_open_issues, IpoBot, fetch_investment_opportunities
from file import get_user_details
from demo_mail import send_mail
from keep_alive import keep_alive
from datetime import date
import time
import logging
import pytz
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_details = get_user_details()


keep_alive()
i = 0
while True:
    latest_issues = fetch_investment_opportunities()
    print(latest_issues)
    log_tz = pytz.timezone('Asia/Kathmandu')
    log_np_time = datetime.now(log_tz).strftime("%H:%M")
    print("#################################")
    print(log_np_time)
    print("#################################")
    for issues in latest_issues:
        # # index = issues['share_type'].find(':')
        applied_users = []
        share_type = issues['share_type'].lower()
        company_name = issues['company_name']
        if any(s in share_type for s in ['general', 'public']) or share_type =='ordinary':
        # if True:
        # if issues['share_type'][:index] == 'IPO' or 'General' in issues['share_type'][:index] or 'Public':
            print(f"GENERAL IPO : {company_name}")
            start_date = issues['start_date']
            company_name = issues['company_name']
            tz = pytz.timezone('Asia/Kathmandu')
            np_time = datetime.now(tz).strftime("%H:%M")
            # if start_date == '2023-02-23' and company_name == 'Aatmanirbhar Laghubitta Bittiya Sanstha Limited':
            if start_date == str(date.today()) and np_time == "11:30":          
                ## fill ipo and send mail
                for user in user_details:
                    print(f"Lets fill the ipo for user: {user}")
                    user['username'] = f'00' + str(user['username'])
                    if user['alias'] == "Dayaram":
                        user['crn'] = f'00' + str(user['crn'])
                    try:
                        mero_share = IpoBot()
                        print(f'mero share object : {mero_share}')
                    except Exception as e:
                        logger.error(
                            "Error opening meroshare page. Please try again or after a while"
                        )
                        break
                    try:
                        mero_share.login(user)
                    except Exception as e:
                        logger.error(
                            f"Error while trying to login to {user['alias']}",
                            e)
                        continue
                    mero_share.navigate("asba")
                    mero_share.parse_open_issues()
                    indices = mero_share.get_issue_indexes_for(
                        share_type="Ordinary Shares")
                    if not indices:
                        logger.warning("No open issues found for your config.")
                        continue
                    mero_share.apply_ipo(user, indices)
                    applied_users.append(user['alias'])
                    # print(s,f)

                send_mail(f'''
          This is an automated mail so don't reply.
          IPO has been successfully applied for:
          Company Name: {company_name}
          users: {applied_users}
          Date: {date.today()}
          successfully filled: {applied_users}
          failed : 
          ''')
            else:
                print("No current ipo to fill ")
    time.sleep(60)
