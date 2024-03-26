from . import state_store

class NoneStateStore(state_store.StateStore):
    def __init__(self, state_store_location):
        super(NoneStateStore, self).__init__(state_store_location)
        
    def load(self):
        pass

    def format(self):
        pass
    
    def get_crypto_material_state(self):
        pass

    def store_crypto_material_state(self, crypto_material_state):
        pass
