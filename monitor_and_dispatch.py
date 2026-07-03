import os
import requests
import google.generativeai as genai

# Setup API Keys from GitHub Secrets
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
chat_id = os.environ.get("TELEGRAM_CHAT_ID")
apify_token = os.environ.get("APIFY_API_TOKEN")

# LIST YOUR COMPETITORS HERE
COMPETITORS = ["desifitlab", "bodybuildingindia"]


def fetch_competitor_data():
    """Calls Apify's managed cloud infrastructure to scrape competitors safely."""
    url = f"https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items?token={apify_token}"

    payload = {
        "directUrls": [f"https://www.instagram.com/{user}/" for user in COMPETITORS],
        "resultsLimit": 10,  # Fetch last 10 posts per competitor to find averages
        "resultsType": "posts",
    }

    response = requests.post(url, json=payload)
    if response.status_code == 201 or response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Apify API failed with status code {response.status_code}")


def analyze_outliers_and_dispatch():
    try:
        raw_posts = fetch_competitor_data()

        user_data = {}
        for post in raw_posts:
            username = post.get("username")
            if username not in user_data:
                user_data[username] = []

            user_data[username].append({
                "caption": post.get("caption", ""),
                "views": post.get("videoViewCount", post.get("likesCount", 0) * 10),
                "url": post.get("url", "")
            })

        outliers_context = ""

        for username, posts in user_data.items():
            if not posts:
                continue
            total_views = sum(p["views"] for p in posts)
            avg_views = total_views / len(posts)

            for p in posts:
                if p["views"] >= (avg_views * 3) and p["views"] > 0:
                    outliers_context += f"\n--- VIRAL OUTLIER FROM @{username} ---\n"
                    outliers_context += f"Performance: Generated {p['views']} views (Account Avg: {int(avg_views)})\n"
                    outliers_context += f"Original Caption: {p['caption']}\n"

        if not outliers_context:
            outliers_context = "No extreme 3x viral outlier posts found today. Analyzing the highest performing recent post instead:\n" + \
                               f"Caption: {raw_posts[0].get('caption', '') if raw_posts else 'No data'}"

        prompt = f"""
        You are an expert Instagram Growth Strategist. Review this data showcasing competitor posts that mathematically outperformed their baseline averages:

        {outliers_context}

        Perform the following tasks based on these winning concepts:
        1. STRATEGY BREAKDOWN: Identify why this topic/hook performed so well compared to normal posts.
        2. FRESH CONTENT IDEAS: Generate 1 highly viral Reel Idea (including a 3-second visual text hook and audio vibe) and 1 highly engaging 5-slide Carousel script based on this topic.
        3. CAPTION: Draft an optimized, scannable caption using line-breaks ready for your page.
        """

        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": f"🔥 **Viral Outlier Trend Analysis Report** 🔥\n\n{response.text}",
            "parse_mode": "Markdown"
        }
        tg_response = requests.post(url, payload)

        if tg_response.status_code != 200:
            print(f"Telegram send FAILED. Status: {tg_response.status_code}")
            print(f"Telegram response: {tg_response.text}")
            raise Exception(f"Telegram API rejected the message: {tg_response.text}")
        else:
            print("Telegram message sent successfully.")

    except Exception as e:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": f"Automation Error: {str(e)}"})
        raise e


if __name__ == "__main__":
    analyze_outliers_and_dispatch()
