from file_state_store import FileStateStore
from none_state_store import NoneStateStore

from state_store_exceptions import UnknownStateStoreException
    
class StateStoreFactory:

    def __init__(self, state_store_location):
        self._instance = None
        self._state_store_location = state_store_location
    
    def get_instance(self, type):
        if (self._instance is not None):
            return self._instance
        type_upper = type.upper()
        if (type_upper == "FILE"):
            self._instance = FileStateStore(self._state_store_location)
        elif (type_upper == "NONE"):
            self._instance = NoneStateStore(self._state_store_location)
        else:
            error_msg = "Unknown state store: {0}".format(type)
            raise UnknownStateStoreException(error_msg)
        return self._instance
