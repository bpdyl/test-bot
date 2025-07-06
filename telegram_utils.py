import os
import requests
import time
import logging

# TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Set this in your environment
TELEGRAM_BOT_TOKEN = '5836627566:AAFtwNffd9hEgj2M2WrMQ1SHE1m1DUnCJpw' # Set this in your environment
# TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')      # Set this in your environment
TELEGRAM_CHAT_ID = '969004992'    # Set this in your environment

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else None


def send_telegram_message(message: str) -> bool:
    """Send a message to the configured Telegram chat."""
    if not TELEGRAM_API_URL or not TELEGRAM_CHAT_ID:
        logger.error("Telegram bot token or chat ID not set.")
        return False
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown',
        }
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            logger.info("Telegram message sent successfully.")
            return True
        else:
            logger.error(f"Failed to send Telegram message: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Exception sending Telegram message: {e}")
        return False

def poll_telegram_reply(last_update_id=None, timeout=60, allowed_user_id=None) -> str:
    """Poll for a reply from the owner. Returns the text of the first new message from the allowed user."""
    if not TELEGRAM_API_URL or not TELEGRAM_CHAT_ID:
        logger.error("Telegram bot token or chat ID not set.")
        return None
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            url = f"{TELEGRAM_API_URL}/getUpdates"
            params = {'timeout': 10, 'offset': last_update_id + 1 if last_update_id else None}
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                for update in data.get('result', []):
                    update_id = update['update_id']
                    message = update.get('message', {})
                    chat_id = str(message.get('chat', {}).get('id'))
                    user_id = str(message.get('from', {}).get('id'))
                    text = message.get('text')
                    if chat_id == TELEGRAM_CHAT_ID and text \
                        and (allowed_user_id is None or user_id == allowed_user_id):
                            logger.info(f"Received Telegram reply: {text}")
                            return text, update_id
                if data.get('result'):
                    last_update_id = data['result'][-1]['update_id']
            time.sleep(2)
        except Exception as e:
            logger.error(f"Exception polling Telegram: {e}")
            time.sleep(5)
    logger.warning("No Telegram reply received in time window.")
    return None, last_update_id 