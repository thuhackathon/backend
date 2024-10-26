import pvporcupine
import pyaudio
import struct
import speech_recognition as sr
import dotenv
import os

# Load environment variables
dotenv.load_dotenv()
ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY")

# Initialize Porcupine for hot word detection
def init_porcupine():
    porcupine = pvporcupine.create(access_key=ACCESS_KEY, keyword_paths=["./hey-remy_en_mac_v3_0_0.ppn"])
    return porcupine

# Initialize Speech Recognizer
recognizer = sr.Recognizer()

# Function to recognize speech after wake word detection
def recognize_speech():
    with sr.Microphone() as source:
        print("Listening for command...")
        try:
            audio = recognizer.listen(source, phrase_time_limit=10, timeout=2)
            text = recognizer.recognize_google(audio, language="zh-CN")
            print(f"Recognized Speech: {text}")
        except sr.UnknownValueError:
            print("Could not understand the audio")
        except sr.RequestError:
            print("Could not request results; check your internet connection")
        except Exception as e:
            print(f"Error during recognition: {e}")

# Callback function to execute on hot word detection
def on_wake_word_detected():
    print("Hey Remy detected! Starting speech recognition...")
    recognize_speech()

# Function to listen for hot word
def listen_for_hotword(porcupine, audio_stream):
    print("Listening for 'Hey Remy' hot word...")
    try:
        while True:
            pcm = audio_stream.read(porcupine.frame_length)
            pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)

            # Check if hot word is detected
            if porcupine.process(pcm_unpacked) >= 0:
                on_wake_word_detected()
                break  # Exit the loop after hot word detection to stop listening

    except KeyboardInterrupt:
        print("Exiting gracefully...")
        audio_stream.stop_stream()
        audio_stream.close()
        porcupine.delete()

def main():
    porcupine = init_porcupine()
    pa = pyaudio.PyAudio()
    
    # Configure audio stream
    audio_stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )
    
    try:
        listen_for_hotword(porcupine, audio_stream)

    except KeyboardInterrupt:
        print("Exiting gracefully...")
    finally:
        audio_stream.stop_stream()
        audio_stream.close()
        pa.terminate()
        porcupine.delete()

if __name__ == "__main__":
    main()