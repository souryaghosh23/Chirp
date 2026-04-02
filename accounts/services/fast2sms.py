from twilio.rest import Client
import os
from dotenv import load_dotenv
import requests, secrets, logging, hashlib

load_dotenv()
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

# Find your Account SID and Auth Token in the 
url = "https://www.fast2sms.com/dev/bulkV2"
headers = {
    "accept": "application/json",
    "authorization": os.getenv('FAST2API'),
    "content-type": "application/json"
}


def send_otp(phone_number, channel='sms'):
    """
    Sends an OTP to the specified phone number via the chosen channel.
    """
    otp = str(secrets.randbelow(900000) + 100000)
    code= hashlib.sha256(otp.encode()).hexdigest()

    payload = {
    "route": "q",
    "message": f"Your Chirp verification code is: {otp}.\
    Don't share this code with anyone; our employees will never ask for the code",
    "numbers": phone_number,
    "sms_details": "1"
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
    except Exception as e:
        logging.error(f"Couldn't generate otp due to {str(e)}")
        code = None

    return code
