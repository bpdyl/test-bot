from driver import EnhancedIpoBot, fetch_investment_opportunities_enhanced
from file import get_user_details
from demo_mail import send_mail
from keep_alive import keep_alive
from datetime import date, datetime
import time
import logging
import pytz
from config import config
from logger_setup import setup_logger
from cache_manager import cache_manager
from screenshot_utils import screenshot_manager
from ipo_status_manager import (
    get_unfilled_ipos_for_users, mark_ipo_filled_for_user, sync_status_with_open_issues,
    ignore_ipo, clear_expired_ignores, needs_status_sync
)
from telegram_utils import send_telegram_message, poll_telegram_reply

# Setup enhanced logging
setup_logger()
logger = logging.getLogger(__name__)

def get_user_details_safe():
    """Safely get user details with error handling"""
    try:
        user_details = get_user_details()
        logger.info(f"📋 Loaded {len(user_details)} user configurations")
        return user_details
    except Exception as e:
        logger.error(f"❌ Failed to load user details: {e}")
        return []

def check_ipo_eligibility(ipo_data):
    """Check if IPO is eligible for application"""
    share_type = ipo_data['share_type'].lower()
    company_name = ipo_data['company_name']
    status = ipo_data['status']
    # Check if it's a general/public IPO
    if (any(s in share_type for s in ['general', 'public']) or share_type == 'ordinary') and status.lower() == 'open':
        logger.info(f"✅ Eligible IPO found: {company_name} ({share_type})")
        return True
    else:
        logger.debug(f"⏭️ Skipping non-eligible IPO: {company_name} ({share_type})")
        return False

def check_timing_conditions(ipo_data):
    """Check if current time matches IPO application conditions"""
    start_date = ipo_data['start_date']
    end_date = ipo_data['end_date']
    company_name = ipo_data['company_name']
    
    tz = pytz.timezone('Asia/Kathmandu')
    current_time = datetime.now(tz)
    current_date = current_time.strftime("%Y-%m-%d")
    current_time_str = current_time.strftime("%H:%M")
    
    # Check if IPO is open
    if not start_date <= current_date <= end_date:
        logger.debug(f"⏭️ IPO {company_name} not open today ({start_date} to {end_date}, now {current_date})")
        return False
    
    # Optionally, check time window here
    # logger.info(f"⏰ Checking time: {current_time_str}")
    logger.info(f"⏰ IPO {company_name} is open for application at {current_time_str}")
    return True

def process_user_application(user, company_name, bot, ipo_id, open_issues_for_user, api_ipo_list):
    """Process IPO application for a single user and update status"""
    logger.info(f"👤 Processing application for user: {user['alias']}")
    try:
        # Format user data
        user['username'] = f'00{user["username"]}'
        if user['alias'] == "Dayaram":
            user['crn'] = f'00{user["crn"]}'
        
        # Start browser session
        if not bot.start_session():
            logger.error(f"❌ Failed to start browser session for {user['alias']}")
            return False, "Browser session failed"
        
        # Login
        if not bot.login(user):
            logger.error(f"❌ Login failed for {user['alias']}")
            return False, "Login failed"
        
        # Navigate to ASBA
        if not bot.navigate("asba"):
            logger.error(f"❌ Navigation failed for {user['alias']}")
            return False, "Navigation failed"
        
        # Parse open issues
        if not bot.parse_open_issues():
            logger.error(f"❌ Failed to parse open issues for {user['alias']}")
            return False, "Parse issues failed"
        
        # Sync status: if IPO is not in open issues, mark as filled
        sync_status_with_open_issues(bot.open_issues, [user['alias']], api_ipo_list)
        
        # Get issue indexes
        indices = bot.get_issue_indexes_for("Ordinary Shares")
        if not indices:
            logger.warning(f"⚠️ No open issues found for {user['alias']}")
            return False, "No open issues found"
        
        # Apply IPO
        success, failed = bot.apply_ipo(user, indices, company_name)
        
        if success:
            logger.info(f"✅ Successfully applied {len(success)} IPOs for {user['alias']}")
            mark_ipo_filled_for_user(str(ipo_id), user['alias'])
            return True, f"Applied {len(success)} IPOs"
        else:
            logger.error(f"❌ Failed to apply any IPOs for {user['alias']}")
            return False, "Application failed"
    except Exception as e:
        logger.error(f"❌ Unexpected error processing {user['alias']}: {e}")
        return False, f"Unexpected error: {str(e)}"
    finally:
        bot.quit()

def main():
    logger.info("🚀 Starting Enhanced IPO Bot with Telegram approval, status sync, and ignore support")
    logger.info(f"📊 Configuration: {config.to_dict()}")
    user_details = get_user_details_safe()
    if not user_details:
        logger.error("❌ No user details available. Exiting.")
        return
    user_aliases = [u['alias'] for u in user_details]
    keep_alive()
    iteration = 0
    last_update_id = None
    while True:
        iteration += 1
        logger.info(f"🔄 Starting iteration {iteration}")
        
        try:
            clear_expired_ignores()  # Clean up old ignores
            latest_issues = fetch_investment_opportunities_enhanced()
            if not latest_issues:
                logger.warning("⚠️ No investment opportunities found")
                time.sleep(config.CHECK_INTERVAL_SECONDS)
                continue
            
            logger.info(f"📊 Found {len(latest_issues)} investment opportunities")
            
            # Log current time
            log_tz = pytz.timezone('Asia/Kathmandu')
            log_np_time = datetime.now(log_tz).strftime("%H:%M")
            # Filter eligible IPOs
            eligible_ipos = [ipo for ipo in latest_issues if check_ipo_eligibility(ipo) and check_timing_conditions(ipo)]
            
            # Only run status sync if there are eligible IPOs that might need updates
            if eligible_ipos and needs_status_sync(eligible_ipos):
                logger.info("🔄 Status sync needed - running dry run mode for all users")
                screenshot_manager.cleanup_dry_run_screenshots()  # Clean up before new dry runs
                sync_start_time = time.time()
                
                for user in user_details:
                    bot = EnhancedIpoBot(dry_run=True)  # dry_run to avoid side effects
                    if not bot.start_session():
                        continue
                    if not bot.login(user):
                        bot.quit()
                        continue
                    if not bot.navigate("asba"):
                        bot.quit()
                        continue
                    if not bot.parse_open_issues():
                        bot.quit()
                        continue
                    sync_status_with_open_issues(bot.open_issues, [user['alias']], latest_issues)
                    bot.quit()
                
                sync_duration = time.time() - sync_start_time
                logger.info(f"✅ Status sync completed in {sync_duration:.2f} seconds")
            else:
                logger.info("⏭️ No status sync needed - skipping dry run mode")
            
            # Only alert for IPOs not filled and not ignored
            unfilled_ipos = get_unfilled_ipos_for_users(eligible_ipos, user_aliases)
            if not unfilled_ipos:
                logger.info("No unfilled IPOs for any user. Waiting...")
                time.sleep(config.CHECK_INTERVAL_SECONDS)
                continue
            # Send Telegram alert
            alert_lines = ["*IPO Alert!* The following IPOs are available and not filled for all users:"]
            
            alert_lines.extend(f"- {ipo['company_name']} (ID: {ipo['id']}) | Unfilled users: {', '.join(ipo['unfilled_users'])}" for ipo in unfilled_ipos)
            alert_lines.append("\nReply with the IPO name or ID to proceed, or 'ignore <id>' to skip for 24h.")
            send_telegram_message('\n'.join(alert_lines))
            # Wait for reply
            logger.info("Waiting for Telegram reply with IPO name/ID or ignore command...")
            reply, last_update_id = poll_telegram_reply(last_update_id=last_update_id, timeout=600)
            if not reply:
                logger.info("No Telegram reply received. Skipping this round.")
                time.sleep(config.CHECK_INTERVAL_SECONDS)
                continue
            reply = reply.strip().lower()
            # Handle ignore/skip command
            if reply.startswith('ignore ') or reply.startswith('skip '):
                _, ignore_id = reply.split(maxsplit=1)
                for ipo in unfilled_ipos:
                    if ignore_id in str(ipo['id']).lower() or ignore_id in ipo['company_name'].lower():
                        ignore_ipo(str(ipo['id']))
                        send_telegram_message(f"IPO {ipo['company_name']} (ID: {ipo['id']}) will be ignored for 24 hours.")
                        break
                time.sleep(config.CHECK_INTERVAL_SECONDS)
                continue
            # Find IPO by name or ID
            selected_ipo = None
            for ipo in unfilled_ipos:
                if reply in str(ipo['id']).lower() or reply in ipo['company_name'].lower():
                    selected_ipo = ipo
                    break
            if not selected_ipo:
                logger.warning(f"No matching IPO found for reply: {reply}")
                send_telegram_message(f"No matching IPO found for '{reply}'. Please try again.")
                time.sleep(config.CHECK_INTERVAL_SECONDS)
                continue
            # Apply for selected IPO for all unfilled users
            applied_users = []
            failed_users = []
            for user in user_details:
                if user['alias'] not in selected_ipo['unfilled_users']:
                    continue
                bot = EnhancedIpoBot()
                # Fetch open issues for this user for sync
                open_issues_for_user = []
                if bot.start_session() and bot.login(user) and bot.navigate("asba") and bot.parse_open_issues():
                    open_issues_for_user = bot.open_issues
                success, message = process_user_application(user, selected_ipo['company_name'], bot, selected_ipo['id'], open_issues_for_user, latest_issues)
                if success:
                    applied_users.append(user['alias'])
                else:
                    failed_users.append(f"{user['alias']}: {message}")
            # If any failures, alert only for failed users for this IPO
            if failed_users:
                fail_msg = f"Failed to apply for IPO {selected_ipo['company_name']} (ID: {selected_ipo['id']}) for: {failed_users}"
                send_telegram_message(fail_msg)
            # Send email and Telegram notification
            summary = f"""
IPO Application Summary:\nCompany Name: {selected_ipo['company_name']}\nDate: {date.today()}\nTime: {log_np_time}\n\nSuccessfully applied: {applied_users}\nFailed applications: {failed_users}\n\nConfiguration:\n- Dry Run Mode: {config.DRY_RUN_MODE}\n- Caching Enabled: {config.ENABLE_CACHING}\n- Screenshots Enabled: {config.ENABLE_SCREENSHOTS}\n"""
            try:
                send_mail(summary)
                send_telegram_message(summary)
                logger.info("📧 Email and Telegram notification sent")
            except Exception as e:
                logger.error(f"❌ Failed to send notification: {e}")
            screenshot_manager.cleanup_old_screenshots()
            cache_stats = cache_manager.get_cache_stats()
            logger.info(f"📊 Cache stats: {cache_stats}")
            screenshot_stats = screenshot_manager.get_screenshot_stats()
            logger.info(f"📸 Screenshot stats: {screenshot_stats}")
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal. Shutting down gracefully...")
            break
        except Exception as e:
            logger.error(f"❌ Unexpected error in main loop: {e}")
            time.sleep(config.CHECK_INTERVAL_SECONDS)
            continue
        
        # Wait before next iteration
        logger.info(f"⏳ Waiting {config.CHECK_INTERVAL_SECONDS} seconds before next check...")
        time.sleep(config.CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()