import os
import struct
import time
from abc import ABC, abstractmethod
from threading import Thread, Lock

from palleon import SimpleSocket


class InputPlugin(ABC):
    def __init__(self):
        self._current_image = None
        self._current_image_lock = Lock()
        self._current_image_already_sent = False
        self._current_image_already_sent_lock = Lock()

        self._host = os.environ["PALLEON_HOST"]
        self._port = int(os.environ["PALLEON_PORT"])

    def update_image(self, encoded_image):
        with self._current_image_lock:
            self._current_image = encoded_image
            with self._current_image_already_sent_lock:
                self._current_image_already_sent = False

    def get_image(self):
        with self._current_image_lock:
            return self._current_image

    @abstractmethod
    def update_thread(self):
        pass

    @abstractmethod
    def settings_hook(self, key, value, value_type):
        pass

    def connection_thread(self):
        with SimpleSocket(self._host, self._port) as s:
            while True:
                instruction = s.recv_exactly(1)

                match instruction:
                    case b"s":
                        # mvp of a method the input plugin could receive settings from the core
                        length_key, length_value, value_type = struct.unpack("<iii", s.recv_exactly(3 * 4))
                        key_and_value = s.recv_exactly(length_key + length_value)
                        key = key_and_value[:length_key]
                        value = key_and_value[length_key: length_key + length_value]
                        self.settings_hook(key, value, value_type)
                    case b"i":
                        # the server requested an image
                        # it was a deliberate decision so the server could decide when to handle new input
                        # because otherwise it could lead to a DOS like situation
                        with self._current_image_already_sent_lock:
                            if self._current_image_already_sent:
                                # no new image was loaded
                                s.sendall(struct.pack("<i", 2))
                            else:
                                with self._current_image_lock:
                                    if self._current_image:
                                        data = struct.pack("<ii", 1, len(self._current_image)) + self._current_image
                                        s.sendall(data)
                                        self._current_image_already_sent = True
                                    else:
                                        # no data atm
                                        # in principle the same as 2 (nop) but it implies "it could take
                                        # longer, so please wait some time before further requests"
                                        s.sendall(struct.pack("<i", 0))

    def run(self):
        collector = Thread(target=self.update_thread)
        collector.daemon = True
        collector.start()

        connector = Thread(target=self.connection_thread)
        connector.daemon = True
        connector.start()

        while True:
            time.sleep(1)
