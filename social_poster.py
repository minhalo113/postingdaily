import os
import requests
import json
import tweepy
from dotenv import load_dotenv
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

load_dotenv()

GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v21.0")

def ensure_env(value, name):
    if not value:
        raise ValueError(f"{name} is not configured")
    return value

def create_public_server(video_path):
    print("Uploading media to Imgur...")
    imgur_client_id = ensure_env(os.getenv("IMGUR_CLIENT_ID"), "IMGUR_CLIENT_ID")
    url = "https://api.imgur.com/3/image"
    headers = {"Authorization": f"Client-ID {imgur_client_id}"}
    
    try:
        with open(video_path, "rb") as video_file:
            files = {"image": video_file}
            response = requests.post(url, headers=headers, files=files)
            
        if response.status_code == 200:
            video_url = response.json()["data"]["link"]
            print(f"Media uploaded successfully to Imgur. URL: {video_url}")
            return video_url
        else:
            print(f"Error uploading media to Imgur: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred during Imgur upload: {e}")
        return None

def wait_for_ig_container_ready(creation_id, access_token, max_wait_ms=900000, poll_interval_ms=5000):
    endpoint = f"https://graph.facebook.com/{GRAPH_VERSION}/{creation_id}"
    start_time = time.time() * 1000
    
    while True:
        try:
            response = requests.get(endpoint, params={'access_token': access_token, 'fields': 'status_code'})
            response.raise_for_status()
            data = response.json()
            status = data.get('status_code')
            print(f"Instagram container status: {status}")
            
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

def post_to_meta(video_path, caption):
    print("--- Posting to Meta (Facebook & Instagram) ---")
    try:
        access_token = ensure_env(os.getenv("META_ACCESS_TOKEN"), "META_ACCESS_TOKEN")
        facebook_page_id = ensure_env(os.getenv("META_FACEBOOK_PAGE_ID"), "META_FACEBOOK_PAGE_ID")
        instagram_business_id = ensure_env(os.getenv("META_INSTAGRAM_BUSINESS_ID"), "META_INSTAGRAM_BUSINESS_ID")
    except ValueError as e:
        print(f"Meta credentials missing: {e}. Skipping Meta.")
        return False
        
    try:
        video_url = create_public_server(video_path)
        if not video_url:
            raise Exception("Failed to get public URL from Imgur upload")
        
        print("Publishing to Facebook...")
        try:
            facebook_endpoint = f"https://graph.facebook.com/{GRAPH_VERSION}/{facebook_page_id}/videos"
            facebook_params = {
                'access_token': access_token,
                'file_url': video_url,
                'description': caption
            }
            fb_response = requests.post(facebook_endpoint, data=facebook_params)
            fb_response.raise_for_status()
            print("Successfully published to Facebook!")
        except Exception as e:
            print(f"Failed to publish to Facebook: {e}")
            print(fb_response)
            
        print("Publishing to Instagram...")
        try:
            instagram_endpoint = f"https://graph.facebook.com/{GRAPH_VERSION}/{instagram_business_id}/media"
            instagram_params = {
                'access_token': access_token,
                'media_type': 'REELS',
                'video_url': video_url,
                'caption': caption
            }
            ig_response = requests.post(instagram_endpoint, data=instagram_params)
            ig_response.raise_for_status()
            media_data = ig_response.json()
            creation_id = media_data.get('id')
            
            if not creation_id:
                raise Exception("Failed to create Instagram media container")
                
            ready = wait_for_ig_container_ready(creation_id, access_token)
            if not ready.get('ok'):
                diag = json.dumps(ready.get('diag', {}))
                error_msg = ready.get('error')
                raise Exception(f"Instagram container not publishable: {ready.get('status')}. {error_msg} diag={diag}")
                
            publish_endpoint = f"https://graph.facebook.com/{GRAPH_VERSION}/{instagram_business_id}/media_publish"
            publish_params = {
                'access_token': access_token,
                'creation_id': creation_id
            }
            pub_response = requests.post(publish_endpoint, data=publish_params)
            pub_response.raise_for_status()
            print("Successfully published to Instagram!")
        except Exception as e:
            print(f"Failed to publish to Instagram: {e}")
            print(pub_response)
            
        return True
            
    except Exception as e:
        print(f"Error in Meta posting pipeline: {e}")
        return False

def post_to_x(video_path, caption):
    print("--- Posting to X (Twitter) ---")
    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_secret = os.getenv("X_ACCESS_SECRET")
    
    if not all([api_key, api_secret, access_token, access_secret]):
        print("X (Twitter) credentials missing. Skipping X.")
        return False
        
    try:
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
        api = tweepy.API(auth)
        
        print("Uploading media to X...")
        media = api.media_upload(video_path, media_category="tweet_video", chunked=True)
        
        processing_info = media.processing_info
        while processing_info and (processing_info['state'] == 'pending' or processing_info['state'] == 'in_progress'):
            check_after_secs = processing_info.get('check_after_secs', 5)
            print(f"X media processing... waiting {check_after_secs}s")
            time.sleep(check_after_secs)
            media_status = api.get_media_upload_status(media.media_id)
            processing_info = media_status.processing_info
            
            if processing_info['state'] == 'failed':
                print(f"X media processing failed: {processing_info}")
                return False
            if processing_info['state'] == 'succeeded':
                break

        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret
        )
        
        print("Creating tweet...")
        client.create_tweet(text=caption, media_ids=[media.media_id])
        print("Successfully posted to X!")
        return True
    except Exception as e:
        print(f"Failed to post to X: {e}")
        return False


def post_to_youtube(video_path, title, description):
    print("--- Posting to YouTube ---")
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("YouTube credentials missing. Skipping YouTube.")
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
        
        print(f"Uploading {video_path} to YouTube as '{title}'...")
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )
        
        response = request.execute()
        print(f"Successfully posted to YouTube! Video ID: {response.get('id')}")
        return True
        
    except Exception as e:
        print(f"Failed to post to YouTube: {e}")
        return False