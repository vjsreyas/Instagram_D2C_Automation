import os
import threading
from flask import Flask, request
from dotenv import load_dotenv
import requests
import json 
import redis
from openai import OpenAI
import hmac
import hashlib

load_dotenv()

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
BUSSINESS_ID = os.getenv("BUSSINESS_ID")
OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")
REDIS_URL = os.getenv("REDIS_URL")
# REDIS_TOKEN = os.getenv("REDIS_TOKEN")


client = OpenAI(api_key=OPEN_AI_API_KEY)

try:
    if REDIS_URL:
        db = redis.from_url(REDIS_URL, decode_responses=True)
        print("Connected to Redis Database")
    else:
        print("REDIS_URL not found. Using temporary RAM memory.")
        db = None
except Exception as e:
    print(f"Redis Connection Failed: {e}")
    db = None


local_memory = {}
human_assistance = set()

def get_memory(user_id):
    if db:
        data = db.get(f"user:{user_id}")
        if data:
            return json.loads(data) # Convert string back to list
        return []
    else:
        return local_memory.get(user_id, [])

def save_memory(user_id, history):
    if db:
        db.set(f"user:{user_id}", json.dumps(history))
        db.expire(f"user:{user_id}", 86400)
    else:
        local_memory[user_id] = history

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'   # DMs
    GREEN = '\033[92m'  # Success
    YELLOW = '\033[93m' # Comments
    RED = '\033[91m'   # Errors
    RESET = '\033[0m'   # Reset (improtant)
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

prompt_dm = """
You are a friendly and helpful sales assistant for 'Demo Shop', a trendy fashion store.
Your goal is to answer customer questions politely and encourage them to buy.

Key Information:
- Shipping: Free shipping on orders over amount infinite.
- Link: provide the link to the shop "hello.com"
- Tone: Casual, Emoji-friendly, but professional. 
- Length: Keep responses short (under 2 sentences) because this is Instagram.

Example:
user: Whats the price of this?
you: Its $. Check the link hello.com for more (In dms provide the link)

Answer In less than 20 words.

"""

prompt_public = """
You are a friendly social media manager for 'Demo Shop'.
Your goal is to reply to public comments politely and tell them you have sent a DM.
If the user asks for the price or link, tell them to check the DMs, after sending one of the following variations:
- Variation: "Sent!", "Check your inbox! ", "DMed you! ✨", "Check your requests!"
- Do NOT give the price or link here.
- Keep it under 5 words.
If the user asks for any queries answer them politely
"""


def json_output(data):
    with open("output.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def is_valid_signature(request):
    """
    Checks if the incoming request is actually from Meta.
    Returns True if valid, False if fake.
    """

    signature = request.headers.get('X-Hub-Signature-256')

    if not signature:
        return False
    
    app_secret = os.getenv("APP_SECRET")
    
    if not app_secret:
        print(f"{Colors.FAIL}⚠️ APP_SECRET is missing in .env!{Colors.RESET}")
        return True 
    
    #hmac shar 256
    expected_hash = signature.split('=')[1]
    
    my_hash = hmac.new(
        key=app_secret.encode(), 
        msg=request.data,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # 5. Compare the two hashes securely
    return hmac.compare_digest(my_hash, expected_hash)

def get_ai_response(user_id,message_text,sys_prompt):

    # user_history = local_memory.get(user_id,[])
    # user_history.append({"role": "user", "content": message_text})

    # if len(user_history) > 6:
    #     user_history = user_history[-6:]
    history = get_memory(user_id)

    history.append({"role": "user", "content": message_text})
    if len(history) > 6:
        history = history[-6:]

    save_memory(user_id, history)

    try:
        messages_payload = [{"role": "system", "content": sys_prompt}] + history
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_payload,
            temperature=0.56,
            max_tokens=100
        )
        
        ai_reply = response.choices[0].message.content
        

        history.append({"role": "assistant", "content": ai_reply})

        # user_history.append({"role": "assistant", "content": ai_reply})
        # local_memory[user_id] = user_history
        
        return ai_reply
        
    except Exception as e:
        print(f"{Colors.FAIL}Connection Error: {e}{Colors.RESET}")
        return "I'm having a little trouble thinking right now. Try again later!"

def send_request(url, payload, request_type):
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"{Colors.GREEN}({request_type}) Sent Successfully!{Colors.RESET}")
        else:
            print(f"{Colors.RED}({request_type}) failed: {response.json()}{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}({request_type}) Response Error: {e}{Colors.RESET}")


def handle_dm_async(sender_id, message_text): # Sends Ai response to the bg 
    if sender_id in human_assistance:
        print(f"{Colors.YELLOW}User {sender_id} is in Human Mode. Bot ignored.{Colors.RESET}")
        return
    
    triggers = ["human", "support", "agent", "stop bot","person","Customer Support"]
    if any(keyword in message_text for keyword in triggers):
        human_assistance.add(sender_id)
        
        msg = "A Person will be with you shortly!"
        url = f"https://graph.facebook.com/v24.0/me/messages?access_token={ACCESS_TOKEN}"
        payload = {"recipient": {"id": sender_id}, "message": {"text": msg}}
        requests.post(url, json=payload)
        
        print(f"{Colors.RED}🚨 User {sender_id} requested Human Handoff!{Colors.RESET}")
        return
    
    ai_response = get_ai_response(sender_id,message_text,prompt_dm)
    url = f"https://graph.facebook.com/v24.0/me/messages?access_token={ACCESS_TOKEN}"
    payload = {"recipient": {"id": sender_id}, "message": {"text": ai_response}}
    send_request(url, payload, "Private DM")

def handle_comment_async(comment_id, comment_text): # replies privately in the background
    #  Public - Static
    url_public = f"https://graph.facebook.com/v24.0/{comment_id}/replies"
    payload_public = {"message": "Please check your DMs!", "access_token": ACCESS_TOKEN}
    send_request(url_public, payload_public, "Public Reply")
    keywords = ["price", "cost", "link", "buy"]
    if any(keyword in comment_text for keyword in keywords):
        msg = "Here's the link to the product: hello.com"
        url = f"https://graph.facebook.com/v24.0/me/messages?access_token={ACCESS_TOKEN}"
        payload = {"recipient": {"id": comment_id}, "message": {"text": msg}}
        send_request(url, payload, "Private DM")

    ai_response = get_ai_response(comment_id, comment_text,prompt_public)
    

    # Private - AI
    url_private = f"https://graph.facebook.com/v24.0/me/messages?access_token={ACCESS_TOKEN}"
    payload_private = {
        "recipient": {"comment_id": comment_id},
        "message": {"text": ai_response}
    }
    send_request(url_private, payload_private, "Private Comment DM")

# def reply_public(comment_id, message_text):
#     url = f"https://graph.facebook.com/v24.0/{comment_id}/replies"
#     payload = {
#         "message": message_text,
#         "access_token": ACCESS_TOKEN
#     }
#     threading.Thread(target=send_request, args=(url, payload, "Public Reply")).start()

# def reply_dm(user_id, message_text):
#     url = f"https://graph.facebook.com/v24.0/me/messages?access_token={ACCESS_TOKEN}"
#     payload = {
#         "recipient": {"id": user_id},
#         "message": {"text": message_text}
#     }
#     threading.Thread(target=send_request, args=(url, payload, "Private DM")).start()

# def reply_dm_from_comment(comment_id, message_text):
#     url = f"https://graph.facebook.com/v24.0/me/messages?access_token={ACCESS_TOKEN}"
#     payload = {
#         "recipient": {
#             "comment_id": comment_id
#             },
#         "message": {
#             "text": message_text
#             }
#     }
    
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

    # threading.Thread(target=send_request, args=(url, payload, "Private Comment DM")).start()

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

    if not is_valid_signature(request):
        print(f"{Colors.RED}Invalid Signature Detected!{Colors.RESET}")
        return "Forbidden", 403

    data = request.json
    # json_output(data) 
    
    if data.get("object") == "instagram":
        for entry in data.get("entry", []):
            if "messaging" in entry:
                for event in entry["messaging"]:
                    if "sender" not in event: continue
                    sender_id = event["sender"]["id"]

        
                    if event.get("message", {}).get("is_echo"): continue

                    if "message" not in event or "text" not in event["message"]:
                        print(f"{Colors.YELLOW} Received non-text message. Ignoring.{Colors.RESET}")
                        continue
           
                    message_text = event["message"]["text"].lower()
                    print(f"{Colors.CYAN}DM received: {message_text}{Colors.RESET}")

                    threading.Thread(target=handle_dm_async, args=(sender_id, message_text)).start()

            elif "changes" in entry:
                for change in entry["changes"]:
                    field = change.get("field")
                    value = change.get("value", {})

                    if field == "comments":
                        sender_id = value.get("from", {}).get("id")
                        
                        if sender_id == BUSSINESS_ID: continue

                        comment_id = value.get("id")
                        comment_text = value.get("text", "").lower()
                        
                        print(f"\n{Colors.YELLOW}Comment Id = {comment_id}{Colors.RESET}")
                        print(f"{Colors.YELLOW}Comment Text: {comment_text}{Colors.RESET}\n")
                        
                        threading.Thread(target=handle_comment_async, args=(comment_id, comment_text)).start()

                    # Create a story feature soon...
                    elif field == "mentions":
                    
                        sender_id = value.get("sender_id")
                        print(f"{Colors.CYAN}Story Mention from {sender_id}!{Colors.RESET}")
                        # threading.Thread(target=handle_story_async, args=(sender_id,)).start()

    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)

# if __name__ == "__main__":
#     app.run(
#         host ="0.0.0.0",
#         port = int(os.environ.get("PORT",8080))
#     )