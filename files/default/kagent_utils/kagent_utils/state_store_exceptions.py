class StateLayoutVersionMismatchException(Exception):
    def __init__(self, message):
        super(StateLayoutVersionMismatchException, self).__init__(message)

class UnknownStateStoreException(Exception):
    def __init__(self, message):
        super(UnknownStateStoreException, self).__init__(message)

class StateNotLoadedException(Exception):
    def __init__(self, message):
        super(StateNotLoadedException, self).__init__(message)
