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
        
        posted_file = "posted_news.txt"
        posted_urls = []
        if os.path.exists(posted_file):
            with open(posted_file, "r") as f:
                posted_urls = [line.strip() for line in f if line.strip()]

        if data.get("articles") and len(data["articles"]) > 0:
            for article in data["articles"]:
                article_url = article.get("url")
                if article_url and article_url not in posted_urls:
                    title = article.get("title", "")
                    description = article.get("description", "")
                    
                    posted_urls.append(article_url)
                    if len(posted_urls) > 100:
                        posted_urls = posted_urls[-100:]
                        
                    with open(posted_file, "w") as f:
                        for p_url in posted_urls:
                            f.write(f"{p_url}\n")
                            
                    return f"{title}. {description}"
            
            print("no news to post")
            return ""
        else:
            print(data)
        return ""
    except Exception as e:
        print(f"Error fetching news: {e}")
        return ""

def summarize_and_extract_keywords(news_text, model_name="gpt-5-nano"):
    api_key = os.getenv("OPENAI_API_KEY")
    
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
