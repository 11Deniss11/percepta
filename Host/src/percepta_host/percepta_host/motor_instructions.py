import rclpy
from std_msgs.msg import String
from rclpy.node import Node
import numpy as np
import socket

#    To use this method, publish coordinates to /motor_instructions_topic, and this node will receive them and print them to the console.

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

        # Create the subscriber
        # Arguments: (MessageType, 'topic_name', callback_function, qos_depth)
        self.subscription = self.create_subscription(
            String,
            #'/dummy_instructions',
            '/motor_instructions_topic',
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

        motor_nx, motor_px, motor_ny, motor_py = 0.0, 0.0, 0.0, 0.0

        #Direction pointing from hand to target in screenspace
        direction_vector2 = np.array([target_x - hand_x, target_y - hand_y])

        #X motor magnitude
        x_magnitude = min(max(abs(direction_vector2[0]), self.MIN_POWER_DIST), self.MAX_POWER_DIST)  # Clamp values
        x_magnitude = (x_magnitude - self.MIN_POWER) / (1 - self.MIN_POWER) + self.MIN_POWER  # Normalize to [0, 1]

        #Y motor magnitude
        y_magnitude = min(max(abs(direction_vector2[1]), self.MIN_POWER_DIST), self.MAX_POWER_DIST)  # Clamp values
        y_magnitude = (y_magnitude - self.MIN_POWER) / (1 - self.MIN_POWER) + self.MIN_POWER  # Normalize to [0, 1]

        # Set x_motor powers
        if direction_vector2[0] < 0:
            motor_nx = x_magnitude
        else:
            motor_px = x_magnitude

        # Set y_motor powers
        if direction_vector2[1] < 0:
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