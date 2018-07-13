import os
import pickle
import shutil

from threading import Lock

import state_store
from state_store import CryptoMaterialState
from state_store_exceptions import StateLayoutVersionMismatchException
from state_store_exceptions import StateNotLoadedException

class FileStateStore(state_store.StateStore):

    _CRYPTO_MATERIAL_STATE_FILE = "crypto_material_state.pkl"
    
    def __init__(self, state_store_location):
        state_store.StateStore.__init__(self, state_store_location)
        if (not os.path.isdir(self.state_store_location)):
            os.makedirs(self.state_store_location)
        self.state_lock = Lock()
        self.crypto_material_state_file = os.path.join(self.state_store_location, self._CRYPTO_MATERIAL_STATE_FILE)
        self.crypto_material_state = None

    def load(self):
        try:
            self.state_lock.acquire()
            self._load_crypto_material_state()
        finally:
            self.state_lock.release()

    def format(self):
        shutil.rmtree(self.state_store_location)
        
    def get_crypto_material_state(self):
        try:
            self.state_lock.acquire()
            if (self.crypto_material_state is not None):
                return self.crypto_material_state

            raise StateNotLoadedException("CryptoMaterialState was not loaded!!!")
        finally:
            self.state_lock.release()

    def store_crypto_material_state(self, crypto_material_state):
        try:
            self.state_lock.acquire()
            with open(self.crypto_material_state_file, 'wb') as fd:
                pickle.dump(crypto_material_state, fd, 2)
            self._fix_permission(self.crypto_material_state_file)
        finally:
            self.state_lock.release()

    # csr.py is run as user root so we need to fix the permission
    # and set the file owner to the user running kagent
    def _fix_permission(self, file):
        self._chmod(file)
        self._chown(file)
        
    def _chmod(self, file):
        os.chmod(file, 0700)

    def _chown(self, file):
        # Get UID and GID of state store directory, it should be the user running kagent
        ss_stat = os.stat(self.state_store_location)
        uid = ss_stat.st_uid
        gid = ss_stat.st_gid
        os.chown(file, uid, gid)
            
    def _load_crypto_material_state(self):
        if (os.path.isfile(self.crypto_material_state_file)):
            # Deserialize it
            with open(self.crypto_material_state_file, 'rb') as fd:
                self.crypto_material_state = pickle.load(fd)
            if (state_store.StateStore.crypto_material_state_layout_version != self.crypto_material_state.layout_version):
                raise StateLayoutVersionMismatchException(
                    "CryptoMaterialState recovered layout version is {} while the current is {}"
                    .format(self.crypto_material_state.layout_version,
                            state_store.StateStore.crypto_material_state_layout_version))
        else:
            self.crypto_material_state = CryptoMaterialState()

    
