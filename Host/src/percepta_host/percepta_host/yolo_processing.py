import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLOWorld


class YoloProcessing(Node):
    def __init__(self):
        super().__init__('yolo_processing_node')

        self.bridge = CvBridge()
        self.model = YOLOWorld('yolov8s-worldv2.pt')
        self.model.set_classes(['cellphone', 'hand'])

        self.subscription = self.create_subscription(
            Image,
            '/image_raw',
            self.image_callback,
            10
        )

        self.publisher = self.create_publisher(
            Image,
            '/camera/yolo_output',
            10
        )

        self.get_logger().info('YOLO processing node started')

    def image_callback(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding='bgr8'
            )

            results = self.model(frame, verbose=False)
            annotated_frame = results[0].plot()

            output_msg = self.bridge.cv2_to_imgmsg(
                annotated_frame,
                encoding='bgr8'
            )
            output_msg.header = msg.header

            self.publisher.publish(output_msg)

        except Exception as error:
            self.get_logger().error(f'Image processing failed: {error}')


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