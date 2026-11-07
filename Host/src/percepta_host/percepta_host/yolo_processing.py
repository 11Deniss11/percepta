import rclpy
from rclpy.node import Node


class YoloProcessing(Node):
    def __init__(self):
        super().__init__('my_node')
        self.get_logger().info('My node started')


def main(args=None):
    rclpy.init(args=args)
    node = YoloProcessing()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()