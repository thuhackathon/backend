import cv2
import base64
import os
import time

def capture_and_save_photo() -> dict[str, str]:
    """Returns:
        dict[str, str]: Dictionary containing:
            - 'base64': Base64 encoded image data with data URI prefix (str)
            - 'file_path': Path where the image file was saved (str)
    """
    # Initialize webcam
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

        # Convert to base64
        _, buffer = cv2.imencode('.jpg', frame)
        base64_data = base64.b64encode(buffer).decode('utf-8')
        
        return {
            'base64': f"data:image/jpeg;base64,{base64_data}",
            'file_path': file_path
        }

    finally:
        video_capture.release()

if __name__ == "__main__":
    # Test the function
    try:
        result = capture_and_save_photo()
        print(f"Photo saved to: {result['file_path']}")
        print("Base64 data:", result['base64'][:50] + "...")  # Print first 50 chars of base64
    except Exception as e:
        print(f"Error: {str(e)}")