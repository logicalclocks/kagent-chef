import unittest

from kagent_utils import CondaEnvsWatcherAction
from kagent_utils import KConfig
from kagent_utils import ConcurrentCircularLinkedList

class MockCondaEnvsWatcherAction(CondaEnvsWatcherAction):
    def __init__(self, monitor_list):
        config = KConfig("some_path")
        config.conda_dir = "/some/path/anaconda-2-5.2.0"
        config.conda_python_versions = "2.7, 3.6"
        CondaEnvsWatcherAction.__init__(self, monitor_list, config)

    def _get_conda_envs(self):
        return "{\
        \"envs\": [\
        \"/srv/hops/anaconda/anaconda-2-5.2.0\",\
        \"/srv/hops/anaconda/anaconda-2-5.2.0/envs/anaconda\",\
        \"/srv/hops/anaconda/anaconda-2-5.2.0/envs/lala\",\
        \"/srv/hops/anaconda/anaconda-2-5.2.0/envs/project_06c88519\"\
        ]\
        }"
    
class TestCondaEnvsWatcherAction(unittest.TestCase):

    def setUp(self):
        self.list = ConcurrentCircularLinkedList()

    def test_envs_in_list(self):
        self.assertEquals(0, self.list.list_size())
        action = MockCondaEnvsWatcherAction(self.list)
        action.action()
        self.assertEquals(2, self.list.list_size())
        # These are blacklisted environments
        self.assertFalse(self.list.contains("anaconda-2-5.2.0"))
        self.assertFalse(self.list.contains("anaconda"))
        self.assertTrue(self.list.contains("lala"))
        self.assertTrue(self.list.contains("project_06c88519"))
