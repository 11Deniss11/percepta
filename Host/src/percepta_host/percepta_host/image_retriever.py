import socket
import struct
import time

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import Image


MAGIC = b'PJPG'
# Version 2 uses a uint32 JPEG-size field; version 1 used uint16.
PROTOCOL_VERSION = 2
# magic, version, frame number, chunk number, chunk count, JPEG size, timestamp
HEADER = struct.Struct('!4sBIIHIQ')
MAX_FRAME_SIZE = 64 * 1024 * 1024
FRAME_TIMEOUT = 1.0
FRAME_POLL_INTERVAL = 1.0 / 120.0


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
        self.frames = {}
        self.received_frames = 0
        self.published_frames = 0
        self.last_report = time.monotonic()

        self.bridge = CvBridge()
        qos = QoSProfile(
            depth=1,
            history=QoSHistoryPolicy.KEEP_LAST,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
        )
        self.publisher = self.create_publisher(Image, topic, qos)

        self.timer = self.create_timer(FRAME_POLL_INTERVAL, self.receive_frame)

        self.get_logger().info(
            f'Receiving JPEG frames on udp://{address}:{port}, '
            f'publishing to {topic}'
        )

    def _reassemble_packet(self, packet):
        if len(packet) < HEADER.size:
            self.get_logger().debug('Ignoring UDP packet shorter than its header')
            return None

        magic, version, frame_number, chunk_number, chunk_count, jpeg_size, _ = (
            HEADER.unpack_from(packet)
        )
        if magic != MAGIC or version != PROTOCOL_VERSION:
            self.get_logger().debug('Ignoring UDP packet with an unknown header')
            return None
        if (
            chunk_count == 0
            or chunk_number >= chunk_count
            or jpeg_size == 0
            or jpeg_size > MAX_FRAME_SIZE
        ):
            self.get_logger().debug('Ignoring UDP packet with invalid frame metadata')
            return None

        chunk = packet[HEADER.size:]
        frame = self.frames.get(frame_number)
        if frame is None or (
            frame['chunk_count'] != chunk_count or frame['jpeg_size'] != jpeg_size
        ):
            frame = {
                'chunk_count': chunk_count,
                'jpeg_size': jpeg_size,
                'chunks': {},
                'received': 0,
                'last_seen': time.monotonic(),
            }
            self.frames[frame_number] = frame

        frame['last_seen'] = time.monotonic()
        if chunk_number not in frame['chunks']:
            frame['chunks'][chunk_number] = chunk
            frame['received'] += len(chunk)

        if len(frame['chunks']) != chunk_count:
            return None
        if frame['received'] != jpeg_size:
            self.frames.pop(frame_number, None)
            self.get_logger().debug('Ignoring frame with an invalid JPEG size')
            return None

        jpeg = b''.join(frame['chunks'][index] for index in range(chunk_count))
        self.frames.pop(frame_number, None)
        return jpeg

    def _remove_expired_frames(self):
        cutoff = time.monotonic() - FRAME_TIMEOUT
        expired = [
            frame_number
            for frame_number, frame in self.frames.items()
            if frame['last_seen'] < cutoff
        ]
        for frame_number in expired:
            self.frames.pop(frame_number, None)

    def receive_frame(self):
        try:
            # Drain queued packets so a slow ROS callback does not build a backlog.
            newest_jpeg = None
            while True:
                try:
                    packet, _ = self.socket.recvfrom(65535)
                except BlockingIOError:
                    break
                if len(packet) >= HEADER.size:
                    frame_number = HEADER.unpack_from(packet)[2]
                    chunk_number = HEADER.unpack_from(packet)[3]
                    self.get_logger().info(
                        f'Received UDP packet for frame {frame_number}, '
                        f'chunk {chunk_number}'
                    )
                jpeg = self._reassemble_packet(packet)
                if jpeg is not None:
                    self.received_frames += 1
                    newest_jpeg = jpeg

            self._remove_expired_frames()
            now = time.monotonic()
            if now - self.last_report >= 10:
                self.get_logger().info(
                    f'Received {self.received_frames} complete frames, '
                    f'published {self.published_frames} in the last 10 seconds'
                )
                self.received_frames = 0
                self.published_frames = 0
                self.last_report = now
            if newest_jpeg is None:
                return

            encoded = np.frombuffer(newest_jpeg, dtype=np.uint8)
            frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

            if frame is None:
                self.get_logger().warning('Invalid reassembled JPEG frame')
                return

            message = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            message.header.stamp = self.get_clock().now().to_msg()
            message.header.frame_id = self.frame_id

            self.publisher.publish(message)
            self.published_frames += 1
            self.get_logger().debug('Published frame')

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
