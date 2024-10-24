import argparse
import cv2 
from time import sleep 
from vlm import VLM 
from queue import Queue 
from api_server import FlaskServer 


response_dict = dict() 
overlay_output = ""


def _draw_text(image, text, x, y, text_color):
    """Draw text on an image using OpenCV"""
    # Get text size
    font_scale = 1
    thickness = 2
    (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    text_height += baseline

    # Put text on the image
    cv2.putText(image, text, (x, y + text_height - baseline), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, thickness)

def draw_lines(image, text, x, y, **kwargs):
    """Draw text on an image with word wrapping using OpenCV"""

    if text is None:
        return y

    text_color = kwargs.get("text_color", (255, 255, 255))  # Default white
    line_spacing = kwargs.get("line_spacing", 42)
    line_length = kwargs.get("line_length", 100)

    # Split text into words
    words = text.split()
    current_line = ""
    y_offset = y

    for word in words:
        if len(current_line) + len(word) <= line_length:
            current_line += word + " "
        else:
            _draw_text(image, current_line.strip(), x, y_offset, text_color)
            current_line = word + " "
            y_offset += line_spacing

    if current_line:
        _draw_text(image, current_line.strip(), x, y_offset, text_color)
        y_offset += line_spacing

    return y_offset


def vlm_callback(reply, **kwargs):
    global response_dict 
    global overlay_output

    prompt_id = kwargs.get("prompt_id")

    response_dict[prompt_id] = reply 
    overlay_output = reply 

def main(model_url, video_file, api_key, port, overlay=False):
    global response_dict 
    global overlay_output 

    prompt_queue = Queue() 

    flask_server = FlaskServer(prompt_queue, response_dict, port=port)
    flask_server.start_flask()

    #open video file 
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return
    
    vlm = VLM(model_url, api_key, callback=vlm_callback)

    prompt = ""
    prompt_id = ""
    while True:
        #Get new frame
        ret, frame = cap.read() #Get new Frame 

        #Check frame return is valid 
        if not ret:
            break 

        #Get new prompt 
        if not prompt_queue.empty():
            print("updating prompt")
            message = prompt_queue.get()
            prompt = message.data
            prompt_id = message.id 

        #VLM available, call on latest frame 
        if vlm.busy == False:
            vlm(prompt, frame, prompt_id=prompt_id) #call on latest prompt 
            
    
        #Output overlay if enabled
        if overlay:
            draw_lines(frame, overlay_output, 20, 20)
            cv2.imshow("Overlay", frame)
            if cv2.waitKey(30) & 0xFF == ord('q'):
                break 

    
    #clean up
    cap.release()
    cv2.destroyAllWindows() 

if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description="Process a model and a video file.")

    # Add the arguments
    parser.add_argument('--model_url',
                        type=str,
                        required=True,
                        help='The path to the model file')

    parser.add_argument('--video_file',
                        type=str,
                        required=True,
                        help='The path to the video file')
    
    parser.add_argument("--api_key", type=str, required=True, help="API Key")

    parser.add_argument("--port", type=int, required=True, help="Flask Port")

    parser.add_argument("--overlay", action="store_true", help="Enable VLM overlay")

    # Execute the parse_args() method
    args = parser.parse_args()

    # Call the main function
    main(args.model_url, args.video_file, args.api_key, args.port, overlay=args.overlay)
