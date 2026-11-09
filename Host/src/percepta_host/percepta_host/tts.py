import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import os
import wave
import socket
from ament_index_python.packages import get_package_share_directory
from piper import PiperVoice

class TTSNode(Node):
    def __init__(self):
        super().__init__('tts_node')
        
        # 1. Subscribe to the topic where you will send text
        self.subscription = self.create_subscription(
            String,
            '/say',
            self.text_callback,
            10
        )
        
        # 2. Locate and load the Piper model
        package_share = get_package_share_directory('percepta_host')
        model_path = os.path.join(package_share, 'weights', 'en_US-hfc_female-medium.onnx')
        
        try:
            self.voice = PiperVoice.load(model_path)
            self.get_logger().info(f"Successfully loaded Piper model from {model_path}")
        except Exception as e:
            self.get_logger().error(f"Failed to load Piper model: {e}")
            self.voice = None

    def text_callback(self, msg):
        text = msg.data
        self.get_logger().info(f'Synthesizing text: "{text}"')
        
        if self.voice is None:
            self.get_logger().error("Cannot synthesize, voice model is not loaded.")
            return

        wav_path = "/tmp/latest_speech.wav"
        try:
            # 1. Synthesize the text to a local WAV file inside Docker
            with wave.open(wav_path, "wb") as wav_file:
                self.voice.synthesize_wav(text, wav_file)
            
            # 2. Transmit the file to Windows over Port 5001
            host = 'host.docker.internal'
            port = 5001
            
            with open(wav_path, 'rb') as f:
                wav_data = f.read()
                
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((host, port))
            client_socket.sendall(wav_data)
            client_socket.close()
            
            self.get_logger().info(f"Successfully sent audio to Windows on port {port}")
            
        except Exception as e:
            self.get_logger().error(f"Error during synthesis or TCP transfer: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = TTSNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()