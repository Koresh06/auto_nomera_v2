class _AutoId:
    def __init__(self) -> None:
        self._n = 1

    def next(self) -> int:
        n = self._n
        self._n += 1
        return n
