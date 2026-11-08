import rclpy
from rclpy.node import Node
from std_msgs.msg import String

import socket
import threading
import speech_recognition as sr
from collections import deque

class UDPAudioSource(sr.AudioSource):
    """A custom audio source that reads from a UDP socket instead of a microphone."""
    def __init__(self, udp_ip="0.0.0.0", udp_port=5005): 
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        
        # Audio configuration (must match Sender)
        self.CHUNK = 1024
        self.SAMPLE_RATE = 44100
        self.SAMPLE_WIDTH = 2
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.udp_ip, self.udp_port))
        
        # Set a timeout so recvfrom doesn't block forever, but doesn't instantly crash
        self.sock.settimeout(0.1)
        self.stream = self.UDPStream(self.sock)

    class UDPStream:
        def __init__(self, sock):
            self.sock = sock
            self.pending = deque()
            self.packet_count = 0

        def read(self, size):
            while not self.pending:
                try:
                        data, addr = self.sock.recvfrom(4096)
                        if not data:
                            continue
                        print(".", end="", flush=True)
                        self.packet_count += 1
                        self.pending.append(data)
                except (socket.timeout, BlockingIOError):
                    return b'\x00' * size

            packet = self.pending.popleft()
            if len(packet) <= size:
                return packet.ljust(size, b'\x00')

            chunk = packet[:size]
            remainder = packet[size:]
            if remainder:
                self.pending.appendleft(remainder)
            return chunk

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.sock.close()

class SpeechRecognition(Node):
    def __init__(self):
        # Set the node name (tag) to 'speech_recognition'
        super().__init__('speech_recognition')
        
        # Publisher for the transcribed text
        self.publisher_ = self.create_publisher(String, 'recognized_speech', 10)
        
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.5
        
        # Run the blocking listener in a separate daemon thread
        self.listen_thread = threading.Thread(target=self.transcription_loop)
        self.listen_thread.daemon = True
        self.listen_thread.start()

    def transcription_loop(self):
        self.get_logger().info("Starting UDP Receiver & Transcriber on port 5005...")
        
        with UDPAudioSource() as source:
            self.get_logger().info(
                f"UDP socket bound on 0.0.0.0:5005 "
                f"(send audio to this machine's UDP address)"
            )
            self.get_logger().info("Calibrating for background network static... (Wait 2 seconds)")
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
            if source.stream.packet_count == 0:
                self.get_logger().warn(
                    "No UDP audio packets received yet. Verify the sender uses this "
                    "machine's reachable IP and UDP port 5005, not 127.0.0.1 from "
                    "inside a different network namespace."
                )
            
            self.get_logger().info("Ready! Listening for UDP audio streams...")
            
            # Loop while the ROS 2 system is running
            while rclpy.ok():
                try:
                    # timeout=1.0 allows the loop to check rclpy.ok() periodically
                    # rather than blocking indefinitely if there is no audio
                    audio = self.recognizer.listen(source, timeout=1.0)
                    
                    self.get_logger().debug("Processing speech chunk...")
                    text = self.recognizer.recognize_whisper(audio, model="tiny", language="english")
                    
                    if text.strip():
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