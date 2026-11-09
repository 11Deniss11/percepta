import rclpy
from rclpy.node import Node
from std_msgs.msg import String

import socket
import threading


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#                                 INFO
#
#   The speech recognition is not performed within this script.
#   All speech recognition is handled on windows and the strings are
#   sent to this node via a TCP socket.
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



class SpeechRecognition(Node):
    def __init__(self):
        # Kept the original node name for compatibility with your existing launch files
        super().__init__('speech_recognition') 
        
        self.publisher_ = self.create_publisher(String, 'llm_prompt', 10)
        
        # Thread: Drain TCP Socket continuously for incoming text strings
        self.listen_thread = threading.Thread(target=self.tcp_listen_loop)
        self.listen_thread.daemon = True
        self.listen_thread.start()

    def tcp_listen_loop(self):
        tcp_ip = "0.0.0.0"
        tcp_port = 5005
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((tcp_ip, tcp_port))
        self.sock.listen(1)
        
        self.get_logger().info(f"Starting TCP Text Receiver on port {tcp_port}...")
        
        while rclpy.ok():
            try:
                # 1-second timeout allows the loop to periodically check if rclpy is still running
                self.sock.settimeout(1.0) 
                conn, addr = self.sock.accept()
                self.get_logger().info(f"Connected to speech sender at {addr}")
                
                # Using makefile allows us to easily read line-by-line, splitting on the '\n' 
                # that was added by the Windows sender script
                with conn, conn.makefile('r', encoding='utf-8') as f:
                    while rclpy.ok():
                        line = f.readline()
                        if not line:
                            # An empty read means the connection was closed by the sender
                            self.get_logger().warn("Connection closed by sender. Waiting for new connection...")
                            break
                        
                        text = line.strip()
                        if text:
                            self.process_text(text)
                            
            except socket.timeout:
                continue
            except Exception as e:
                if rclpy.ok():
                    self.get_logger().error(f"[TCP Listener Error]: {e}")
                break

    def process_text(self, text):
        # Log everything heard, matching your original functionality
        self.get_logger().info(f"Heard: '{text}'")
        
        # Check for trigger word
        if "laura" in text.lower():
            msg = String()
            msg.data = text
            self.publisher_.publish(msg)
            self.get_logger().info(f"Published: {msg.data}")

    def destroy_node(self):
        """Ensure the socket is properly closed when the node shuts down."""
        if hasattr(self, 'sock'):
            self.sock.close()
        super().destroy_node()

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