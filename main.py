from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
import asyncio


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
def reset_chat_history():
    chat_history = []
    save_chat_history(chat_history)


# Basic Configurations 
# AI configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ZHIPU_API_KEY = os.getenv('ZHIPU_API_KEY')

# Model settings
openai_model = 'gpt-4o-mini'
zhipuai_model = 'glm-4v'

# Choose AI provider
AI_PROVIDER = 'openai' # 'openai' | 'zhipuai', we have a bug with openai currently

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

app.mount("/static", StaticFiles(directory="./templates"), name="static")

@app.get("/")
async def home():
    return FileResponse("templates/index.html")

# Create uploads directory
upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
os.makedirs(upload_folder, exist_ok=True)

class ImageData(BaseModel):
    data: str

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
async def active_chat(
    message: str = Form(...), # user's message from frontend textarea input
    image_url: str = Form(...),
    user_prompt: str = prompts['active_user_prompt'],
    system_prompt: str = prompts['passive_system_prompt'].format(recipe=prompts['recipe']['egg']),
    chat_history: list = None
):
    chat_history = load_chat_history()
        
    # Use the message as the user_prompt
    # user_prompt = message
    
    return await chat_internal(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        image_url=image_url,
        chat_history=chat_history
    )

# Create a separate internal chat function for the existing logic
async def chat_internal(user_prompt, system_prompt, image_url, chat_history):
    """
    Process a chat with optional image input and maintain chat history.

    Args:
        user_prompt (str): The user's text input/question. Defaults to passive_user_prompt. It can also be the user's voice input (in string).
        system_prompt (str): System instructions for the AI. Defaults to passive_system_prompt.
        image_url (Optional[str]): Path to an image file to analyze. Defaults to None.
        chat_history (list): Previous chat messages. Defaults to loaded chat history.

    Returns:
        dict: Contains 'response' key with the AI's text response.

    Raises:
        HTTPException: 
            - 404 if image file not found
            - 500 for other processing errors

    The function:
    1. Validates the image file if provided
    2. Converts image to base64 format
    3. Constructs message array with system prompt, chat history, and current query
    4. Makes API call to AI provider
    5. Updates and saves chat history
    6. Returns AI response
    """
    
    if not os.path.exists(image_url):
        raise HTTPException(status_code=404, detail="Image file not found")

    try:
        # Open the image in binary mode
        # Read the image file into binary data
        with open(image_url, 'rb') as image_file:
            image_data = image_file.read()

        # Convert binary image data to base64 string format
        # This is required for sending images to the OpenAI API
        encoded_image = base64.b64encode(image_data).decode('utf-8')

        # Prepare the content for the API request
        # Start with the text message in the required format
        user_content = [{"type": "text", "text": user_prompt}]
        
        # If an image was provided, add it to the content
        # The image needs to be in data URL format: data:image/jpeg;base64,<base64 string>
        if image_url:
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}})

        # Prepare messages array starting with system prompt
        messages = [{'role': 'system', 'content': system_prompt}]
        
        # Add chat history
        for msg in chat_history:
            messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
        
        # Add current user message with image
        messages.append({'role': 'user', 'content': user_content})
        
        # Make API call with full message history
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=300
        )

        # Extract the AI's response from the API result
        # Convert the response object to a dictionary and get the message content
        response_dict = response.to_dict()
        # Update chat history with the new messages
        response_message = response_dict['choices'][0]['message']['content']
        
        chat_history.append({
            'role': 'user',
            'content': user_prompt
        })
        chat_history.append({
            'role': 'assistant', 
            'content': response_message
        })
        save_chat_history(chat_history)
        
        return {"response": response_message}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


    
if __name__ == "__main__":
    # reset chat history
    reset_chat_history()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
    
    # start_time = time.time()
    # asyncio.run(chat_internal(
    #     user_prompt=prompts['active_user_prompt'],
    #     system_prompt=prompts['active_system_prompt'], 
    #     image_url="./static/uploads/1729948639.8396459.jpg",
    #     chat_history=load_chat_history()
    # ))
    # end_time = time.time()
    # print(f"Execution time: {end_time - start_time:.2f} seconds")