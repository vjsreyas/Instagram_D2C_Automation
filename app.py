import os
from flask import Flask, request
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

def reply_public(comment_id, message_text):
    url = f"https://graph.facebook.com/v18.0/{comment_id}/replies"
    payload = {
        "message": message_text,
        "access_token": ACCESS_TOKEN
    }
    try:
        requests.post(url, json=payload)
        print(f"(Public)✅ Reply sent to comment {comment_id}")
    except Exception as e:
        print(f"(Public)❌ Error: {e}")

def reply_private(user_id, message_text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": user_id},
        "message": {"text": message_text}
    }
    try:
        requests.post(url, json=payload)
        print(f"(Private) ✅ DM sent to {user_id}")
    except Exception as e:
        print(f"(Private) ❌ Error: {e}")

# Verification 
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

'''Dms comes under message'''


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json
    if data.get("object") == "instagram":
        for entry in data.get("entry", []):
            
            # 1. Handle DMs
            if "messaging" in entry:
                for event in entry["messaging"]:
                    sender_id = event["sender"]["id"]
                    if "message" in event and "text" in event["message"]:
                        message_text = event["message"]["text"].lower()
                        print(f"📩 DM received from {sender_id}: {message_text}")
                        
                        # Logic for DMs
                        if "price" in message_text:
                            reply_private(sender_id, "The price is $49.99.")
                        elif "hello" in message_text:
                            reply_private(sender_id, "Hi there! How can I help?")

            # 2. Handle Comments (Feed changes)
            elif "changes" in entry:
                for change in entry["changes"]:
                    if change.get("field") == "comments":
                        value = change.get("value", {})
                        comment_id = value.get("id")
                        comment_text = value.get("text", "").lower()
                        
                        # We must ignore our own replies to avoid infinite loops!
                        # (You might need to check sender ID vs your Page ID here)
                        
                        print(f"💬 Comment received: {comment_text}")

                        # Logic for Comments
                        if "price" in comment_text:
                            reply_public(comment_id, "Please check your DMs for the price! 👇")
                        elif "link" in comment_text:
                            reply_public(comment_id, "Here is the link: www.shop.com")

    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)