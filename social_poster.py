import os
import requests
import json
import tweepy
from dotenv import load_dotenv
import time
import cloudinary
import cloudinary.uploader
import cloudinary.api
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

load_dotenv()

GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v21.0")

def ensure_env(value, name):
    if not value:
        raise ValueError(f"{name} is not configured")
    return value

def upload_to_cloudinary(image_path):
    try:
        cloudinary.config(
            cloud_name=ensure_env(os.getenv("CLOUDINARY_CLOUD_NAME"), "CLOUDINARY_CLOUD_NAME"),
            api_key=ensure_env(os.getenv("CLOUDINARY_API_KEY"), "CLOUDINARY_API_KEY"),
            api_secret=ensure_env(os.getenv("CLOUDINARY_API_SECRET"), "CLOUDINARY_API_SECRET")
        )
        
        response = cloudinary.uploader.upload(image_path)
        image_url = response.get("secure_url")
        public_id = response.get("public_id")
        
        return image_url, public_id
    except Exception as e:
        print(f"error for cloudinary upload: {e}")
        return None, None

def wait_for_ig_container_ready(creation_id, access_token, max_wait_ms=900000, poll_interval_ms=5000):
    endpoint = f"https://graph.facebook.com/{GRAPH_VERSION}/{creation_id}"
    start_time = time.time() * 1000
    
    while True:
        try:
            response = requests.get(endpoint, params={'access_token': access_token, 'fields': 'status_code'})
            response.raise_for_status()
            data = response.json()
            status = data.get('status_code')
            
            if status == 'FINISHED':
                return {'ok': True, 'status': status, 'diag': data}
                
            if status == 'ERROR':
                msg = 'Unknown IG container error'
                try:
                    error_response = requests.get(endpoint, params={'access_token': access_token, 'fields': 'error_message'})
                    e2 = error_response.json()
                    if e2 and e2.get('error_message'):
                        msg = e2.get('error_message')
                except Exception:
                    pass
                return {'ok': False, 'status': status, 'diag': {'status_code': 'ERROR'}, 'error': Exception(f"IG container ERROR: {msg}")}
                
            if (time.time() * 1000) - start_time > max_wait_ms:
                return {'ok': False, 'status': status, 'error': Exception('Timed out waiting for IG container to finish processing')}
                
            time.sleep(poll_interval_ms / 1000.0)
            
        except requests.exceptions.RequestException as err:
            body = err.response.json() if err.response and err.response.content else {}
            msg = body.get('error', {}).get('message') or json.dumps(body) or str(err)
            status_code = err.response.status_code if err.response else '??'
            raise Exception(f"Polling failed (HTTP {status_code}): {msg}")

def post_to_meta(image_path, caption):
    try:
        access_token = ensure_env(os.getenv("META_ACCESS_TOKEN"), "META_ACCESS_TOKEN")
        facebook_page_id = ensure_env(os.getenv("META_FACEBOOK_PAGE_ID"), "META_FACEBOOK_PAGE_ID")
        instagram_business_id = ensure_env(os.getenv("META_INSTAGRAM_BUSINESS_ID"), "META_INSTAGRAM_BUSINESS_ID")
    except ValueError as e:
        print(f"Meta credentials missing: {e}. Skipping Meta.")
        return False
        
    public_id_to_delete = None
    try:
        image_url, public_id = upload_to_cloudinary(image_path)
        if not image_url:
            raise Exception("Failed to get public URL from Cloudinary upload")
            
        public_id_to_delete = public_id
        
        try:
            facebook_endpoint = f"https://graph.facebook.com/{GRAPH_VERSION}/{facebook_page_id}/photos"
            facebook_params = {
                'access_token': access_token,
                'url': image_url,
                'message': caption
            }
            fb_response = requests.post(facebook_endpoint, data=facebook_params)
            fb_response.raise_for_status()
            print("posted to facebook")
        except Exception as e:
            print(f"error for facebook: {e}")
            if 'fb_response' in locals():
                print(fb_response.text)
            
        # try:
        #     instagram_endpoint = f"https://graph.facebook.com/{GRAPH_VERSION}/{instagram_business_id}/media"
        #     instagram_params = {
        #         'access_token': access_token,
        #         'image_url': image_url,
        #         'caption': caption
        #     }
        #     ig_response = requests.post(instagram_endpoint, data=instagram_params)
        #     ig_response.raise_for_status()
        #     media_data = ig_response.json()
        #     creation_id = media_data.get('id')
            
        #     if not creation_id:
        #         raise Exception("Failed to create Instagram media container")
                
        #     ready = wait_for_ig_container_ready(creation_id, access_token)
        #     if not ready.get('ok'):
        #         diag = json.dumps(ready.get('diag', {}))
        #         error_msg = ready.get('error')
        #         raise Exception(f"Instagram container not publishable: {ready.get('status')}. {error_msg} diag={diag}")
                
        #     publish_endpoint = f"https://graph.facebook.com/{GRAPH_VERSION}/{instagram_business_id}/media_publish"
        #     publish_params = {
        #         'access_token': access_token,
        #         'creation_id': creation_id
        #     }
        #     pub_response = requests.post(publish_endpoint, data=publish_params)
        #     pub_response.raise_for_status()
        #     print("posted to Instagram!")
        # except Exception as e:
        #     print(f"error for instagram: {e}")
        #     if 'pub_response' in locals():
        #         print(pub_response.text)
            
        return True
            
    except Exception as e:
        print(f"error for meta: {e}")
        return False
    finally:
        if public_id_to_delete:
            try:
                cloudinary.uploader.destroy(public_id_to_delete)
                print("deleted from cloudinary")
            except Exception as e:
                print(f"error for cloudinary delete: {e}")

def post_to_x(image_path, caption):
    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_secret = os.getenv("X_ACCESS_SECRET")
    
    if not all([api_key, api_secret, access_token, access_secret]):
        print("error for x: missing credentials")
        return False
        
    try:
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
        api = tweepy.API(auth)
        
        media = api.media_upload(image_path)

        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret
        )
        
        client.create_tweet(text=caption, media_ids=[media.media_id])
        print("posted to x")
        return True
    except Exception as e:
        print(f"error for x: {e}")
        return False


def post_to_youtube(video_path, title, description):
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("error for youtube: missing credentials")
        return False

    try:
        credentials = Credentials(
            None,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token"
        )
        
        youtube = build("youtube", "v3", credentials=credentials)
        
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "25" # News & Politics
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )
        
        response = request.execute()
        print(f"posted to youtube")
        return True
        
    except Exception as e:
        print(f"error for youtube: {e}")
        return False