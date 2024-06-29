import json
import os
import uuid

from openai import OpenAI
from pytube import YouTube
from pytube.exceptions import RegexMatchError


def return_i_tag(audio_streams):
    """
    For the purposes of this project the audio/webm format is desired from the audio_streams.
    returns: i_tag of the desired stream.
    """
    i_tag = 0
    for stream in audio_streams:
        if stream.mime_type == 'audio/webm':
            i_tag = stream.itag
            return i_tag


def lambda_handler(event, context):
    """

    :param event:
        - should contain only "url" key with the url of the YouTube video to transcribe.
    :param context:
        - requirement of AWS lambda function. Not used here.
    :return:
        - returns JSON object with transcript of YouTube video.
    """

    url = event.get('url')

    # Set up client for OPEN AI.
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

    # Setup PyTube to be able to download YouTube video's audio.
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
    # get audio streams from yt object
    audio_streams = yt.streams.filter(only_audio=True)
    # get itag of desired audio stream and get audio stream
    i_tag = return_i_tag(audio_streams)
    audio_stream = yt.streams.get_by_itag(i_tag)

    # Limit file size to meet GPT-whisper constraints.
    filesize = audio_stream.filesize
    print(f'Downloaded {filesize} bytes of audio')
    if filesize > 21000000:
        return {
            "statusCode": 500,
            "body": {
                "message": f"YuoTube Audio stream file size too large: {filesize} bytes :(",
            }
        }

    # Download audio file.
    audio_stream.download(output_path=output_path, filename=filename)

    # Use GPT-Whisper to transcribe.
    audio_file = open(output_path + '/' + filename, 'rb')
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
    )
    # Return transcription.
    return {
        "statusCode": 200,
        "body": {
            "url": url,
            "transcript": transcript.text
        }
    }


# Uncomment the following to test locally.
if __name__ == "__main__":
    event = {
        "url": "https://www.youtube.com/watch?v=ySLViEgeFkM"
    }  # Define any event data if needed
    context = {}  # Define any context data if needed
    result = lambda_handler(event, context)
    print(json.dumps(result, indent=2))
