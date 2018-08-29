import abc

"""
Abstract class to be implemented by different actions passed to Watcher thread
"""
class WatcherAction:
    __metaclass__=abc.ABCMeta

    @abc.abstractmethod
    def preAction(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def action(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def postAction(self, *args, **kwargs):
        pass
