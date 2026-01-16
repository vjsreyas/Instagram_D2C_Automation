import os
from flask import Flask, request
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)

verify_token = os.getenv("VERIFY_TOKEN")
access_token = os.getenv("ACCESS_TOKEN")

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == verify_token:
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json
    print("Webhook received:", data)

    if data.get("object") == "instagram":
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                
                if change.get("field") == "comments":
                    value = change.get("value", {})
                    
                    comment_id = value.get("id")
                    comment_text = value.get("text", "").lower() 
                    sender_id = value.get("from", {}).get("id")
                    
                    print(f"Comment from {sender_id}: {comment_text}")

                    if "price" in comment_text or "cost" in comment_text:
                        reply_to_comment(comment_id, "Hey! The price is $49.99. Check our bio to buy!")
                    
                    elif "link" in comment_text or "buy" in comment_text:
                        reply_to_comment(comment_id, "You can grab it here: www.yourshop.com/product")
                    
                    else:
                        print("No keywords matched, ignoring.")

    return "EVENT_RECEIVED", 200

def reply_to_comment(comment_id, message_text):
    url = f"https://graph.facebook.com/v24.0/{comment_id}/replies"
    payload = {
        "message": message_text,
        "access_token": access_token
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"Reply sent to comment {comment_id}!")
        else:
            print(f"Failed to reply: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    app.run(port=5000, debug=True)