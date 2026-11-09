#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from std_msgs.msg import String
import ollama

from sensor_msgs.msg import Image
from cv_bridge import CvBridge          
import cv2


OLLAMA_MODEL = 'qwen3.5:2b'


class QwenNode(Node):
    def __init__(self):
        super().__init__('llm')
        
        # Subscribe to incoming text prompts
        self.subscription = self.create_subscription(
            String,
            'llm_prompt',
            self.prompt_callback,
            10
        )

        # Subscribe to incoming video frames
        self.subscription_image = self.create_subscription(
            Image,
            '/image_raw',
            self.image_callback,
            QoSProfile(
                depth=1,
                history=QoSHistoryPolicy.KEEP_LAST,
                reliability=QoSReliabilityPolicy.BEST_EFFORT,
            )
        )
        
        # Publisher for the model's responses for tts
        self.publisher_tts = self.create_publisher(String, '/say', 10)

        self.publisher_yolo = self.create_publisher(String, '/yolo_classes', 10)

        # State variables for image processing
        self.latest_image_msg = None
        self.bridge = CvBridge()

        self.get_logger().info("Qwen3.5 2B ROS2 Node initialized. Waiting for prompts on '/llm_prompt'...")
        

    def image_callback(self, msg):
        # Constantly overwrite with the most recent frame
        self.latest_image_msg = msg

    def prompt_callback(self, msg):
        prompt = msg.data
        self.get_logger().info(f"Received prompt: '{prompt}'")

        message_payload = {'role': 'user', 'content': prompt}

        #Provide basic context to the model
        system_msg = {
            'role': 'system', 
            'content': 'You are an AI assistant named Laura responding to voice commands. Your purpose is to integrate a system of sensors to help blind people. If you are asked for help to find something, or where something is, simply state "You are looking for [object class for yolo]". ALWAYS put the object class of the object being looked for inside of square brackets. For example, if someone asks "Where are my keys?", you should respond with "You are looking for [keys]". Keep your answers short and concise.'
        }

        # Check if we have received an image yet
        if self.latest_image_msg is not None:
            try:
                # Convert ROS Image message to OpenCV BGR image
                cv_image = self.bridge.imgmsg_to_cv2(self.latest_image_msg, desired_encoding='bgr8')
                
                # Compress to JPEG to save memory/transfer time to Ollama
                success, buffer = cv2.imencode('.jpg', cv_image)
                if success:
                    img_bytes = buffer.tobytes()
                    # Append the image bytes to the Ollama payload
                    message_payload['images'] = [img_bytes]
                    self.get_logger().info("Appended latest camera frame to prompt.")
                else:
                    self.get_logger().error("Failed to encode image to JPEG.")
            except Exception as e:
                self.get_logger().error(f"Failed to process image with cv_bridge: {e}")
        else:
            self.get_logger().warn("No image received yet on '/image_raw'. Sending text only.")
        
        try:
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[system_msg, message_payload],
                think=False,
                options={
                    # Ollama uses CUDA when a compatible GPU is available and
                    # falls back to CPU when the container has no GPU access.
                    'num_gpu': -1,
                    'reasoning_effort': 0,
                    'temperature': 0.0,   # Eliminates sampling randomness; fastest token selection
                    #'num_predict': 20,    # Hard cap on output length. It will cut off mid-sentence, but return instantly.
                    'num_ctx': 512,       # Shrinks the context window to reduce memory/compute overhead
                    'top_k': 10,          # Drastically reduces the vocabulary pool it evaluates per token
                    'top_p': 0.1          # Further restricts token evaluation
                }
            )
            
            reply_text = response['message']['content']
            
            # Publish the result
            reply_msg = String()
            reply_msg.data = reply_text

            if not "[" in reply_msg.data:
                self.publisher_tts.publish(reply_msg)
            
                self.get_logger().info("Response published successfully.")
            else:
                # Extract the object class from the response
                start_idx = reply_msg.data.find("[") + 1
                end_idx = reply_msg.data.find("]")
                if start_idx > 0 and end_idx > start_idx:
                    object_class = reply_msg.data[start_idx:end_idx]
                    yolo_msg = String()
                    yolo_msg.data = object_class
                    self.publisher_yolo.publish(yolo_msg)
                    self.get_logger().info(f"Published object class '{object_class}' to '/yolo_classes'.")
                else:
                    self.get_logger().warn("No valid object class found in the response.")

            
        except Exception as e:
            self.get_logger().error(f"Failed to query Ollama: {str(e)}")

def main(args=None):
    rclpy.init(args=args)
    node = QwenNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
        
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()