import rclpy
from rclpy.node import Node
from rclpy.qos import QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLOWorld


class YoloProcessing(Node):
    def __init__(self):
        super().__init__('yolo_processing_node')

        self.bridge = CvBridge()
        self.model = YOLOWorld('yolov8s-worldv2.pt')
        self.model.set_classes(['hand'])

        qos = QoSProfile(
            depth=1,
            history=QoSHistoryPolicy.KEEP_LAST,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
        )
        self.subscription = self.create_subscription(
            Image,
            '/image_raw',
            self.image_callback,
            qos
        )

        self.publisher = self.create_publisher(
            Image,
            '/camera/yolo_output',
            qos
        )

        self.get_logger().info('YOLO processing node started')

    def image_callback(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding='bgr8'
            )

            results = self.model(frame, verbose=False)
            result = results[0]
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                confidence = float(box.conf[0])
                self.get_logger().debug(
                    f'Hand coordinates: center=({center_x:.1f}, {center_y:.1f}), '
                    f'box=({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}), '
                    f'confidence={confidence:.3f}'
                )
            annotated_frame = result.plot()

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