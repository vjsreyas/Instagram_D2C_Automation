import os
from flask import Flask, request
from dotenv import load_dotenv
import requests

load_dotenv()
'''Dms comes under message'''
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
        print(f"(Public) Reply sent to comment {comment_id}")
    except Exception as e:
        print(f"(Public) Error: {e}")

def reply_private(user_id, message_text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": user_id},
        "message": {"text": message_text}
    }
    try:
        requests.post(url, json=payload)
        print(f"(Private) DM sent to {user_id}")
    except Exception as e:
        print(f"(Private) Error: {e}")

# Verification 
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403


def reply_dms(comment_id, message_text):

    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={ACCESS_TOKEN}"
    payload = {
        "recipient": {"comment_id": comment_id},  #Uses comment_id, not id
        "message": {"text": message_text}
    }
    try:
        requests.post(url, json=payload)
        print(f"(Private) DM sent for comment {comment_id}")
    except Exception as e:
        print(f"(Private) Error: {e}")


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json
    if data.get("object") == "instagram":
        for entry in data.get("entry", []):
            
            if "messaging" in entry:
                for event in entry["messaging"]:
                    sender_id = event["sender"]["id"]
                    if "message" in event and "text" in event["message"]:
                        message_text = event["message"]["text"].lower()
                        print(f"DM received from {sender_id}: {message_text}")
                        
                        if "price" in message_text:
                            reply_private(sender_id, "The price is $49.99.")
                        elif "hello" in message_text:
                            reply_private(sender_id, "Hi there! How can I help?")

            elif "changes" in entry:
                for change in entry["changes"]:
                    if change.get("field") == "comments":
                        value = change.get("value", {})
                        comment_id = value.get("id")
                        comment_text = value.get("text", "").lower()
                        
                        print(f"Comment received: {comment_text}")

                        # logic for the replies - change into open ai api key 
                        if "price" in comment_text:
                            reply_public(comment_id, "Please check your DMs for the price! ")
                            reply_dms(comment_id,"Here is the link: xxx.")
                        elif "link" in comment_text:
                            reply_public(comment_id, "Here is the link: www.shop.com")
    return "EVENT_RECEIVED", 200



if __name__ == "__main__":
    app.run(port=5000, debug=True)