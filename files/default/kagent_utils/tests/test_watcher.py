import unittest
import time

from kagent_utils import WatcherAction
from kagent_utils import Watcher

class MockWatcherAction(WatcherAction):
    def __init__(self):
        self.pre_action_flag = False
        self.action_flag = False
        self.post_action_flag = False

    def preAction(self, *args, **kwargs):
        self.pre_action_flag = True

    def action(self, *args, **kwargs):
        self.action_flag = True

    def postAction(self, *args, **kwargs):
        self.post_action_flag = True

class MockFailingWatcherAction(WatcherAction):
    def preAction(self, *args, **kwargs):
        pass
    
    def action(self, *args, **kwargs):
        pass

    def postAction(self, *args, **kwargs):
        raise Exception("Oops :(")

class MockFailOnceWatcherAction(WatcherAction):
    def __init__(self):
        self.should_I_fail = True

    def preAction(self, *args, **kwargs):
        pass

    def action(self, *args, **kwargs):
        if self.should_I_fail:
            self.should_I_fail = False
            raise Exception("It won't happen again, I promise")
        pass

    def postAction(self, *args, **kwargs):
        pass
    
class TestWatcher(unittest.TestCase):

    def test_calling_all_callbacks(self):
        action = MockWatcherAction()
        self.assertFalse(action.pre_action_flag)
        self.assertFalse(action.action_flag)
        self.assertFalse(action.post_action_flag)
        
        watcher = Watcher(action, 2)
        watcher.start()
        time.sleep(1)

        self.assertTrue(action.pre_action_flag)
        self.assertTrue(action.action_flag)
        self.assertTrue(action.post_action_flag)
        watcher.stop()
        time.sleep(2)

        self.assertFalse(watcher.is_alive())

    def test_watcher_exits_after_failures(self):
        action = MockFailingWatcherAction()
        watcher = Watcher(action, 2)
        watcher.start()

        time.sleep(6)

        self.assertFalse(watcher.is_alive())
        self.assertEqual(6, watcher.failures)

    def test_recover_after_failure(self):
        action = MockFailOnceWatcherAction()
        self.assertTrue(action.should_I_fail)
        watcher = Watcher(action, 2)
        watcher.start()

        time.sleep(2)

        self.assertEqual(0, watcher.failures)
        self.assertTrue(watcher.is_alive())
        watcher.stop()
        time.sleep(3)
        self.assertFalse(watcher.is_alive())
