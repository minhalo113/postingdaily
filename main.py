import os
from news_fetcher import fetch_top_news, summarize_and_extract_keywords
from image_processor import fetch_pixabay_image, create_final_image
from video_generator import create_video_from_image
from social_poster import post_to_meta, post_to_x, post_to_youtube


import os

def main():
    news_text = fetch_top_news()
    if not news_text:
        print("No new articles to post.")
        return
    print(f"News fetched: {news_text[:100]}...")

    ai_result = summarize_and_extract_keywords(news_text)
    summary = ai_result.get("summary", "")
    keyword = ai_result.get("keyword", "")
    title = ai_result.get("title", summary[:97] + "..." if summary else "")
    description = ai_result.get("description", summary)
    
    if not summary or not keyword:
        print("cant make keyword")
        return
        
    print(f"Summary: {summary}")
    print(f"Keyword: {keyword}")
    print(f"Title: {title}")

    pixabay_img = fetch_pixabay_image(keyword)
    
    image_output_path = "final_output.png"
    create_final_image(pixabay_img, summary, image_output_path)

    video_output_path = "final_output.mp4"
    success = create_video_from_image(image_output_path, video_output_path, duration=15)
    
    if success:
        caption = description
        
        try:
            post_to_meta(image_output_path, caption)
        except Exception as e:
            print(f"Unexpected error posting to Meta (Facebook/Instagram): {e}")
            
        # try:
        #     # post_to_x(image_output_path, caption)
        # except Exception as e:
        #     print(f"Unexpected error posting to X: {e}")
            
        try:
            post_to_youtube(video_output_path, title, description)
        except Exception as e:
            print(f"Unexpected error posting to YouTube: {e}")
            
    else:
        print("Video generation failed. Skipping social posting.")

if __name__ == "__main__":
    main()
