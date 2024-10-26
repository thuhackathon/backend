from aip import AipSpeech
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
APP_ID = os.getenv("BAIDU_APP_ID")
API_KEY = os.getenv("BAIDU_API_KEY")
SECRET_KEY = os.getenv("BAIDU_SECRET_KEY")

# Initialize the Baidu TTS client
client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)

def synthesize(text, output_file='audio.mp3'):
    """Convert text to speech and save it to an audio file."""
    result = client.synthesis(text, 'zh', 1, {'vol': 5, 'per': 5003})

    # Check if the result is binary audio data or an error dictionary
    if not isinstance(result, dict):
        with open(output_file, 'wb') as f:
            f.write(result)
        print(f"Audio saved to {output_file}")
    else:
        print(f"Error in synthesis: {result}")

# Example usage
if __name__ == "__main__":
    synthesize('简易煎蛋')