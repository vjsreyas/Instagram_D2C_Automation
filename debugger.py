import os
import threading
from flask import Flask, request
from dotenv import load_dotenv
import requests
import json 
from openai import OpenAI

load_dotenv()

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
BUSSINESS_ID = os.getenv("BUSSINESS_ID")
OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")

client = OpenAI(api_key=OPEN_AI_API_KEY)

# --- COLOR PALETTE ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'   # DMs
    GREEN = '\033[92m'  # Success
    YELLOW = '\033[93m' # Comments
    RED = '\033[91m'   # Errors
    RESET = '\033[0m'   # Reset (important)
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

prompt = """
You are a friendly and helpful sales assistant for 'Demo Shop', a trendy fashion store.
Your goal is to answer customer questions politely and encourage them to buy.

Key Information:
- Shipping: Free shipping on orders over amount infinite.
- Link: provide the link to the shop "hello.com"
- Tone: Casual, Emoji-friendly, but professional. 
- Length: Keep responses short (under 2 sentences) because this is Instagram.

Example:
user: Whats the price of this?
you: Its $50. Check dms for more information. (In dms provide the link)

"""

def json_output(data):
    with open("output.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def get_ai_response(message_text):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message_text}
            ],
            temperature=0.6,
            max_tokens=300,
            top_p=1,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"{Colors.RED}Connection Error: {e}{Colors.RESET}")
        return "We are having a slight issue connecting with our server. Please try again later!"

def send_request(url, payload, request_type):
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"{Colors.GREEN}({request_type}) Sent Successfully!{Colors.RESET}")
        else:
            print(f"{Colors.RED}({request_type}) failed: {response.json()}{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}({request_type}) Response Error: {e}{Colors.RESET}")

def reply_public(comment_id, message_text):
    url = f"https://graph.facebook.com/v24.0/{comment_id}/replies"
    payload = {
        "message": message_text,
        "access_token": ACCESS_TOKEN
    }
    threading.Thread(target=send_request, args=(url, payload, "Public Reply")).start()

def reply_dm(user_id, message_text):
    url = f"https://graph.facebook.com/v24.0/me/messages?access_token={ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": user_id},
        "message": {"text": message_text}
    }
    threading.Thread(target=send_request, args=(url, payload, "Private DM")).start()

def reply_dm_from_comment(comment_id, message_text):
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

    threading.Thread(target=send_request, args=(url, payload, "Private Comment DM")).start()

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return str(challenge), 200
    return "Forbidden :)", 403

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json
    # print("\n Raw Json data:\n", data) 
    # json_output(data)
    if data.get("object") == "instagram":
        
        for entry in data.get("entry",[]):
            print(entry)
        for entry in data.get("entry", []):
            if "messaging" in entry:
                for event in entry["messaging"]:
                    if "sender" not in event: continue
                    sender_id = event["sender"]["id"]
                    if event.get("message", {}).get("is_echo"):
                        continue
                    
                    if "message" in event and "text" in event["message"]:
                        message_text = event["message"]["text"].lower()
                        # UPDATED: Using Colors.CYAN for DMs
                        print(f"{Colors.CYAN}DM received: {message_text}{Colors.RESET}")
                    
                        # reply_dm(sender_id, "Hello! How can I help?")
                        # if "price" in message_text:
                        #     reply_dm(sender_id, "The price is Infinite.")
                        # elif "hello" in message_text:
                        #     reply_dm(sender_id, "Hi there! How can I help?")

                        ai_response = get_ai_response(message_text)
                        # print(f"AI Response: \n{ai_response}\n")
                        reply_dm(sender_id, ai_response)
                        
            elif "changes" in entry:
                for change in entry["changes"]:
                    if change.get("field") == "comments":
                        value = change.get("value", {})
                        
                        sender_id = value.get("from", {}).get("id")
                        if sender_id == BUSSINESS_ID:
                            # print(f"Ignoring selfncomment from {sender_id}")
                            continue

                        comment_id = value.get("id")
                        # UPDATED: Using Colors.YELLOW for Comment info
                        print(f"\n{Colors.YELLOW}Comment Id = {comment_id}{Colors.RESET}")
                        comment_text = value.get("text", "").lower()
                        print(f"{Colors.YELLOW}Comment Text: {comment_text}{Colors.RESET}\n")
                        
                        reply_public(comment_id, "Please check your DMs!")
                        ai_response = get_ai_response(comment_text)
                        # print(f"AI Response: \n{ai_response}\n")
                        reply_dm_from_comment(comment_id, ai_response)


                        # if "price" in comment_text.lower():
                        #     reply_public(comment_id, "Please check your DMs for the price!")
                        #     reply_dm_from_comment(comment_id, "Lets fking go")
                        
                        # elif "link" in comment_text:
                        #     reply_public(comment_id, "Sent! Check your DMs ")
                        #     reply_dm_from_comment(comment_id, "LETSSSSSS GPPPPPPP")

    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)

# if __name__ == "__main__":
#     app.run(
#         host ="0.0.0.0",
#         port = int(os.environ.get("PORT",8080))
#     )