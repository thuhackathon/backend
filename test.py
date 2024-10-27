import yaml
import pvporcupine
import pyaudio
import struct
import speech_recognition as sr
import dotenv
import os
import time
import threading
import signal
import sys
import asyncio
from capture_and_save_photo import capture_and_save_photo
import logging
import tkinter as tk
from PIL import Image, ImageTk

from main import active_chat, chat_internal, load_chat_history, save_chat_history

# Add logging configuration near the top of the file after imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('remy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
dotenv.load_dotenv()
ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY")

# Initialize Tkinter
root = tk.Tk()
root.title("Latest Captured Image")
root.geometry("400x300")

# Label for displaying the image
image_label = tk.Label(root)
image_label.pack()

# Initialize Porcupine for hot word detection
def init_porcupine():
    porcupine = pvporcupine.create(access_key=ACCESS_KEY, keyword_paths=["./hey-remy_en_mac_v3_0_0.ppn"])
    return porcupine

# Initialize Speech Recognizer
recognizer = sr.Recognizer()

# Flag to control the repeating task
resume_repeating_task = threading.Event()
resume_repeating_task.set()  # Initially, we want the task to run

# Function for the repeating task
async def repeating_task():
    while resume_repeating_task.is_set():
        logger.info("Active chat is running...")
        res = await active_chat(image_url=capture_and_save_photo()["file_path"])
        logger.info(f"Active chat response: {res}")
        await asyncio.sleep(2)  # Replace time.sleep with asyncio.sleep

# Function to update the Tkinter label with the latest image
def update_image():
    image_path = capture_and_save_photo()["file_path"]
    image = Image.open(image_path)
    image = image.resize((300, 200))  # Resize for display in Tkinter
    photo = ImageTk.PhotoImage(image)
    image_label.config(image=photo)
    image_label.image = photo  # Keep a reference to avoid garbage collection
    root.after(2000, update_image)  # Schedule to update the image every 2 seconds

# Start updating images in Tkinter
update_image()

# Create a function to run the async task
def run_repeating_task():
    asyncio.run(repeating_task())

# Update the thread creation
repeating_thread = threading.Thread(target=run_repeating_task, daemon=True)

# Function to recognize speech after wake word detection
async def recognize_speech():
    with sr.Microphone() as source:
        logger.info("Listening for command...")
        try:
            # Adjust the timeout and phrase_time_limit to be more lenient
            recognizer.adjust_for_ambient_noise(source, duration=0.5)  # Add ambient noise adjustment
            audio = recognizer.listen(source, phrase_time_limit=5, timeout=5)  # Increased from 2,1 to 5,5
            user_voice_msg = recognizer.recognize_google(audio, language="zh-CN")
            logger.info(f"Recognized Speech: {user_voice_msg}")
            image_url = capture_and_save_photo()["file_path"]

            with open('prompts.yaml', 'r') as file:
                prompts = yaml.safe_load(file)
                
            res = await chat_internal(
                user_prompt=user_voice_msg,
                system_prompt=prompts["passive_system_prompt"]  ,
                image_url=image_url,
                chat_history=load_chat_history()
            )
            logger.info(f"Chat response: {res}")
            save_chat_history(res)
            
        except sr.WaitTimeoutError:
            logger.warning("No speech detected within timeout period")
        except sr.UnknownValueError:
            logger.warning("Could not understand the audio")
        except Exception as e:
            logger.error(f"Error during recognition: {e}", exc_info=True)

# Update the function to run the async recognition
def run_recognition():
    asyncio.run(recognize_speech())

# Callback function to execute on hot word detection
def on_wake_word_detected():
    global resume_repeating_task
    global repeating_thread
    logger.info("Hey Remy detected! Starting speech recognition...")

    # Pause repeating task
    resume_repeating_task.clear()
    
    # Start speech recognition in a separate thread with the new runner function
    recognition_thread = threading.Thread(target=run_recognition)
    recognition_thread.start()

    # Resume repeating task after recognition starts in background
    recognition_thread.join()  # Wait until the recognition is complete
    
    repeating_thread = threading.Thread(target=run_repeating_task, daemon=True)
    resume_repeating_task.set()
    repeating_thread.start()

# Function to listen for hot word
def listen_for_hotword():
    logger.info("Listening for 'Hey Remy' hot word...")
    
    porcupine = init_porcupine()
    try:
        pa = pyaudio.PyAudio()
        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )
        while True:
            pcm = audio_stream.read(porcupine.frame_length)
            pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)

            # Check if hot word is detected
            if porcupine.process(pcm_unpacked) >= 0:
                logger.info("Hot word detected!")
                
                audio_stream.stop_stream()
                audio_stream.close()
                
                on_wake_word_detected()  # Call function to handle the wake word
                
                audio_stream = pa.open(
                    rate=porcupine.sample_rate,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=porcupine.frame_length
                )
                
                logger.info("Resuming hot word detection...")

    except KeyboardInterrupt:
        logger.info("Exiting gracefully...")
        
    finally:
        porcupine.delete()
        pa.terminate() 

def main():
    # Set up a handler for KeyboardInterrupt (Ctrl+C)
    def signal_handler(sig, frame):
        logger.info("\nExiting gracefully...")
        resume_repeating_task.clear()  # Stop the repeating task
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)


    # Start the repeating task in a separate thread as a daemon
    # repeating_thread = threading.Thread(target=repeating_task, daemon=True)
    repeating_thread.start()

    # Start Tkinter mainloop
    root.mainloop()

    try:
        listen_for_hotword()

    except KeyboardInterrupt:
        logger.info("Exiting gracefully...")

if __name__ == "__main__":
    main()
