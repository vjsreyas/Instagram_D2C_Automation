Instagram Comment Automation

It's a Python based automation tool I am building for D2C (Direct-to-Consumer) sellers on Instagram.

Sellers get bombarded with DMs and comments asking for prices or links all day. If they do not reply instantly, they lose the customer. I wrote this script to handle those repetitive queries automatically through the Instagram Graph API, ensuring the seller is always responsive, increasing potential for profits.

How It Works:

The system runs on a simple trigger action model using Flask to listen for Webhooks.
The system captures the event. When a user comments, for example asking for a link, Meta sends a payload to my webhook URL.

The code then analyzes the text. The Python script catches the JSON payload and looks for specific trigger keywords like price, cost, link, or buy.

It then executes the reply. If a keyword matches, the script pulls the correct response from the database and uses the Graph API to post a reply or send a DM instantly.

Work in Progress:

I am currently working on adding AI driven responses. Instead of just keywords, I am integrating an LLM to parse the comments. This will allow the program to understand context and give a more human reply to drive purchase intent, rather than just providing links

Future Plans: (will be updating as i generate more ideas)

I plan to build a Client Dashboard. This will be a frontend so the client can log in and see their engagement stats without asking me.

I also want to add No Code Configuration. This will be a settings page where the user can update their trigger keywords without needing to touch the Python code.

Project Strucutre:

app.py: Main application code
.env: To store the tokens 
