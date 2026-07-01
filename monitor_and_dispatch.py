import instaloader
import requests
import os
import google.generativeai as genai

# 1. Setup API Keys
# These keys are pulled automatically from your GitHub Secrets
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
chat_id = os.environ.get("TELEGRAM_CHAT_ID")

def monitor_and_dispatch(username):
    # Initialize Instaloader
    L = instaloader.Instaloader()
    
    # We use 'art' as the target username
    profile = instaloader.Profile.from_username(L.context, username)
    
    # Get the latest post
    post = next(profile.get_posts())
    
    # Analyze text with Gemini
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(f"Create an engaging infographic idea and caption based on this post: {post.caption}")
    
    # Send message to Telegram
    message = f"New post detected from @{username}! \n\nAI analysis: {response.text}"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # Send the final text to your Telegram bot
    requests.post(url, data={"chat_id": chat_id, "text": message})

# The username is now set to 'art'
if __name__ == "__main__":
    monitor_and_dispatch('art')
