from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    motor_udp_address = LaunchConfiguration('motor_udp_address')
    nodes = [
        ('udp_image_publisher', 'udp_image_publisher'),
        ('yolo_processing', 'yolo_processing'),
        ('motor_instructions', 'motor_instructions'),
        ('speech_recognition', 'speech_recognition'),
        ('llm', 'llm'),
    ]

    launch_actions = [
        DeclareLaunchArgument(
            'motor_udp_address',
            default_value='172.20.10.2',
            description='IP address of the ESP32 haptic wristband',
        ),
    ]
    launch_actions.extend(
        Node(
            package='percepta_host',
            executable=executable,
            name=name,
            output='screen',
            parameters=(
                [{'udp_address': motor_udp_address}]
                if name == 'motor_instructions' else []
            ),
        )
        for executable, name in nodes
    )

    return LaunchDescription(launch_actions)
