from flask import Flask
from datetime import datetime, timezone, date
from flask.templating import render_template
from threading import Thread
import pytz
import logging
from driver import fetch_investment_opportunities

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

app = Flask('')


@app.route('/')
def home():
    tz = pytz.timezone('Asia/Kathmandu')
    np_time = datetime.now(tz)
    print("--------------------------------")
    logger.info(np_time)
    print("--------------------------------")
    upcoming_ipos = fetch_investment_opportunities()
    return render_template('display.html', web_data=upcoming_ipos)


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()
