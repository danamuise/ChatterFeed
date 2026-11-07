"""Single source of truth for ChatterFeed's eight score-to-marker colors.

The same mapping can later control the physical marker carousel. Color
selection is deterministic and local; no additional AI request is needed.

AI valence: -1.0 .. +1.0
Displayed score: -100 .. +100
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Marker:
    number: int
    name: str
    hex_color: str


MARKERS = (
    Marker(1, "Dark red", "#78212B"),    # -100 to -76
    Marker(2, "Red", "#CE353F"),         #  -75 to -51
    Marker(3, "Orange", "#E67B2C"),      #  -50 to -26
    Marker(4, "Yellow", "#E5B83B"),      #  -25 to  -1
    Marker(5, "Light green", "#A3CA63"), #    0 to +24
    Marker(6, "Green", "#3FA868"),       #  +25 to +49
    Marker(7, "Cyan", "#40B9CB"),        #  +50 to +74
    Marker(8, "Blue", "#3267C2"),        #  +75 to +100
)


def score_to_marker(score: int | float) -> Marker:
    """Select one of eight physical markers from the displayed tone score."""
    clamped = max(-100, min(100, round(score)))
    return MARKERS[min(7, (clamped + 100) // 25)]
