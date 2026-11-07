"""ChatterFeed emotion-to-marker mapping, shared by display and robot controls.

Tone (-100..+100) is still reported, but does not by itself select a color.
The eight physical marker numbers are fixed; the emotional dimensions in
the interpreter response determine which one to use.
"""

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Marker:
    number: int
    name: str
    hex_color: str
    emotion: str


MARKERS = (
    Marker(1, "Dark red", "#78212B", "Extreme hostility"),
    Marker(2, "Red", "#CE353F", "Anger/attack"),
    Marker(3, "Orange", "#E67B2C", "Heated conflict"),
    Marker(4, "Yellow", "#E5B83B", "Tension/uncertainty"),
    Marker(5, "Light green", "#A3CA63", "Neutral/reflection"),
    Marker(6, "Green", "#3FA868", "Warmth/support"),
    Marker(7, "Blue", "#3267C2", "Sadness/vulnerability"),
    Marker(8, "Cyan", "#40B9CB", "Hope/connection"),
)


def emotion_to_marker(interpretation: Mapping[str, float]) -> Marker:
    """Choose a physical marker from interpreted emotions, not the tone score.

    Hostility takes precedence when actual attacks/threats are present.
    Otherwise sadness or vulnerable disclosure is BLUE, not red, even
    though it may describe an unpleasant or painful experience.
    """
    def level(key: str) -> float:
        return max(0.0, min(1.0, float(interpretation.get(key, 0.0))))

    aggression = level("aggression")
    dehumanizing = level("dehumanizing")
    violence = level("violent_rhetoric")
    sadness = level("sadness")
    vulnerability = level("vulnerability")
    hope = level("hope")
    warmth = level("warmth")
    tension = level("tension")
    uncertainty = level("uncertainty")
    intensity = level("intensity")
    valence = max(-1.0, min(1.0, float(interpretation.get("valence", 0.0))))

    # Hostile conduct is different from describing personal suffering.
    if dehumanizing >= 0.60 or violence >= 0.60 or (
        aggression >= 0.85 and valence <= -0.55
    ):
        return MARKERS[0]  # Dark red: extreme hostility
    if dehumanizing >= 0.35 or violence >= 0.35 or aggression >= 0.65:
        return MARKERS[1]  # Red: direct attack, contempt or violent rhetoric

    # Sadness and vulnerability are positive/neutral in social tone, but
    # have their own emotional color. Hope wins only if clearly dominant.
    if sadness >= 0.55 or vulnerability >= 0.65:
        if hope >= 0.75 and hope > max(sadness, vulnerability) + 0.15:
            return MARKERS[7]  # Cyan: hope dominates a mixed emotion
        if aggression < 0.35:
            return MARKERS[6]  # Blue: grief, loneliness, vulnerable sharing

    if (aggression >= 0.30 and valence < -0.15) or (
        valence <= -0.45 and (tension >= 0.40 or intensity >= 0.55)
    ):
        return MARKERS[2]  # Orange: heated disagreement / agitation

    if hope >= 0.65 and hope >= warmth:
        return MARKERS[7]  # Cyan: hope, optimism, openness
    if warmth >= 0.55:
        return MARKERS[5]  # Green: compassion, care, friendliness
    if hope >= 0.65:
        return MARKERS[7]
    if tension >= 0.45 or uncertainty >= 0.60:
        return MARKERS[3]  # Yellow: unease or genuine uncertainty
    return MARKERS[4]  # Light green: neutral / reflective
