import os
import random
from moviepy import ImageClip, AudioFileClip, CompositeAudioClip

def create_video_from_image(image_path, output_path = "final_output.mp4", duration = 15):
    if not os.path.exists(image_path):
        print(f"Error: Image {image_path} not found")
        return False
    
    print(f"Creating {duration}-second video from {image_path}...")

    image_clip = ImageClip(image_path).with_duration(duration)

    music_dir = "music"
    audio_clip = None

    if os.path.exists(music_dir) and os.path.isdir(music_dir):
        music_files = [f for f in os.listdir(music_dir) if f.endswith(('.mp3', '.wav', '.ogg'))]
        if music_files:
            selected_music = random.choice(music_files)
            music_path = os.path.join(music_dir, selected_music)
            print(f"Selected background music: {music_path}")

            try:
                raw_audio = AudioFileClip(music_path)
                if raw_audio.duration > duration:
                    audio_clip = raw_audio.subclipped(0, duration)
                else:
                    audio_clip = raw_audio
            except Exception as e:
                print(f"Error processing audio file {music_path}: {e}")
        else:
            print(f"No audio files found in {music_dir}/")
    else:
        print(f"Music directory {music_dir}/ not found.")

    if audio_clip:
        from moviepy.audio.fx.AudioFadeOut import AudioFadeOut

        audio_clip = audio_clip.with_effects([AudioFadeOut(2)])
        image_clip = image_clip.with_audio(audio_clip)

    try:
        image_clip.write_videofile(
            output_path,
            fps = 30,
            codec = "libx264",
            audio_codec = "aac",
            preset = "ultrafast"
        )
        print(f"Successfully generated video: {output_path}")
        return True
    except Exception as e:
        print(f"Error generating video: {e}")
        return False

if __name__ == "__main__":
    create_video_from_image("final_output.png")