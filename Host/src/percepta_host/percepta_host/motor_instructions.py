import rclpy
from geometry_msgs.msg import PointStamped
from rclpy.node import Node
from rclpy.qos import QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
import socket

class MotorInstructions(Node):

    MAX_POWER_DIST = 500
    MIN_POWER_DIST = 50

    MIN_POWER = 0.2

    def __init__(self):
        super().__init__('motor_instructions')
        self.get_logger().info('Motor Instructions node started')

        # UDP socket parameters
        self.declare_parameter('udp_address', '172.20.10.2')
        self.declare_parameter('udp_port', 5000)

        # Initialize UDP socket
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        qos = QoSProfile(
            depth=1,
            history=QoSHistoryPolicy.KEEP_LAST,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
        )

        # Create the subscriber
        # Arguments: (MessageType, 'topic_name', callback_function, qos_depth)
        self.subscription = self.create_subscription(
            PointStamped,
            '/yolo_coordinate_difference',
            self.instructions_callback,
            qos
        )
        self.subscription  # Prevent unused variable warning

    #Called whenever a message is received from /planar_instructions_topic
    def instructions_callback(self, msg: PointStamped):
        x_difference = msg.point.x
        y_difference = msg.point.y

        motor_nx, motor_px, motor_ny, motor_py = 0.0, 0.0, 0.0, 0.0

        #X motor magnitude
        x_magnitude = self.motor_power(abs(x_difference))

        #Y motor magnitude
        y_magnitude = self.motor_power(abs(y_difference))

        # Set x_motor powers
        if x_difference < 0:
            motor_nx = x_magnitude
        else:
            motor_px = x_magnitude

        # Set y_motor powers
        if y_difference < 0:
            motor_ny = y_magnitude
        else:
            motor_py = y_magnitude

        # Retreive UDP parameters
        target_ip = self.get_parameter('udp_address').value
        target_port = self.get_parameter('udp_port').value

        # Send the motor instructions as a UDP packet
        payload = f"{motor_nx:.3f},{motor_px:.3f},{motor_ny:.3f},{motor_py:.3f}"
        try:
            self.udp_socket.sendto(payload.encode('utf-8'), (target_ip, target_port))
            self.get_logger().info(f'Sent UDP: {payload} to {target_ip}:{target_port}')
        except Exception as e:
            self.get_logger().error(f'UDP send failed: {e}')

    def motor_power(self, distance: float) -> float:
        if distance == 0:
            return 0.0

        distance = min(max(distance, self.MIN_POWER_DIST), self.MAX_POWER_DIST)
        return self.MIN_POWER + (
            (distance - self.MIN_POWER_DIST)
            / (self.MAX_POWER_DIST - self.MIN_POWER_DIST)
            * (1 - self.MIN_POWER)
        )

        

def main(args=None):
    rclpy.init(args=args)
    node = MotorInstructions()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()