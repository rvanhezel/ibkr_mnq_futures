import pandas as pd
from src.utilities.utils import split_tenor_string


class Period:

    def __init__(self, tenor_str: str):
        units, tenor = split_tenor_string(tenor_str)
        self.units: int = units
        self.tenor: str = self._check_frequency(tenor)

    def _check_frequency(self, tenor: str):
        if tenor == "m":
            raise ValueError("Superfluous 'm' tenor. Use min for minutes or M for month.")
        elif tenor not in ("min", "b", "d", "W", "M", "Q", "SA", "Y", "D", "B"):
            raise ValueError("tenor not recognized")
        
        return tenor

    def __str__(self):
        return str(self.units) + self.tenor
