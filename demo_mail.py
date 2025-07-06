from file import get_mail_cred
mail_cred = get_mail_cred()
import smtplib
from email.message import EmailMessage
# print((mail_cred))
cred1 = mail_cred[0]['cred1']
cred2 = mail_cred[0]['cred2']

def send_mail(msg_content):
  msg = EmailMessage()
  msg.set_content(msg_content)

  msg['Subject'] = 'Subject IPO Filled'
  msg['From'] = 'ipobot_noreply@gmail.com'
  msg['To'] = ['bibekpaudyal23@gmail.com']
  server=smtplib.SMTP('smtp.gmail.com',587)
  server.starttls()
  server.login(cred1,cred2)
  server.send_message(msg)
  server.quit()

  print('Mail sent')
                                                                                        