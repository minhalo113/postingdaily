import os
import requests
from dotenv import load_dotenv
import json
import httpx

load_dotenv()

def fetch_top_news():
    api_key = os.getenv("NEWS_API_KEY")
    
    url = f"https://newsapi.org/v2/top-headlines?country=us&language=en&pageSize=5&apiKey={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get("articles") and len(data["articles"]) > 0:
            article = data["articles"][0]
            title = article.get("title", "")
            description = article.get("description", "")
            return f"{title}. {description}"
        else:
            print(data)
        return ""
    except Exception as e:
        print(f"Error fetching news: {e}")
        return ""

def summarize_and_extract_keywords(news_text, model_name="gpt-5-nano"):
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key or api_key == "your_openai_api_key_here":
        # Mock response for testing
        print("[MOCK] Summarizing news and extracting keywords...")
        return {
            "summary": "AI has achieved a major breakthrough, enabling robots to autonomously write flawless code and boost global productivity.",
            "keyword": "robot coding",
            "title": "Robots Are Now Writing Code! 🤖💻",
            "description": "AI has achieved a major breakthrough! Robots are now autonomously writing flawless code, significantly boosting global productivity. Check out the future of software development! #AI #Robotics #Coding #TechNews"
        }

    from openai import OpenAI
    client = OpenAI(api_key=api_key
    , http_client=httpx.Client(
        proxy=None,       
        trust_env=False   
    ))

    prompt = (
        f"Here is a news headline/description:\n'{news_text}'\n\n"
        "1. Summarize it in 1 to 3 short sentences that are easy to read on a social media image.\n"
        "2. Extract 1 to 2 visual keywords that describe this news, which I can use to search for a stock photo on Pixabay.\n"
        "3. Create a catchy YouTube video title (maximum 100 characters) for this news.\n"
        "4. Create a detailed description/caption for social media (Facebook, Instagram, X, YouTube) including relevant hashtags.\n"
        "Format the output strictly as JSON with four keys: 'summary', 'keyword', 'title', and 'description'."
    )

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error generating summary: {e}")
        return {"summary": "", "keyword": ""}

if __name__ == "__main__":

    news = fetch_top_news()
    print("Fetched News:", news)
    result = summarize_and_extract_keywords(news)
    print("AI Result:", result)
