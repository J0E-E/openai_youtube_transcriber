import json
import os
import uuid

from openai import OpenAI
from pytube import YouTube
from pytube.exceptions import RegexMatchError


def return_i_tag(audio_streams):
    i_tag = 0
    for stream in audio_streams:
        if stream.mime_type == 'audio/webm':
            i_tag = stream.itag
            return i_tag


def lambda_handler(event, context):
    url = event.get('url')
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {
            'statusCode': 400,
            'body': {
                'message': 'Missing OPENAI_API_KEY environment variable'
            }
        }
    try:
        client = OpenAI(api_key=api_key)
    except Exception as e:
        return {
            "statusCode": 500,
            "body": {
                "message": "Something went wrong with OpenAI. Please try again. :(",
                "error": str(e)
            }
        }

    filename = f"{uuid.uuid4()}_transcript_video.webm"
    output_path = '/tmp'
    try:
        yt = YouTube(url)
    except RegexMatchError as e:
        print(f"regex error: {e}")
        print(f"url: {url}")
        print(f"unable to use this url, moving on...")
        return {
            "statusCode": 500,
            "body": {
                "message": f"Unable to use url: {url} :(",
                "error": str(e)
            }
        }

    audio_streams = yt.streams.filter(only_audio=True)
    i_tag = return_i_tag(audio_streams)
    audio_stream = yt.streams.get_by_itag(i_tag)
    filesize = audio_stream.filesize

    print(f'Downloaded {filesize} bytes of audio')
    if filesize > 21000000:
        return {
            "statusCode": 500,
            "body": {
                "message": f"YuoTube Audio stream file size too large: {filesize} bytes :(",
            }
        }

    audio_stream.download(output_path=output_path, filename=filename)

    audio_file = open(output_path + '/' + filename, 'rb')

    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
    )

    return {
        "statusCode": 200,
        "body": {
            "url": url,
            "transcript": transcript.text
        }
    }


# # Uncomment the following to test locally.
# if __name__ == "__main__":
#     event = {
#         "url": "https://www.youtube.com/watch?v=ySLViEgeFkM"
#     }  # Define any event data if needed
#     context = {}  # Define any context data if needed
#     result = lambda_handler(event, context)
#     print(json.dumps(result, indent=2))
