import unittest
import tempfile
import shutil

from kagent_utils import StateStoreFactory
from kagent_utils import FileStateStore
from kagent_utils import NoneStateStore
from kagent_utils import UnknownStateStoreException

class TestStateStoreFactory(unittest.TestCase):

    def setUp(self):
        self.state_store_location = tempfile.mkdtemp(prefix='agent_state_store')
        self.factory = StateStoreFactory(self.state_store_location)

    def tearDown(self):
        shutil.rmtree(self.state_store_location, ignore_errors=True)
        
    def test_file_state_store(self):
        state_store = self.factory.get_instance('file')
        self.assertIsNotNone(state_store)
        self.assertIsInstance(state_store, FileStateStore)

    def test_none_state_store(self):
        state_store = self.factory.get_instance('none')
        self.assertIsNotNone(state_store)
        self.assertIsInstance(state_store, NoneStateStore)

    def test_unknown_state_store(self):
        with self.assertRaises(UnknownStateStoreException) as ex:
            state_store = self.factory.get_instance('invalid')

        exception = ex.exception
        self.assertEqual('Unknown state store: invalid', str(exception))
        
