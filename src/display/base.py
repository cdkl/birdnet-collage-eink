import abc

class BaseDisplay(abc.ABC):
    def __init__(self):
        self.last_quantized_bytes = None

    @property
    @abc.abstractmethod
    def resolution(self):
        pass

    @abc.abstractmethod
    def show(self, png_bytes):
        pass

    @abc.abstractmethod
    def clear(self):
        pass