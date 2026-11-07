import rclpy
from std_msgs.msg import String
from rclpy.node import Node

#    To use this method, publish coordinates to /planar_instructions_topic, and this node will receive them and print them to the console.

class PlanarInstructions(Node):
    def __init__(self):
        super().__init__('planar_instructions')
        self.get_logger().info('Planar Instructions node started')

        # PARAMETERS
        self.declare_parameter('table_height', 0.5) # Vertical height between table and camera in meters

        # Create the subscriber
        # Arguments: (MessageType, 'topic_name', callback_function, qos_depth)
        self.subscription = self.create_subscription(
            String,
            '/planar_instructions_topic',
            self.instructions_callback,
            10  # Max number of stored messages while wiaitng for processing to finish
        )
        self.subscription  # Prevent unused variable warning

    #Called whenever a message is received from /planar_instructions_topic
    def instructions_callback(self, msg: String):
        self.get_logger().info(f'Received instruction: "{msg.data}"')

        msg.data = msg.data.strip()  # Remove any leading/trailing whitespace

        # Split the string into a list of strings and convert to float
        # Conatins screen x, y coordinates of the and and target
        hand_x, hand_y, target_x, target_y = map(float, msg.data.split(","))

        s_vector = (target_x - hand_x, target_y - hand_y)  # Vector from hand to target

        

def main(args=None):
    rclpy.init(args=args)
    node = PlanarInstructions()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()