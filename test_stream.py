import cv2
import sys

# ESP32-CAM Stream URL
STREAM_URL = "http://192.168.43.105/capture"
WINDOW_NAME = "ESP32-CAM Stream"

def main():
    print(f"Connecting to ESP32-CAM stream at: {STREAM_URL}")
    
    # Initialize video capture with the stream URL
    cap = cv2.VideoCapture(STREAM_URL)
    
    # Check if stream opened successfully
    if not cap.isOpened():
        print(f"Error: Unable to open video stream from {STREAM_URL}")
        print("Please verify:")
        print(" 1. ESP32-CAM is powered on and connected to the same Wi-Fi network.")
        print(" 2. IP address and port are correct.")
        print(" 3. Stream URL is accessible in a web browser.")
        sys.exit(1)
        
    print("Stream connected successfully. Press 'q' or 'Q' to exit.")
    
    try:
        while True:
            ret, frame = cap.read()
            
            # If frame was not read correctly
            if not ret or frame is None:
                print("Frame not received")
                break
            
            # Display the video frame
            cv2.imshow(WINDOW_NAME, frame)
            
            # Exit condition on 'q' or 'Q' key press
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                print("Exiting stream on user request ('q' pressed).")
                break
                
    except KeyboardInterrupt:
        print("\nInterrupted by user. Closing...")
    finally:
        # Release the video capture and destroy OpenCV windows
        cap.release()
        cv2.destroyAllWindows()
        print("Cleaned up resources. Stream closed.")

if __name__ == "__main__":
    main()
