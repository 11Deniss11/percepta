import rclpy
from rclpy.node import Node
from std_msgs.msg import String

#   This node currently doesn't serve much of a role. It blindy publishes
#   dummy instructions to the /dummy_instructions topic every second for debugging

class DummyPublisher(Node):
    def __init__(self):
        super().__init__('dummy_publisher')

        # Create a publisher on topic '/dummy_instructions' with queue depth 10
        self.publisher_ = self.create_publisher(
            String,
            'llm_prompt',
            10
        )

        # Create a timer running every 1.0 seconds
        timer_period = 5.0  # seconds

        # Uses witchcraft to create a timer
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.count = 0
        self.get_logger().info('Dummy Publisher node started, publishing every 1s...')

    def timer_callback(self):
        # Construct and publish the message
        msg = String()
        #msg.data = f'0.0, 0.0, 100.0, 100.0'  # Dummy instruction data
        msg.data = "Hey Laura, where is my soda?"
        
        self.publisher_.publish(msg)
        self.get_logger().info(f'Published: "{msg.data}"')
        
        self.count += 1


def main(args=None):
    rclpy.init(args=args)
    node = DummyPublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()