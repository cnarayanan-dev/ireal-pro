"""Music theory helpers: note names, chord parsing and transposition."""

from __future__ import annotations

import re
from dataclasses import dataclass

SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# Keys that are conventionally spelled with flats.
FLAT_KEYS = {"F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"}

# Keys offered in the UI, in the usual iReal order.
KEYS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

_LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Interval sets (semitones above the root) for each chord quality.
# Several spellings map to the same structure so charts can be typed loosely.
QUALITIES: dict[str, tuple[int, ...]] = {
    "": (0, 4, 7),
    "maj": (0, 4, 7),
    "M": (0, 4, 7),
    "5": (0, 7),
    "6": (0, 4, 7, 9),
    "69": (0, 4, 7, 9, 14),
    "add9": (0, 4, 7, 14),
    "maj7": (0, 4, 7, 11),
    "M7": (0, 4, 7, 11),
    "^7": (0, 4, 7, 11),
    "^": (0, 4, 7, 11),
    "maj9": (0, 4, 7, 11, 14),
    "^9": (0, 4, 7, 11, 14),
    "7": (0, 4, 7, 10),
    "9": (0, 4, 7, 10, 14),
    "11": (0, 7, 10, 14, 17),
    "13": (0, 4, 7, 10, 14, 21),
    "7b9": (0, 4, 7, 10, 13),
    "7#9": (0, 4, 7, 10, 15),
    "7#11": (0, 4, 7, 10, 18),
    "7b13": (0, 4, 7, 10, 20),
    "7alt": (0, 4, 10, 13, 15, 20),
    "7#5": (0, 4, 8, 10),
    "+7": (0, 4, 8, 10),
    "aug7": (0, 4, 8, 10),
    "7sus4": (0, 5, 7, 10),
    "7sus": (0, 5, 7, 10),
    "9sus4": (0, 5, 7, 10, 14),
    "sus4": (0, 5, 7),
    "sus": (0, 5, 7),
    "sus2": (0, 2, 7),
    "m": (0, 3, 7),
    "-": (0, 3, 7),
    "min": (0, 3, 7),
    "m6": (0, 3, 7, 9),
    "-6": (0, 3, 7, 9),
    "m7": (0, 3, 7, 10),
    "-7": (0, 3, 7, 10),
    "min7": (0, 3, 7, 10),
    "m9": (0, 3, 7, 10, 14),
    "-9": (0, 3, 7, 10, 14),
    "m11": (0, 3, 7, 10, 14, 17),
    "-11": (0, 3, 7, 10, 14, 17),
    "mmaj7": (0, 3, 7, 11),
    "m^7": (0, 3, 7, 11),
    "-^7": (0, 3, 7, 11),
    "m7b5": (0, 3, 6, 10),
    "-7b5": (0, 3, 6, 10),
    "h7": (0, 3, 6, 10),
    "h": (0, 3, 6, 10),
    "ø": (0, 3, 6, 10),
    "ø7": (0, 3, 6, 10),
    "dim": (0, 3, 6),
    "o": (0, 3, 6),
    "dim7": (0, 3, 6, 9),
    "o7": (0, 3, 6, 9),
    "aug": (0, 4, 8),
    "+": (0, 4, 8),
}

_CHORD_RE = re.compile(r"^([A-G])([#b]?)(.*?)(?:/([A-G])([#b]?))?$")

NO_CHORD = "N.C."


class ChordError(ValueError):
    """Raised when a chord symbol cannot be parsed."""


def pitch_class(letter: str, accidental: str = "") -> int:
    pc = _LETTER_PC[letter]
    if accidental == "#":
        pc += 1
    elif accidental == "b":
        pc -= 1
    return pc % 12


def parse_note(name: str) -> int:
    """Parse a note name like 'Bb' or 'F#' into a pitch class."""
    m = re.fullmatch(r"([A-G])([#b]?)", name.strip())
    if not m:
        raise ChordError(f"Invalid note name: {name!r}")
    return pitch_class(m.group(1), m.group(2))


def note_name(pc: int, prefer_flats: bool) -> str:
    return (FLAT_NAMES if prefer_flats else SHARP_NAMES)[pc % 12]


def key_prefers_flats(key: str) -> bool:
    root = key.rstrip("m-")
    return root in FLAT_KEYS


@dataclass(frozen=True)
class Chord:
    root: int
    quality: str
    bass: int | None = None

    @property
    def intervals(self) -> tuple[int, ...]:
        return QUALITIES[self.quality]

    @property
    def pitch_classes(self) -> list[int]:
        return [(self.root + i) % 12 for i in self.intervals]

    def tone(self, kind: str) -> int | None:
        """Return the interval for 'third', 'fifth' or 'seventh' if present."""
        wanted = {"third": (3, 4, 5, 2), "fifth": (7, 6, 8), "seventh": (10, 11, 9)}[kind]
        for candidate in wanted:
            if candidate in self.intervals:
                # A 6th only counts as the seventh for diminished-seventh chords.
                if kind == "seventh" and candidate == 9 and self.quality not in ("dim7", "o7"):
                    continue
                return candidate
        return None

    @property
    def is_minor(self) -> bool:
        return 3 in self.intervals and 4 not in self.intervals

    @property
    def is_dominant(self) -> bool:
        return 4 in self.intervals and 10 in self.intervals

    def symbol(self, prefer_flats: bool) -> str:
        text = note_name(self.root, prefer_flats) + self.quality
        if self.bass is not None:
            text += "/" + note_name(self.bass, prefer_flats)
        return text


def parse_chord(symbol: str) -> Chord:
    m = _CHORD_RE.match(symbol.strip())
    if not m:
        raise ChordError(f"Invalid chord symbol: {symbol!r}")
    letter, acc, quality, bass_letter, bass_acc = m.groups()
    if quality not in QUALITIES:
        raise ChordError(f"Unknown chord quality {quality!r} in {symbol!r}")
    bass = pitch_class(bass_letter, bass_acc) if bass_letter else None
    return Chord(pitch_class(letter, acc), quality, bass)


def transpose_symbol(symbol: str, semitones: int, prefer_flats: bool) -> str:
    if symbol == NO_CHORD:
        return symbol
    chord = parse_chord(symbol)
    moved = Chord(
        (chord.root + semitones) % 12,
        chord.quality,
        None if chord.bass is None else (chord.bass + semitones) % 12,
    )
    return moved.symbol(prefer_flats)


def interval_between_keys(src: str, dst: str) -> int:
    return (parse_note(dst.rstrip("m-")) - parse_note(src.rstrip("m-"))) % 12


def parse_chart(chart: str) -> list[list[str]]:
    """Parse a chart like 'C7 | F7 | C7 | % | F7 Fdim7 | ...' into bars.

    Bars are separated by '|'. Chords inside a bar are separated by spaces and
    split the bar evenly. '%' repeats the previous bar. Every chord symbol is
    validated so bad input fails early.
    """
    bars: list[list[str]] = []
    for raw in chart.replace("\n", "|").split("|"):
        tokens = raw.split()
        if not tokens:
            continue
        if tokens == ["%"]:
            if not bars:
                raise ChordError("'%' cannot be the first bar")
            bars.append(list(bars[-1]))
            continue
        if len(tokens) > 4:
            raise ChordError(f"At most 4 chords per bar, got {raw.strip()!r}")
        for token in tokens:
            if token != NO_CHORD:
                parse_chord(token)
        bars.append(tokens)
    if not bars:
        raise ChordError("Chart has no bars")
    return bars


def format_chart(bars: list[list[str]]) -> str:
    return " | ".join(" ".join(bar) for bar in bars)


def transpose_bars(bars: list[list[str]], semitones: int, prefer_flats: bool) -> list[list[str]]:
    return [[transpose_symbol(c, semitones, prefer_flats) for c in bar] for bar in bars]


def beat_split(count: int, beats_per_bar: int = 4) -> list[int]:
    """How many beats each chord in a bar gets."""
    if count == 1:
        return [beats_per_bar]
    if count == 2:
        return [beats_per_bar // 2, beats_per_bar - beats_per_bar // 2]
    if count == 3:
        return [2, 1, 1]
    return [1] * count
