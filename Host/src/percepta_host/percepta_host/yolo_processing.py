from math import hypot

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from geometry_msgs.msg import PointStamped
from sensor_msgs.msg import Image
from std_msgs.msg import String
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
        self.image_subscription = self.create_subscription(
            Image,
            '/image_raw',
            self.image_callback,
            qos
        )

        self.classes_subscription = self.create_subscription(
            String,
            '/yolo_classes',
            self.classes_callback,
            qos
        )

        self.publisher = self.create_publisher(
            Image,
            '/yolo_output',
            qos
        )
        self.coordinate_difference_publisher = self.create_publisher(
            PointStamped,
            '/yolo_coordinate_difference',
            qos
        )

        self.get_logger().info('YOLO processing node started')

    def classes_callback(self, msg: String):
        object_class = msg.data.strip()
        if not object_class:
            self.get_logger().warning('Ignoring empty YOLO classes message')
            return

        self.model.set_classes([object_class, 'hand'])
        self.get_logger().info(f'YOLO classes updated: {[object_class]}')

    def image_callback(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding='bgr8'
            )

            results = self.model(frame, conf=0.07, verbose=False)
            result = results[0]
            best_hand = None
            best_object = None
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                confidence = float(box.conf[0])
                class_name = result.names[int(box.cls[0])].lower()
                detection = (confidence, center_x, center_y)
                if class_name == 'hand':
                    if best_hand is None or confidence > best_hand[0]:
                        best_hand = detection
                elif best_object is None or confidence > best_object[0]:
                    best_object = detection

            self.coordinate_difference_publisher.publish(
                self.coordinate_difference_message(msg, best_hand, best_object)
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

    @staticmethod
    def coordinate_difference_message(
        image_msg: Image,
        hand: tuple[float, float, float] | None,
        object_detection: tuple[float, float, float] | None,
    ) -> PointStamped:
        coordinate_msg = PointStamped()
        coordinate_msg.header = image_msg.header
        if hand is not None and object_detection is not None:
            _, hand_x, hand_y = hand
            _, object_x, object_y = object_detection
            difference_x = object_x - hand_x
            difference_y = object_y - hand_y
            if hypot(difference_x, difference_y) >= 15:
                coordinate_msg.point.x = difference_x
                coordinate_msg.point.y = difference_y
        coordinate_msg.point.z = 0.0
        return coordinate_msg


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