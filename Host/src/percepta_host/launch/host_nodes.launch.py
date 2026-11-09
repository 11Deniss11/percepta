from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    nodes = [
        ('udp_image_publisher', 'udp_image_publisher'),
        ('yolo_processing', 'yolo_processing'),
        ('motor_instructions', 'motor_instructions'),
        ('speech_recognition', 'speech_recognition'),
        ('llm', 'llm'),
    ]

    return LaunchDescription([
        Node(
            package='percepta_host',
            executable=executable,
            name=name,
            output='screen',
        )
        for executable, name in nodes
    ])
