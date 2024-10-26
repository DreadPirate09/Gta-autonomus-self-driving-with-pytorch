import os
import torch
from torchvision import transforms
from PIL import Image
from gta_v_driver_model import GTAVDriverModel
from pilot import Pilot
import mss
import pygame

# Load the trained model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = GTAVDriverModel().to(device)
model.load_state_dict(torch.load('gtav_driver_model.pth'))
model.eval() 

transform = transforms.Compose([
    transforms.Resize((160, 640)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def read_last_speed(log_file_path):

    with open(log_file_path, 'rb') as f:
        f.seek(-2, os.SEEK_END) 
        while f.read(1) != b'\n': 
            f.seek(-2, os.SEEK_CUR) 
        last_line = f.readline().decode().strip() 
    return float(last_line) 


def preprocess_frame(frame):

    pil_image = Image.frombytes('RGB', frame.size, frame.rgb)
    

    pil_image = pil_image.resize((640, 360), Image.BICUBIC)
    pil_image = pil_image.crop(box=(0, 200, 640, 360))

    transformed_image = transform(pil_image)

    return transformed_image

def run_inference(model, frame, speed):

    frame_tensor = preprocess_frame(frame).unsqueeze(0).to(device)  # Add batch dimension
    
    speed_tensor = torch.tensor([[speed]], dtype=torch.float32).to(device)
    
    model_input = torch.cat((speed_tensor, frame_tensor.flatten(start_dim=1)), dim=1)
    
    # Perform inference
    with torch.no_grad():
        predictions = model(model_input)
    
    # Return the predictions (steering, throttle, brake)
    steering, throttle, brake = predictions[0].cpu().numpy()
    return steering, throttle, brake

# use the path for your speed log generated by the cs script
log_speed_path = os.getcwd()+'\\VehicleSpeedLog.txt'

sct = mss.mss()
mon = {'top': 0, 'left': 0, 'width': 1600, 'height': 1200}
driver = Pilot()

while True:

    sct_img = sct.grab(mon)

    speed = read_last_speed(log_speed_path)
    
    steering, throttle, brake = run_inference(model, sct_img, speed)
    driver.sendIt(steering, throttle, 1.0 - brake)
    
    print(f"Steering: {steering:.4f}, Throttle: {throttle:.4f}, Brake: {brake:.4f}")


