import io

from picamera2 import Picamera2


def open_camera(config):
    # Configure the camera once so every frame uses the same resolution.
    camera = Picamera2()
    camera.configure(
        camera.create_video_configuration(
            main={
                "size": (config.jpeg_width, config.jpeg_height),
                "format": "RGB888",
            }
        )
    )
    camera.start()
    return camera


def capture_frame(camera):
    # Return one complete JPEG; the UDP code sends it in smaller packets.
    output = io.BytesIO()
    camera.capture_file(output, format="jpeg")
    return output.getvalue()


def close_camera(camera):
    camera.stop()
    camera.close()
