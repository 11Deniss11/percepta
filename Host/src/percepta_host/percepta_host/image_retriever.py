import socket

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image


class UdpImagePublisher(Node):
    def __init__(self):
        super().__init__('udp_image_publisher')

        self.declare_parameter('udp_address', '0.0.0.0')
        self.declare_parameter('udp_port', 5000)
        self.declare_parameter('topic', 'image_raw')
        self.declare_parameter('frame_id', 'camera')

        address = self.get_parameter('udp_address').value
        port = self.get_parameter('udp_port').value
        topic = self.get_parameter('topic').value
        self.frame_id = self.get_parameter('frame_id').value

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        self.socket.bind((address, port))
        self.socket.setblocking(False)

        self.bridge = CvBridge()
        self.publisher = self.create_publisher(Image, topic, 10)

        # 30 Hz polling
        self.timer = self.create_timer(1.0 / 30.0, self.receive_frame)

        self.get_logger().info(
            f'Receiving JPEG frames on udp://{address}:{port}, '
            f'publishing to {topic}'
        )

    def receive_frame(self):
        try:
            # Drain queued packets and process only the newest frame.
            packet = None

            while True:
                try:
                    packet, _ = self.socket.recvfrom(65535)
                except BlockingIOError:
                    break

            if packet is None:
                return

            encoded = np.frombuffer(packet, dtype=np.uint8)
            frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

            if frame is None:
                self.get_logger().warning('Invalid JPEG frame')
                return

            message = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            message.header.stamp = self.get_clock().now().to_msg()
            message.header.frame_id = self.frame_id

            self.publisher.publish(message)

            self.get_logger().debug(f'Published frame')

        except OSError as error:
            self.get_logger().error(f'UDP receive error: {error}')

    def destroy_node(self):
        self.socket.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = UdpImagePublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()