import cv2
import io


def encode_image_as_jpeg(frame):
    # saving bandwidth, i.e. trading cpu vs network/storage
    _, buf = cv2.imencode(".jpeg", frame)
    buffer = io.BytesIO(buf)
    return buffer.getvalue()
