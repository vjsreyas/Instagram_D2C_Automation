import os
import sys
import json
import hmac
import hashlib
import threading
import requests

from flask import Flask, request
from dotenv import load_dotenv
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials


load_dotenv()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
BUSINESS_ID = os.getenv("BUSSINESS_ID")
OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")
APP_SECRET = os.getenv("APP_SECRET")

app = Flask(__name__)
openai_client = OpenAI(api_key=OPEN_AI_API_KEY)


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=SCOPES
)

gs_client = gspread.authorize(creds)


sheet = gs_client.open_by_key(
    "11UezMmW9xMM7dGwpcqsYPdn9beBQE01TjS02rjGjiWs"
).sheet1

def log(message):
    print(message)
    sys.stdout.flush()

def get_property_by_media(media_id):
    records = sheet.get_all_records()
    for row in records:
        if str(row["media_id"]) == str(media_id):
            return row
    return None

def is_valid_signature(req):
    signature = req.headers.get("X-Hub-Signature-256")

    if not signature or not APP_SECRET:
        return True

    expected_hash = signature.split("=")[1]

    computed_hash = hmac.new(
        APP_SECRET.encode(),
        req.data,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_hash, expected_hash)

def build_property_prompt(property_data, user_message):
    return f"""
You are a professional real estate assistant.

Property Details:
Title: {property_data['title']}
Price: {property_data['price']}
Rent: {property_data['rent']}
Location: {property_data['location']}
BHK: {property_data['bhk']}
Size: {property_data['sqft']} sqft
Amenities: {property_data['amenities']}
Description: {property_data['description']}

Answer ONLY using the above property data.
Keep reply under 30 words.

User question: {user_message}
"""

def generate_ai_reply(prompt):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.4,
            max_tokens=120
        )
        return response.choices[0].message.content
    except Exception as e:
        log(f"AI Error: {e}")
        return "Please contact the agent for more details."

def send_request(url, payload, label):
    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            log(f"{label} sent")
        else:
            log(f"{label} failed: {r.text}")
    except Exception as e:
        log(f"Network error ({label}): {e}")

def handle_comment(comment_id, comment_text, media_id):

    property_data = get_property_by_media(media_id)

    if not property_data:
        log("No property mapped to this media_id")
        return

    url_public = f"https://graph.facebook.com/v24.0/{comment_id}/replies"
    payload_public = {
        "message": "Sent you the details in DM 📩",
        "access_token": ACCESS_TOKEN
    }
    send_request(url_public, payload_public, "Public reply")

    prompt = build_property_prompt(property_data, comment_text)
    private_reply = generate_ai_reply(prompt)

    url_private = f"https://graph.facebook.com/v24.0/me/messages?access_token={ACCESS_TOKEN}"
    payload_private = {
        "recipient": {"comment_id": comment_id},
        "message": {"text": private_reply}
    }
    send_request(url_private, payload_private, "Private DM")

@app.route("/webhook", methods=["GET"])
def verify():
    if (
        request.args.get("hub.mode") == "subscribe"
        and request.args.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return request.args.get("hub.challenge"), 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook():

    if not is_valid_signature(request):
        return "Forbidden", 403

    data = request.json

    if data.get("object") != "instagram":
        return "Ignored", 200

    for entry in data.get("entry", []):

        if "changes" in entry:
            for change in entry["changes"]:
                if change.get("field") == "comments":
                    value = change.get("value", {})

                    if value.get("from", {}).get("id") == BUSINESS_ID:
                        continue

                    comment_id = value.get("id")
                    comment_text = value.get("text", "").lower()
                    media_id = value.get("media", {}).get("id")

                    threading.Thread(
                        target=handle_comment,
                        args=(comment_id, comment_text, media_id)
                    ).start()

    return "EVENT_RECEIVED", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)