"""Built-in blues library.

Charts use the plain-text format understood by ``theory.parse_chart``.
Progressions are generic forms, not copyrighted melodies.
"""

from __future__ import annotations

BUILTIN_SONGS: list[dict] = [
    {
        "id": "basic-12-bar-blues",
        "title": "Basic 12-Bar Blues",
        "composer": "Traditional",
        "style": "shuffle",
        "key": "A",
        "tempo": 110,
        "chart": "A7 | A7 | A7 | A7 | D7 | D7 | A7 | A7 | E7 | D7 | A7 | E7",
    },
    {
        "id": "quick-change-blues",
        "title": "Quick-Change Blues",
        "composer": "Traditional",
        "style": "shuffle",
        "key": "E",
        "tempo": 120,
        "chart": "E7 | A7 | E7 | E7 | A7 | A7 | E7 | E7 | B7 | A7 | E7 | B7",
    },
    {
        "id": "jazz-blues",
        "title": "Jazz Blues",
        "composer": "Traditional",
        "style": "swing",
        "key": "F",
        "tempo": 140,
        "chart": "F7 | Bb7 | F7 | Cm7 F7 | Bb7 | Bdim7 | F7 | D7 | Gm7 | C7 | F7 D7 | Gm7 C7",
    },
    {
        "id": "bebop-blues",
        "title": "Bebop Blues",
        "composer": "Traditional",
        "style": "swing",
        "key": "Bb",
        "tempo": 180,
        "chart": "Bb7 | Eb7 | Bb7 | Fm7 Bb7 | Eb7 | Edim7 | Bb7 | Dm7 G7 | Cm7 | F7 | Bb7 G7 | Cm7 F7",
    },
    {
        "id": "bird-blues",
        "title": "Bird Blues",
        "composer": "Traditional (Parker changes)",
        "style": "swing",
        "key": "F",
        "tempo": 160,
        "chart": (
            "Fmaj7 | Em7b5 A7 | Dm7 G7 | Cm7 F7 | Bb7 | Bbm7 Eb7 | Am7 D7 | Abm7 Db7 | "
            "Gm7 | C7 | F7 D7 | Gm7 C7"
        ),
    },
    {
        "id": "minor-blues",
        "title": "Minor Blues",
        "composer": "Traditional",
        "style": "swing",
        "key": "C",
        "tempo": 130,
        "chart": "Cm7 | Cm7 | Cm7 | Cm7 | Fm7 | Fm7 | Cm7 | Cm7 | Ab7 | G7 | Cm7 | Dm7b5 G7",
    },
    {
        "id": "slow-blues",
        "title": "Slow Blues",
        "composer": "Traditional",
        "style": "slow",
        "key": "G",
        "tempo": 60,
        "chart": "G7 | C7 | G7 | G7 | C7 | C7 | G7 | E7 | Am7 | D7 | G7 C7 | G7 D7",
    },
    {
        "id": "eight-bar-blues",
        "title": "8-Bar Blues",
        "composer": "Traditional",
        "style": "shuffle",
        "key": "C",
        "tempo": 100,
        "chart": "C7 | G7 | F7 | F7 | C7 | G7 | C7 F7 | C7 G7",
    },
    {
        "id": "rock-blues",
        "title": "Straight-Eighth Blues",
        "composer": "Traditional",
        "style": "rock",
        "key": "E",
        "tempo": 128,
        "chart": "E7 | E7 | E7 | E7 | A7 | A7 | E7 | E7 | B7 | A7 | E7 | B7",
    },
    {
        "id": "funk-blues",
        "title": "Funky Ninth Blues",
        "composer": "Traditional",
        "style": "rock",
        "key": "G",
        "tempo": 100,
        "chart": "G9 | C9 | G9 | G9 | C9 | C9 | G9 | G9 | D9 | C9 | G9 | D9",
    },
]
