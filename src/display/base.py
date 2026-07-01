import abc

class BaseDisplay(abc.ABC):
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