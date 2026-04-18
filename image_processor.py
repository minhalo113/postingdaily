import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

def fetch_pixabay_image(keyword):
    if not keyword:
        raise ValueError("keyword empty")

    if isinstance(keyword, list):
        keyword = ", ".join(keyword)
        
    api_key = os.getenv("PIXABAY_API_KEY")

    url = f"https://pixabay.com/api/?key={api_key}&q={requests.utils.quote(keyword)}&orientation=vertical&image_type=photo&per_page=3"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get("hits") and len(data["hits"]) > 0:
            image_url = data["hits"][0].get("largeImageURL")
            if image_url:
                img_response = requests.get(image_url)
                img_response.raise_for_status()
                return Image.open(BytesIO(img_response.content))
    except Exception as e:
        print(f"Error fetching image from Pixabay: {e}")
    
    return Image.new('RGB', (1080, 1920), color=(50, 50, 50))

def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        line_width = draw.textlength(" ".join(current_line), font=font)
        if line_width > max_width:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
            
    if current_line:
        lines.append(" ".join(current_line))
        
    return lines

def create_final_image(pixabay_img, summary_text, output_path="final_output.png"):
    WIDTH, HEIGHT = 1080, 1920
    
    final_img = Image.new('RGB', (WIDTH, HEIGHT), color=(255, 255, 255))
    
    TOP_HEIGHT = int(HEIGHT * 0.6)
    
    target_ratio = WIDTH / TOP_HEIGHT
    img_ratio = pixabay_img.width / pixabay_img.height
    
    if img_ratio > target_ratio:
        new_width = int(pixabay_img.height * target_ratio)
        offset = (pixabay_img.width - new_width) // 2
        crop_box = (offset, 0, offset + new_width, pixabay_img.height)
    else:
        new_height = int(pixabay_img.width / target_ratio)
        offset = (pixabay_img.height - new_height) // 2
        crop_box = (0, offset, pixabay_img.width, offset + new_height)
        
    cropped_img = pixabay_img.crop(crop_box)
    resized_img = cropped_img.resize((WIDTH, TOP_HEIGHT), Image.Resampling.LANCZOS)
    
    final_img.paste(resized_img, (0, 0))
    
    draw = ImageDraw.Draw(final_img)

    font_large_path = "assets/arialbd.ttf"
    font_small_path = "assets/arial.ttf"
    try:
        font_large = ImageFont.truetype(font_large_path, 60)
        font_small = ImageFont.truetype(font_small_path, 40)
    except IOError as e:
        print("error in font", e)
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    bottom_bg_color = (30, 30, 30)
    draw.rectangle([(0, TOP_HEIGHT), (WIDTH, HEIGHT)], fill=bottom_bg_color)
    
    draw.text((50, TOP_HEIGHT + 50), "BREAKING NEWS", font=font_large, fill=(255, 50, 50))
    
    margin = 50
    max_text_width = WIDTH - (margin * 2)
    lines = wrap_text(summary_text, font_small, max_text_width, draw)
    
    y_text = TOP_HEIGHT + 150
    for line in lines:
        draw.text((margin, y_text), line, font=font_small, fill=(255, 255, 255))
        y_text += 60 

    try:
        if os.path.exists("logo.png"):
            logo = Image.open("logo.png").convert("RGBA")
            
            logo.thumbnail((200, 200))
            
            opacity = 128 
            logo.putalpha(opacity)
            
            margin = 40
            x_pos = WIDTH - logo.width - margin
            y_pos = margin  
            
            final_img.paste(logo, (x_pos, y_pos), logo)
            
    except Exception as e:
        print(f"Error placing logo: {e}")
            
    final_img.save(output_path)
    return output_path

if __name__ == "__main__":
    keyword = "robot coding"
    summary = "AI has achieved a major breakthrough, enabling robots to autonomously write flawless code and boost global productivity."
    
    img = fetch_pixabay_image(keyword)
    create_final_image(img, summary)
