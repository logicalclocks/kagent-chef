import shutil
import os
import unittest
import tempfile

from kagent_utils import FileStateStore
from kagent_utils import CryptoMaterialState
from kagent_utils import StateLayoutVersionMismatchException
from kagent_utils import StateNotLoadedException

class TestFileStateStore(unittest.TestCase):

    def setUp(self):
        self.state_store_location = tempfile.mkdtemp(prefix='agent_state_store')
        self.state_store = FileStateStore(self.state_store_location)

    def tearDown(self):
        shutil.rmtree(self.state_store_location, ignore_errors=True)

    def test_creation_of_directory(self):
        self.assertTrue(os.path.isdir(self.state_store_location))

        # Check that directory is not recreated
        mtime_before = os.stat(self.state_store_location).st_mtime
        state_store = FileStateStore(self.state_store_location)
        mtime_after = os.stat(self.state_store_location).st_mtime
        self.assertEqual(mtime_before, mtime_after)
        
    def test_restore_crypto_material_state(self):
        self.state_store.load()

        # Initially it should be empty
        crypto_material_state = self.state_store.get_crypto_material_state()
        self.assertEqual(-1, crypto_material_state.get_version())

        # Store new state
        crypto_material_state = CryptoMaterialState()
        crypto_material_state.set_version(2)
        self.state_store.store_crypto_material_state(crypto_material_state)

        # Check the serialized file exists
        crypto_material_state_file = os.path.join(self.state_store_location,
                                                  FileStateStore._CRYPTO_MATERIAL_STATE_FILE)
        self.assertTrue(os.path.isfile(crypto_material_state_file))

        # Create new state store
        state_store = FileStateStore(self.state_store_location)
        state_store.load()
        crypto_material_state = state_store.get_crypto_material_state()
        self.assertEqual(2, crypto_material_state.get_version())

    def test_restore_crypto_material_state_with_wrong_layout(self):
        self.state_store.load()
        crypto_material_state = CryptoMaterialState()
        crypto_material_state.layout_version = 2
        self.state_store.store_crypto_material_state(crypto_material_state)

        state_store = FileStateStore(self.state_store_location)
        with self.assertRaises(StateLayoutVersionMismatchException) as ex:
            state_store.load()

    def test_state_not_loaded(self):
        with self.assertRaises(StateNotLoadedException) as ex:
            self.state_store.get_crypto_material_state()

    def test_format(self):
        self.state_store.load()
        self.assertTrue(os.path.isdir(self.state_store_location))

        self.state_store.format()
        self.assertFalse(os.path.isdir(self.state_store_location))
