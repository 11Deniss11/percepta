import rclpy
from rclpy.node import Node
from std_msgs.msg import String

import socket
import threading
import speech_recognition as sr

class TCPAudioSource(sr.AudioSource):
    """A custom audio source that reads from a TCP socket server instead of a microphone."""
    def __init__(self, tcp_ip="0.0.0.0", tcp_port=5005): 
        self.tcp_ip = tcp_ip
        self.tcp_port = tcp_port
        
        # Audio configuration (must match Sender)
        self.CHUNK = 1024
        self.SAMPLE_RATE = 44100
        self.SAMPLE_WIDTH = 2
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allows instant restart of the ROS node without "Address already in use" errors
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        self.sock.bind((self.tcp_ip, self.tcp_port))
        self.sock.listen(1)
        self.conn, self.addr = self.sock.accept()
        
        self.conn.settimeout(0.1)
        self.stream = TCPStream(self.conn)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if hasattr(self, 'conn'):
            self.conn.close()
        self.sock.close()


class TCPStream:
    def __init__(self, conn):
        self.conn = conn
        self.buffer = b''
        self.packet_count = 0

    def read(self, size):
        # Keep receiving until we have exactly enough bytes
        connection_closed = False
        while len(self.buffer) < size:
            try:
                data = self.conn.recv(4096)
                if not data:
                    connection_closed = True
                    break
                self.buffer += data
                self.packet_count += 1
            except (socket.timeout, BlockingIOError):
                continue

        if connection_closed and len(self.buffer) < size:
            raise ConnectionError("The TCP audio sender disconnected")

        # Slice off exactly the requested amount and keep the remainder
        chunk = self.buffer[:size]
        self.buffer = self.buffer[size:]
        return chunk


class SpeechRecognition(Node):
    def __init__(self):
        # Set the node name (tag) to 'speech_recognition'
        super().__init__('speech_recognition')
        
        # Publisher for the transcribed text
        self.publisher_ = self.create_publisher(String, 'llm_prompt', 10)
        
        self.recognizer = sr.Recognizer()
        # Allow normal pauses between words without splitting one utterance.
        self.recognizer.pause_threshold = 1.0
        self.recognizer.non_speaking_duration = 0.8
        
        # Run the blocking listener in a separate daemon thread
        self.listen_thread = threading.Thread(target=self.transcription_loop)
        self.listen_thread.daemon = True
        self.listen_thread.start()

    def transcription_loop(self):
        self.get_logger().info("Starting TCP Receiver & Transcriber on port 5005...")
        
        # This will block until the Windows sender connects
        with TCPAudioSource() as source:
            self.get_logger().info(f"TCP socket bound and connected on port 5005.")
            self.get_logger().info("Calibrating for background network static... (Wait 2 seconds)")
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
            
            self.get_logger().info("Ready! Listening for TCP audio streams...")
            
            # Loop while the ROS 2 system is running
            while rclpy.ok():
                try:
                    # timeout=1.0 allows the loop to check rclpy.ok() periodically
                    audio = self.recognizer.listen(source, timeout=1.0)
                    
                    self.get_logger().debug("Processing speech chunk...")
                    text = self.recognizer.recognize_whisper(audio, model="tiny", language="english")
                    
                    if "laura" in text.lower():
                        # Publish the result to the ROS network
                        msg = String()
                        msg.data = text.strip()
                        self.publisher_.publish(msg)
                        self.get_logger().info(f"Published: {msg.data}")
                        
                except sr.WaitTimeoutError:
                    # Expected if nobody is speaking; just loop back and check rclpy.ok()
                    pass
                except sr.UnknownValueError:
                    self.get_logger().warn("[Could not understand audio]")
                except sr.RequestError as e:
                    self.get_logger().error(f"[Error]: {e}")
                except ConnectionError as e:
                    self.get_logger().error(f"[Audio connection lost]: {e}")
                    break
                except Exception as e:
                    self.get_logger().error(f"[Unexpected Error]: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = SpeechRecognition()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Keyboard interrupt, shutting down...")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()