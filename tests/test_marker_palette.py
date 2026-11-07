"""Checks for ChatterFeed's emotion-based marker selection.

Run from the repository root:
    python -m unittest discover -s tests
"""

import unittest

from marker_palette import MARKERS, emotion_to_marker


class MarkerPaletteTests(unittest.TestCase):
    def test_all_eight_marker_slots_have_distinct_colors(self):
        self.assertEqual([m.number for m in MARKERS], list(range(1, 9)))
        self.assertEqual(len({m.hex_color for m in MARKERS}), 8)

    def test_each_emotional_category(self):
        scenarios = [
            ({"valence": -0.95, "aggression": 0.95, "dehumanizing": 0.8}, 1),
            ({"valence": -0.55, "aggression": 0.75}, 2),
            ({"valence": -0.40, "aggression": 0.45}, 3),
            ({"valence": 0.0, "uncertainty": 0.85, "tension": 0.6}, 4),
            ({"valence": 0.0, "intensity": 0.1}, 5),
            ({"valence": 0.70, "warmth": 0.8}, 6),
            ({"valence": 0.25, "sadness": 0.9, "vulnerability": 0.8}, 7),
            ({"valence": 0.75, "hope": 0.9, "warmth": 0.65}, 8),
        ]
        for scores, marker_number in scenarios:
            with self.subTest(marker=marker_number):
                self.assertEqual(emotion_to_marker(scores).number, marker_number)

    def test_sadness_is_blue_even_if_tone_is_incorrectly_negative(self):
        scores = {
            "valence": -0.70,
            "sadness": 0.9,
            "vulnerability": 0.8,
            "aggression": 0.0,
            "intensity": 0.9,
            "tension": 0.6,
        }
        self.assertEqual(emotion_to_marker(scores).name, "Blue")

    def test_vulnerability_without_sadness_is_blue(self):
        self.assertEqual(emotion_to_marker({"vulnerability": 0.8}).number, 7)

    def test_clear_threat_overrides_sadness(self):
        scores = {"sadness": 0.9, "aggression": 0.85, "violent_rhetoric": 0.8}
        self.assertEqual(emotion_to_marker(scores).number, 1)

    def test_hope_wins_if_clearly_more_dominant_than_sadness(self):
        scores = {"sadness": 0.60, "vulnerability": 0.65, "hope": 0.9}
        self.assertEqual(emotion_to_marker(scores).number, 8)


if __name__ == "__main__":
    unittest.main()
