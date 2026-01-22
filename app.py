import os
from flask import Flask, request
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
BUSSINESS_ID = os.getenv("BUSSINESS_ID")  


def reply_public(comment_id, message_text):
    url = f"https://graph.facebook.com/v24.0/{comment_id}/replies"
    payload = {
        "message": message_text,
        "access_token": ACCESS_TOKEN
    }
    try:
        requests.post(url, json=payload)
        print(f"(Public) Reply sent to {comment_id}")
    except Exception as e:
        print(f"(Public) Error: {e}")

def reply_private(user_id, message_text):
    url = f"https://graph.facebook.com/v24.0/me/messages?access_token={ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": user_id},
        "message": {"text": message_text}
    }
    try:
        requests.post(url, json=payload)
        print(f"(Private) DM sent to user {user_id}")
    except Exception as e:
        print(f"(Private) Error: {e}")

def reply_private_to_comment(comment_id, message_text):
    url = f"https://graph.facebook.com/v24.0/me/messages?access_token={ACCESS_TOKEN}"
    payload = {
        "recipient": {
            "comment_id": comment_id
            },
        "message": {
            "text": message_text
            }
    }
    
    try:
        response = requests.post(url, json=payload)
        response_data = response.json()
        
        if response.status_code == 200:
            print(f"\tDM Success! Message ID: {response_data.get('message_id')}")
        else:
            print(f"\tDM FAILED (Status {response.status_code})")
            print(f"\tError Code: {response_data.get('error', {}).get('code')}")
            print(f"\tError Message: {response_data.get('error', {}).get('message')}")
            
    except Exception as e:
        print(f" Network Error: {e}")

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json
    print("Raw Json data:\n", data) 
    if data.get("object") == "instagram":
        for entry in data.get("entry", []):
            
            if "messaging" in entry:
                for event in entry["messaging"]:
                    if "sender" not in event: continue
                    
                    sender_id = event["sender"]["id"]
                    
                    if sender_id == BUSSINESS_ID:
                        continue

                    if "message" in event and "text" in event["message"]:
                        message_text = event["message"]["text"].lower()
                        print(f"DM received: {message_text}")
                        
                        if "price" in message_text:
                            reply_private(sender_id, "The price is $49.99.")
                        elif "hello" in message_text:
                            reply_private(sender_id, "Hi there! How can I help?")

            elif "changes" in entry:
                for change in entry["changes"]:
                    if change.get("field") == "comments":
                        value = change.get("value", {})
                        
                        sender_id = value.get("from", {}).get("id")
                        if sender_id == BUSSINESS_ID:
                            # print(f"Ignoring selfncomment from {sender_id}")
                            continue

                        comment_id = value.get("id")
                        print(f"\nComment Id = {comment_id}\n")
                        comment_text = value.get("text", "").lower()
                        

                        if "price" in comment_text.lower():
                            reply_public(comment_id, "Please check your DMs for the price!")
                            reply_private_to_comment(comment_id, "Lets fking go")
                        
                        elif "link" in comment_text:
                            reply_public(comment_id, "Sent! Check your DMs ")
                            reply_private_to_comment(comment_id, "LETSSSSSS GPPPPPPP")

    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)