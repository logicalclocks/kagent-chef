import threading
import time
import logging

"""
A watcher thread to perform WatcherAction periodically
"""
class Watcher(threading.Thread):
    def __init__(self, action, watcher_interval, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        """
        Constructor of the Watcher thread

        Parameters
        ----------
        action: Instance of WatcherAction with actions to be performed
        watcher_interval: Interval in seconds
        """
        
        threading.Thread.__init__(self, group=group, target=target, name=name, verbose=verbose)
        self.action = action
        self.watcher_interval = watcher_interval
        self._stop_flag = threading.Event()
        self.failures = 0
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        while (not self._stop_flag.is_set()):
            try:
                self.logger.debug("Watcher calling preAction")
                self.action.preAction()
                self.logger.debug("Watcher calling action")
                self.action.action()
                self.logger.debug("Watcher calling postAction")
                self.action.postAction()
                self.failures = 0
                self.logger.debug("Watcher called all callbacks")
                time.sleep(self.watcher_interval)
            except Exception as e:
                self.logger.warning("Exception in Watcher, retrying... {0}".format(e))
                self.failures += 1
                if self.failures > 5:
                    self.logger.critical("Fatal error in Watcher thread, exiting... {0}".format(e))
                    self.stop()
                else:
                    time.sleep(1)

    def stop(self):
        """
        Stop the current Watcher thread
        """
        
        self._stop_flag.set()

    def stopped(self):
        """
        Check if the current Watcher thread is stopped
        
        Returns
        -------
        True if it is stopped, otherwise False
        """
        return self._stop_flag.is_set()

            
