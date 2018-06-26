import abc

class StateStore:
    __metaclass__=abc.ABCMeta

    ## Increment the version if the layout is changed
    ## State stores should check if the version matches during recovery
    crypto_material_state_layout_version = 1
    
    def __init__(self, state_store_location):
        self.state_store_location = state_store_location

    @abc.abstractmethod
    def load(self):
        pass
    
    @abc.abstractmethod
    def format(self):
        pass
    
    @abc.abstractmethod
    def get_crypto_material_state(self):
        pass
    
    @abc.abstractmethod
    def store_crypto_material_state(self, crypto_material_state):
        pass

class CryptoMaterialState:

    layout_version = 1
    
    def __init__(self):
        self._version = -1

    def set_version(self, version):
        self._version = version

    def get_version(self):
        return int(self._version)
