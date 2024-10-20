import os
import json
import gspread

# Read the credentials JSON from the environment variable
creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')

if not creds_json:
    raise Exception("GOOGLE_SHEETS_CREDENTIALS environment variable not set")

# Parse the JSON string into a dictionary
creds_dict = json.loads(creds_json)

# Authorize using the credentials dictionary
client = gspread.service_account_from_dict(creds_dict)

def get_user_details():
    sheet = client.open("ipo").sheet1
    return sheet.get_all_records()

def get_mail_cred():
    cred_sheet = client.open("ipo").get_worksheet(1)
    return cred_sheet.get_all_records()
