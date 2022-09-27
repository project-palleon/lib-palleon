import os
from abc import ABC, abstractmethod
from io import BytesIO

from PIL import Image

from palleon import SimpleSocket
from .dependency import Dependency


class DataPlugin(ABC):
    def __init__(self, dependencies: list[Dependency] = None, image=True):
        self._dependencies = dependencies if dependencies else []
        self._image = image

        self._host = os.environ["PALLEON_HOST"]
        self._port = int(os.environ["PALLEON_PORT"])

        self._socket = None

    def run(self):
        self._socket = SimpleSocket(self._host, self._port)
        self._socket.connect()

        # send dependencies
        self._socket.send_bson({"dependencies": {d.name: d.value for d in self._dependencies}, "image": self._image})

        self.loop()

    @abstractmethod
    def image_received_hook(self, data, image, input_source, other_metadata):
        return {}

    def loop(self):
        while True:
            # received data from other plugins
            data = self._socket.recv_bson()
            # receive image

            img_wrapper = self._socket.recv_bson()

            img_pil = Image.open(BytesIO(img_wrapper["data"])) if self._image else None
            img_input_source = img_wrapper["input_source"]
            img_other_metadata = {
                "timestamp": img_wrapper["timestamp"],
            }

            # call the handler to get the desired output
            result = self.image_received_hook(data, img_pil, img_input_source, img_other_metadata)

            # send new data
            self._socket.send_bson(result)
