import socket
import time
import speech_recognition as sr


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#                                 INFO
#
#   This script captures audio from the local windows microphone and 
#   performs speech recognition in windows. It then sends the strings
#   sentence-by-sentence to WSL via TCP.
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# Network configuration
TCP_IP = "172.26.212.68"     
TCP_PORT = 5005

def connect_with_retry():
    """Continuously attempts to connect to the ROS2 receiver, creating a new socket each time."""
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"Attempting to connect to TCP server at {TCP_IP}:{TCP_PORT}...")
            sock.connect((TCP_IP, TCP_PORT))
            print("Connected successfully! Ready to send transcribed speech.")
            return sock
        except ConnectionRefusedError:
            print("ROS2 receiver not running. Retrying in 3 seconds...")
            time.sleep(3)
        except Exception as e:
            print(f"Network error ({e}). Retrying in 3 seconds...")
            time.sleep(3)

def main():
    # Initialize Speech Recognition
    r = sr.Recognizer()
    r.pause_threshold = 0.5  
    
    # Attempt initial connection (blocks until ROS2 is ready)
    sock = connect_with_retry()
    
    print("\nStarting Local Microphone Receiver & Transcriber...")
    
    with sr.Microphone() as source:
        print("Calibrating for background noise... (Wait 2 seconds)")
        r.adjust_for_ambient_noise(source, duration=2)
        
        print("\nReady! Listening to the microphone... (Press Ctrl+C to stop)")
        
        try:
            while True:
                audio = r.listen(source)
                
                try:
                    text = r.recognize_whisper(audio, model="tiny", language="english").strip()
                    
                    if text:
                        print(f"You said: {text}")
                        message = text + "\n"
                        
                        try:
                            # Attempt to send the text
                            sock.sendall(message.encode('utf-8'))
                        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as e:
                            print(f"\n[Network Error]: Connection lost ({e}). Attempting to reconnect...")
                            sock.close()
                            
                            # Block and wait until ROS2 is back online
                            sock = connect_with_retry()
                            
                            # Send the pending message that failed when the connection dropped
                            sock.sendall(message.encode('utf-8'))
                            print("Pending message sent successfully.")
                            
                except sr.UnknownValueError:
                    print("[Could not understand audio]")
                except sr.RequestError as e:
                    print(f"[Speech Recognition Error]: {e}")
                    
        except KeyboardInterrupt:
            print("\nShutting down receiver.")
        finally:
            # Clean up resources
            sock.close()
            print("Socket closed.")

if __name__ == "__main__":
    main()