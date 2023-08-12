from enum import Enum, auto


class DistanceMethod(Enum):
    TextPercentage = auto()
    ScopedPercentage = auto()
    ScopedCount = auto()


class SearchCategory(Enum):
    Law = 1
    History = 2
    Wisdom = 3
    Prophets = 4
    Gospels = 5
    Acts = 6
    Epistles = 7
    Apocalyptic = 8
