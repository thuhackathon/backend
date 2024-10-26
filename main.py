from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import time
import cv2
import base64
import numpy as np
from openai import OpenAI
from typing import Optional
from dotenv import load_dotenv
from zhipuai import ZhipuAI
import yaml
import json
# Load environment variables
load_dotenv()

# Load prompts
with open('prompts.yaml', 'r') as file:
    prompts = yaml.safe_load(file)

# load Chat History, create a file if not exists
def load_chat_history():
    if os.path.exists('chat_history.json'):
        with open('chat_history.json', 'r') as file:
            chat_history = json.load(file)
    else:
        chat_history = []
    return chat_history

# save chat history, create a file if not exists
def save_chat_history(chat_history):
    with open('chat_history.json', 'w') as file:
        json.dump(chat_history, file)

# Basic Configurations 
# AI configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ZHIPU_API_KEY = os.getenv('ZHIPU_API_KEY')

# Model settings
openai_model = 'gpt-4o-mini'
zhipuai_model = 'glm-4-plus'

# Choose AI provider
AI_PROVIDER = 'openai' # 'openai' | 'zhipuai'

if AI_PROVIDER == 'openai':
    client = OpenAI(api_key=OPENAI_API_KEY)
    model = openai_model
elif AI_PROVIDER == 'zhipuai':
    client = ZhipuAI(api_key=ZHIPU_API_KEY)
    model = zhipuai_model
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to the API"}

# Create uploads directory
upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
os.makedirs(upload_folder, exist_ok=True)

class ImageData(BaseModel):
    data: str

class ChatRequest(BaseModel):
    message: str
    image_url: Optional[str] = None

@app.post("/process")
async def process_image(image_data: ImageData):
    try:
        # Removes the "data:image/jpeg;base64," prefix
        encoded_data = image_data.data.split(',')[1]  
        # Converts base64 to numpy array
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)  
        # Converts numpy array to OpenCV image
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)  

        # Generate a unique filename
        filename = f"{time.time()}.jpg"
        filepath = os.path.join(upload_folder, filename)

        # Save the image
        cv2.imwrite(filepath, img)

        return {"image": filepath}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/chat")
async def chat(chat_request: ChatRequest,
                system_prompt: str = prompts['passive_system_prompt'], 
                user_prompt: str = prompts['passive_user_prompt'],
                chat_history: list = load_chat_history()):
    
    if not os.path.exists(chat_request.image_url):
        raise HTTPException(status_code=404, detail="Image file not found")

    try:
        # Open the image in binary mode
        # Read the image file into binary data
        with open(chat_request.image_url, 'rb') as image_file:
            image_data = image_file.read()

        # Convert binary image data to base64 string format
        # This is required for sending images to the OpenAI API
        encoded_image = base64.b64encode(image_data).decode('utf-8')

        # Prepare the content for the API request
        # Start with the text message in the required format
        user_content = [{"type": "text", "text": chat_request.message}]
        
        # If an image was provided, add it to the content
        # The image needs to be in data URL format: data:image/jpeg;base64,<base64 string>
        if chat_request.image_url:
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}})

        # Make the API call to GPT-4 Vision
        # We send both the system message (defining the AI's role)
        # and the user's content (text + image)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt}, # a system prompt
                {'role': 'user', 'content': user_prompt + user_content}
            ]
        )

        # Extract the AI's response from the API result
        # Convert the response object to a dictionary and get the message content
        response_dict = response.to_dict()
        # Update chat history with the new messages
        
        chat_history.append({
            'role': 'user',
            'content': chat_request.message
        })
        chat_history.append({
            'role': 'assistant', 
            'content': response_dict['choices'][0]['message']['content']
        })
        save_chat_history(chat_history)
        
        return {"response": response_dict['choices'][0]['message']['content']}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)