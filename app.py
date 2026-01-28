import os
import threading
from flask import Flask, request
from dotenv import load_dotenv
import requests
import json 
import openai

load_dotenv()

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
BUSSINESS_ID = os.getenv("BUSSINESS_ID")
# OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")

# client = openai.OpenAI(api_key=OPEN_AI_API_KEY)

prompt = """
You are a friendly and helpful sales assistant for 'Demo Shop', a trendy fashion store.
Your goal is to answer customer questions politely and encourage them to buy.

Key Information:
- Shipping: Free shipping on orders over amount infinite.
- Link: provide the link to the shop "hello.com"
- Tone: Casual, Emoji-friendly, but professional. 
- Length: Keep responses short (under 2 sentences) because this is Instagram.
"""

def json_output(data):
    with open("output.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

# def get_ai_response(message_text):
#     try:
#         response = openai.ChatCompletion.create(
#             model="gpt-4o-mini",
#             messages=[{"role": "system", "content": prompt},
#                 {"role": "user", "content": message_text}
#                 ]
#             temperature=0.6,
#             max_tokens=500,
#             top_p=1,
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         print(f"Connection Error: {e}")
#         return "We are having a slight issue connecting with our server. Please try again later!"

# def send_request(url, payload, request_type):
#     try:
#         response = requests.post(url, json=payload)
#         if response.status_code == 200:
#             print(f"({request_type}) Sent Successfully!")
#         else:
#             print(f"({request_type}) Failed: {response.json()}")
#     except Exception as e:
#         print(f"({request_type}) Response Error: {e}")

def reply_public(comment_id, message_text):
    url = f"https://graph.facebook.com/v24.0/{comment_id}/replies"
    payload = {
        "message": message_text,
        "access_token": ACCESS_TOKEN
    }
    sender_thread = threading.Thread(target=send_request, args=(url, payload, "Public Reply"))
    sender_thread.start()

def reply_private(user_id, message_text):
    url = f"https://graph.facebook.com/v24.0/me/messages?access_token={ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": user_id},
        "message": {"text": message_text}
    }
    sender_thread = threading.Thread(target=send_request, args=(url, payload, "Private DM"))
    sender_thread.start()

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
    
    # try:
    #     response = requests.post(url, json=payload)
    #     response_data = response.json()
        
    #     if response.status_code == 200:
    #         print(f"\tDM Success! Message ID: {response_data.get('message_id')}")
    #     else:
    #         print(f"\tDM FAILED (Status {response.status_code})")
    #         print(f"\tError Code: {response_data.get('error', {}).get('code')}")
    #         print(f"\tError Message: {response_data.get('error', {}).get('message')}")
            
    # except Exception as e:
    #     print(f" Network Error: {e}")

    sender_thread = threading.Thread(target=send_request, args=(url, payload, "Private Comment DM"))
    sender_thread.start()

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return str(challenge), 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json
    print("Raw Json data:\n", data) 
    json_output(data)

    if data.get("object") == "instagram":
        for entry in data.get("entry", []):
            
            if "messaging" in entry:
                for event in entry["messaging"]:
                    if "sender" not in event: continue
                    
                    sender_id = event["sender"]["id"]
                    
                    if event.get("message", {}).get("is_echo"):
                        continue
                    
        

                    if "message" in event and "text" in event["message"]:
                        message_text = event["message"]["text"].lower()
                        print(f"DM received: {message_text}")
                    
                        reply_private(sender_id, "Hello! How can I help?")
                        if "price" in message_text:
                            reply_private(sender_id, "The price is Infinite.")
                        elif "hello" in message_text:
                            reply_private(sender_id, "Hi there! How can I help?")

                        # ai_response = get_ai_response(message_text)
                        # reply_private(sender_id, ai_response)

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
                        
                        # ai_response = get_ai_response(comment_text)
                        # reply_private_to_comment(comment_id, ai_response)
                        if "price" in comment_text.lower():
                            reply_public(comment_id, "Please check your DMs for the price!")
                            reply_private_to_comment(comment_id, "Lets fking go")
                        
                        elif "link" in comment_text:
                            reply_public(comment_id, "Sent! Check your DMs ")
                            reply_private_to_comment(comment_id, "LETSSSSSS GPPPPPPP")

    return "EVENT_RECEIVED", 200

# if __name__ == "__main__":
#     app.run(port=5000, debug=True)

if __name__ == "__main__":
    app.run(
        host ="0.0.0.0",
        port = int(os.environ.get("PORT",8080))
    )