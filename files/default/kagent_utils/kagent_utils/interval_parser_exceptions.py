class UnrecognizedIntervalException(Exception):
    def __init__(self, message):
        super(UnrecognizedIntervalException, self).__init__(message)
