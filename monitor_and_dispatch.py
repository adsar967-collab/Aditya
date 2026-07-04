import os
import json
import re
import requests
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont

# Setup API Keys from GitHub Secrets
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
chat_id = os.environ.get("TELEGRAM_CHAT_ID")
apify_token = os.environ.get("APIFY_API_TOKEN")

# LIST YOUR COMPETITORS HERE
COMPETITORS = ["desifitlab", "bodybuildingindia"]

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def fetch_competitor_data():
    """Calls Apify's managed cloud infrastructure to scrape competitors safely."""
    url = f"https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items?token={apify_token}"

    payload = {
        "directUrls": [f"https://www.instagram.com/{user}/" for user in COMPETITORS],
        "resultsLimit": 10,
        "resultsType": "posts",
    }

    response = requests.post(url, json=payload)
    if response.status_code in (200, 201):
        return response.json()
    else:
        raise Exception(f"Apify API failed with status code {response.status_code}")


def find_outliers(raw_posts):
    """Groups posts by account and finds ones that performed 3x better than that account's average."""
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
        avg_views = sum(p["views"] for p in posts) / len(posts)
        for p in posts:
            if p["views"] >= (avg_views * 3) and p["views"] > 0:
                outliers_context += f"\n--- VIRAL OUTLIER FROM @{username} ---\n"
                outliers_context += f"Performance: Generated {p['views']} views (Account Avg: {int(avg_views)})\n"
                outliers_context += f"Original Caption: {p['caption']}\n"

    if not outliers_context:
        outliers_context = "No extreme 3x viral outlier posts found today. Analyzing the highest performing recent post instead:\n" + \
                           f"Caption: {raw_posts[0].get('caption', '') if raw_posts else 'No data'}"

    return outliers_context


def get_content_plan(outliers_context):
    """Asks Gemini to pick ONE best content idea and return it as structured JSON
    ready for rendering into an infographic, instead of free-flowing text."""

    prompt = f"""
    You are an expert Instagram Growth Strategist for an Indian fitness audience.

    Review this data showcasing competitor posts that mathematically outperformed their baseline averages:

    {outliers_context}

    Based on the strongest underlying theme in this data, choose exactly ONE single best content
    idea for a new Instagram INFOGRAPHIC post (not a Reel). Then return ONLY a raw JSON object,
    with no markdown code fences, no explanation text before or after it, in exactly this shape:

    {{
      "headline": "Short punchy headline, max 8 words",
      "subheadline": "One supporting sentence, max 15 words",
      "points": ["Stat or tip 1, short", "Stat or tip 2, short", "Stat or tip 3, short"],
      "cta": "Short call-to-action for the bottom banner, max 10 words",
      "instagram_caption": "A full scannable Instagram caption with line breaks, written in Hinglish for an Indian fitness audience, no hashtags included here",
      "hashtags": "20-25 relevant Instagram hashtags separated by spaces, starting with #",
      "audio_style_suggestion": "A short description of the STYLE/MOOD of trending audio that would fit this post (e.g. upbeat gym transition, suspenseful voiceover beat). Do NOT invent a specific real song or artist name, since real trending tracks change daily and must be checked manually on Instagram's Trending Audio page before posting."
    }}
    """

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    raw_text = response.text.strip()

    # Gemini sometimes wraps JSON in ```json ... ``` fences even when asked not to. Strip them if present.
    raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())

    return json.loads(raw_text)


def wrap_text(draw, text, font, max_width):
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        lines.append(current)
    return lines


def create_infographic(plan, output_path="infographic.png"):
    """Draws the Gemini-generated content plan into an actual Instagram-ready infographic image."""
    W, H = 1080, 1350
    bg_color = (18, 18, 28)
    accent_color = (255, 87, 87)
    text_color = (255, 255, 255)
    muted_color = (190, 190, 200)

    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    font_headline = ImageFont.truetype(FONT_BOLD, 64)
    font_sub = ImageFont.truetype(FONT_REGULAR, 34)
    font_point = ImageFont.truetype(FONT_BOLD, 36)
    font_cta = ImageFont.truetype(FONT_BOLD, 32)

    draw.rectangle([0, 0, W, 14], fill=accent_color)

    y = 90
    for line in wrap_text(draw, plan["headline"], font_headline, W - 120):
        draw.text((60, y), line, font=font_headline, fill=text_color)
        y += 74

    y += 20
    for line in wrap_text(draw, plan["subheadline"], font_sub, W - 120):
        draw.text((60, y), line, font=font_sub, fill=muted_color)
        y += 44

    y += 50
    box_x0, box_x1 = 60, W - 60

    for point in plan["points"]:
        text_lines = wrap_text(draw, point, font_point, box_x1 - box_x0 - 80)
        box_h = max(150, 60 + len(text_lines) * 44)
        draw.rounded_rectangle([box_x0, y, box_x1, y + box_h], radius=20, fill=(30, 30, 44))
        draw.rectangle([box_x0, y, box_x0 + 10, y + box_h], fill=accent_color)
        ty = y + (box_h - len(text_lines) * 44) // 2
        for line in text_lines:
            draw.text((box_x0 + 40, ty), line, font=font_point, fill=text_color)
            ty += 44
        y += box_h + 25

    draw.rectangle([0, H - 100, W, H], fill=accent_color)
    cta_lines = wrap_text(draw, plan["cta"], font_cta, W - 120)
    ty = H - 100 + (100 - len(cta_lines) * 38) // 2
    for line in cta_lines:
        bbox = draw.textbbox((0, 0), line, font=font_cta)
        line_w = bbox[2] - bbox[0]
        draw.text(((W - line_w) // 2, ty), line, font=font_cta, fill=(18, 18, 28))
        ty += 38

    img.save(output_path)
    return output_path


def send_telegram_photo(image_path, short_caption):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    with open(image_path, "rb") as photo_file:
        files = {"photo": photo_file}
        data = {"chat_id": chat_id, "caption": short_caption[:1024]}
        tg_response = requests.post(url, data=data, files=files)

    if tg_response.status_code != 200:
        raise Exception(f"Telegram photo send failed: {tg_response.text}")
    print("Infographic image sent successfully.")


def send_telegram_text_chunks(full_text):
    MAX_CHUNK_SIZE = 3800
    chunks = [full_text[i:i + MAX_CHUNK_SIZE] for i in range(0, len(full_text), MAX_CHUNK_SIZE)]
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    for idx, chunk in enumerate(chunks, start=1):
        part_label = f"[Part {idx}/{len(chunks)}]\n\n" if len(chunks) > 1 else ""
        payload = {"chat_id": chat_id, "text": part_label + chunk}
        tg_response = requests.post(url, payload)
        if tg_response.status_code != 200:
            raise Exception(f"Telegram text send failed on part {idx}: {tg_response.text}")
        print(f"Telegram text part {idx}/{len(chunks)} sent successfully.")


def analyze_outliers_and_dispatch():
    try:
        raw_posts = fetch_competitor_data()
        outliers_context = find_outliers(raw_posts)
        plan = get_content_plan(outliers_context)

        image_path = create_infographic(plan)

        send_telegram_photo(image_path, short_caption=f"🔥 {plan['headline']}")

        followup_text = (
            "📋 CAPTION:\n\n"
            f"{plan['instagram_caption']}\n\n"
            "🏷️ HASHTAGS:\n\n"
            f"{plan['hashtags']}\n\n"
            "🎵 AUDIO STYLE TO LOOK FOR (check Instagram's Trending Audio page for the exact real track):\n\n"
            f"{plan['audio_style_suggestion']}"
        )
        send_telegram_text_chunks(followup_text)

    except Exception as e:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": f"Automation Error: {str(e)}"})
        raise e


if __name__ == "__main__":
    analyze_outliers_and_dispatch()
