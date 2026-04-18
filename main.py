import os
from news_fetcher import fetch_top_news, summarize_and_extract_keywords
from image_processor import fetch_pixabay_image, create_final_image
from video_generator import create_video_from_image
from social_poster import post_to_meta, post_to_x


import os

def main():
    print("--- 1. Fetching Top News ---")
    news_text = fetch_top_news()
    if not news_text:
        print("Failed to fetch news. Exiting.")
        return
    print(f"News fetched: {news_text[:100]}...")

    print("\n--- 2. Summarizing & Extracting Keywords ---")
    ai_result = summarize_and_extract_keywords(news_text)
    summary = ai_result.get("summary", "")
    keyword = ai_result.get("keyword", "")
    
    if not summary or not keyword:
        print("Failed to generate summary or keywords. Exiting.")
        return
        
    print(f"Summary: {summary}")
    print(f"Keyword: {keyword}")

    print("\n--- 3. Fetching Image & Processing ---")
    pixabay_img = fetch_pixabay_image(keyword)
    
    # We output directly to root as requested
    image_output_path = "final_output.png"
    create_final_image(pixabay_img, summary, image_output_path)

    print("\n--- 4. Generating Video ---")
    video_output_path = "final_output.mp4"
    success = create_video_from_image(image_output_path, video_output_path, duration=15)
    
    if success:
        print(f"\n✅ Video Generation Complete!")
        print(f"Check {image_output_path} and {video_output_path}")
        
        print("\n--- 5. Posting to Social Media ---")
        caption = summary
        
        try:
            post_to_meta(video_output_path, caption)
        except Exception as e:
            print(f"Unexpected error posting to Meta (Facebook/Instagram): {e}")
            
        try:
            post_to_x(video_output_path, caption)
        except Exception as e:
            print(f"Unexpected error posting to X: {e}")
            
        print("\n✅ Pipeline Fully Complete!")
            
    else:
        print("\n❌ Video generation failed. Skipping social posting.")

if __name__ == "__main__":
    main()
