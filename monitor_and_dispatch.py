import instaloader
import requests
import os
import google.generativeai as genai

# 1. Setup API Keys
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
chat_id = os.environ.get("TELEGRAM_CHAT_ID")

def monitor_and_dispatch(username):
    # Initialize Instaloader
    L = instaloader.Instaloader()
    
    # FIX: Tell Instagram we are a regular Chrome browser, not a robot
    L.context._session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    try:
        # Load the profile
        profile = instaloader.Profile.from_username(L.context, username)
        
        # Get the latest post
        post = next(profile.get_posts())
        
        # Analyze text with Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(f"Create an engaging infographic idea and caption based on this post: {post.caption}")
        
        # Send message to Telegram
        message = f"New post detected from @{username}! \n\nAI analysis: {response.text}"
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": message})
        
    except Exception as e:
        # If Instagram still blocks us, send the exact message to your Telegram so you know
        error_message = f"Automation Error: {str(e)}"
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": error_message})
        raise e

if __name__ == "__main__":
    # Change 'art' to your actual target Instagram account username here
    monitor_and_dispatch('art')
  
