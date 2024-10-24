import numpy as np 
import cv2
from threading import Thread 
from PIL import Image 
import io 
import requests, base64
import json 

class VLM:

    def __init__(self, url, api_key, callback):
        self.url = url
        self.busy = False 
        self.reply = ""
        self.api_key = api_key
        self.callback = callback 
        
    def _encode_image(self, image):
        """ Resize image, encode as jpeg to shrink size then convert to b64 for upload """

        if isinstance(image, str): #file path
            image = Image.open(image).convert("RGB")
        elif isinstance(image, Image.Image): #pil image 
            image = image.convert("RGB")
        elif isinstance(image, np.ndarray): #cv2 / np array image 
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(image)
        else:
            print(f"Unsupported image input: {type(image)}")
            return None 
            
        image = image.resize((336,336)) #TODO centercrop or pad square then resize 
        buf = io.BytesIO() #temporary buffer to save processed image 
        image.save(buf, format="JPEG")
        image = buf.getvalue()
        image_b64 = base64.b64encode(image).decode()
        assert len(image_b64) < 180_000, "Image to large to upload."
        return image_b64

    def _call(self, message, image=None, callback_args={}):

        try:
            image_b64 = self._encode_image(image)
            headers = {
              "Authorization": f"Bearer {self.api_key}",
              "Accept": "application/json"
            }
        
            payload = {
              "messages": [
                {
                  "role": "user",
                  "content": f'{message} Here is the image: <img src="data:image/jpeg;base64,{image_b64}" />'
                }
              ],
              "max_tokens": 128,
              "temperature": 0.20,
              "top_p": 0.70,
              "stream": False
            }
        
            response = requests.post(self.url, headers=headers, json=payload)
            self.reply = response.json()["choices"][0]["message"]["content"]
        finally:
            self.busy = False 

        self.callback(self.reply, **callback_args) 

    def __call__(self, message, image=None, **kwargs):
        if self.busy:
            print("VLM is busy")
            return None
        
        else:
            self.busy = True 
            Thread(target=self._call, args=(message, image, kwargs)).start()