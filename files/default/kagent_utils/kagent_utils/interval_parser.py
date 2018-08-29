import re

from interval_parser_exceptions import UnrecognizedIntervalException

"""
Utility class to parse human readable time units such as 3h or 2m
"""
class IntervalParser:
    def __init__(self):
        self._TIME_UNITS = {
            'ms': 1,
            's': 1000,
            'm': 60000,
            'h': 3600000,
            'd': 86400000
        }
        self._REGEX = re.compile('([0-9]+)([a-z]+)?')

    def get_interval_in_ms(self, value):
        """
        Get a time value in milliseconds

        Parameters
        ----------
        value: Human readable time

        Returns
        -------
        Time in milliseconds
        """
        
        match = self._REGEX.match(value)
        if not match:
            raise UnrecognizedIntervalException("Could not parse interal value: {0}".format(value))

        time_value = match.group(1)
        time_unit = match.group(2)
        if not time_unit:
            time_unit = 'm'
        else:
            time_unit = time_unit.lower()

        if time_unit not in self._TIME_UNITS:
            raise UnrecognizedIntervalException("Unknown time unit: {0}".format(time_unit))

        multiplier = self._TIME_UNITS[time_unit]
        return int(time_value) * multiplier
            

    def get_interval_in_s(self, value):
        """
        Get a time value in seconds

        Parameters
        ----------
        value: Human readable time

        Returns
        -------
        Time in seconds
        """
        
        return self.get_interval_in_ms(value) / 1000
