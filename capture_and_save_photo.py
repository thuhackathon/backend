import cv2
import base64
import os
import time
import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk

latest_img_path = ""  # Global variable to store the latest image path

def capture_and_save_photo() -> dict[str, str]:
    """Returns:
        dict[str, str]: Dictionary containing:
            - 'base64': Base64 encoded image data with data URI prefix (str)
            - 'file_path': Path where the image file was saved (str)
    """
    global latest_img_path  # Update the global variable
    
    # Initialize webcam
    video_capture = cv2.VideoCapture(1)
    if not video_capture.isOpened():
        video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        raise Exception("Could not open webcam")

    try:
        # Add warm-up time for the camera to adjust
        for _ in range(10):  # Capture several frames to let camera adjust
            video_capture.read()
            time.sleep(0.1)  # Small delay between frames

        # Capture single frame
        ret, frame = video_capture.read()
        if not ret:
            raise Exception("Failed to capture frame")

        # Create uploads directory if it doesn't exist
        upload_dir = "statics/uploads"
        os.makedirs(upload_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp = int(time.time())
        file_name = f"capture_{timestamp}.jpg"
        file_path = os.path.join(upload_dir, file_name)

        # Save image to file
        cv2.imwrite(file_path, frame)

        latest_img_path = file_path  # Update the global variable with the file path

        # Convert to base64
        _, buffer = cv2.imencode('.jpg', frame)
        base64_data = base64.b64encode(buffer).decode('utf-8')
        
        return {
            'base64': f"data:image/jpeg;base64,{base64_data}",
            'file_path': file_path
        }

    finally:
        video_capture.release()

def update_latest_image_label(label):
    """Function to update the Tkinter label with the latest captured image."""
    try:
        capture_and_save_photo()  # Capture and update latest image path
        # Load the captured image and display it in Tkinter
        image = Image.open(latest_img_path)
        image = image.resize((300, 200))  # Resize for display in Tkinter
        photo = ImageTk.PhotoImage(image)
        label.config(image=photo)
        label.image = photo  # Keep a reference to avoid garbage collection
    except Exception as e:
        label.config(text=f"Error: {str(e)}")


if __name__ == "__main__":
    # Tkinter setup
    root = tk.Tk()
    root.title("Latest Captured Image")
    root.geometry("400x300")

    # Label to show the latest captured image
    latest_img_label = Label(root, text="No image captured yet.")
    latest_img_label.pack(pady=20)

    # Button to capture a photo and update the label with the image
    capture_button = tk.Button(root, text="Capture Photo", command=lambda: update_latest_image_label(latest_img_label))
    capture_button.pack(pady=10)

    root.mainloop()
