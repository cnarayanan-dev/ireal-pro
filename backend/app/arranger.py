"""Generate a backing-track arrangement (bass, piano, drums) from a chord chart.

The output is a flat list of note events measured in beats. The frontend
schedules them with the Web Audio API, so tempo stays a client-side concern
and can change live while a loop is playing.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .theory import NO_CHORD, Chord, beat_split, parse_chord

BEATS_PER_BAR = 4

# General MIDI drum numbers.
KICK, SIDESTICK, SNARE, HAT, PEDAL_HAT, CRASH, RIDE = 36, 37, 38, 42, 44, 49, 51

STYLES = {
    "swing": {"name": "Jazz Swing", "swing": 2 / 3, "description": "Walking bass, comping piano, ride cymbal"},
    "shuffle": {"name": "Blues Shuffle", "swing": 2 / 3, "description": "Boogie bass line with a shuffle groove"},
    "slow": {"name": "Slow Blues 12/8", "swing": 2 / 3, "description": "Triplet feel for slow tempos"},
    "rock": {"name": "Straight Blues Rock", "swing": 0.5, "description": "Straight eighths, driving bass"},
}

BASS_LOW, BASS_HIGH = 28, 50  # E1 .. D3
PIANO_CENTER = 62


@dataclass
class Slot:
    start: float
    beats: int
    chord: Chord | None
    bar: int


def build_timeline(bars: list[list[str]], choruses: int) -> list[Slot]:
    slots: list[Slot] = []
    for chorus in range(choruses):
        for bar_index, bar in enumerate(bars):
            abs_bar = chorus * len(bars) + bar_index
            beat = abs_bar * BEATS_PER_BAR
            for symbol, length in zip(bar, beat_split(len(bar), BEATS_PER_BAR)):
                chord = None if symbol == NO_CHORD else parse_chord(symbol)
                slots.append(Slot(beat, length, chord, abs_bar))
                beat += length
    return slots


def _event(events: list[dict], t: float, inst: str, note: int, dur: float, vel: float) -> None:
    events.append(
        {"t": round(t, 4), "inst": inst, "note": int(note), "dur": round(dur, 4), "vel": round(max(0.05, min(1.0, vel)), 3)}
    )


def _nearest(pc: int, ref: int, low: int, high: int) -> int:
    """MIDI note with pitch class ``pc`` closest to ``ref`` inside [low, high]."""
    candidates = [n for n in range(low, high + 1) if n % 12 == pc]
    return min(candidates, key=lambda n: (abs(n - ref), n))


def _fit(note: int, low: int = BASS_LOW, high: int = BASS_HIGH) -> int:
    while note < low:
        note += 12
    while note > high:
        note -= 12
    return note


def _next_chord(slots: list[Slot], i: int) -> Chord | None:
    for k in range(1, len(slots) + 1):
        chord = slots[(i + k) % len(slots)].chord
        if chord is not None:
            return chord
    return None


# ---------------------------------------------------------------- bass lines


def _approach(target: int, last: int, rng: random.Random) -> int:
    if last < target:
        options = [target - 1, target - 2] if rng.random() < 0.25 else [target - 1]
    elif last > target:
        options = [target + 1, target + 2] if rng.random() < 0.25 else [target + 1]
    else:
        options = [target - 1, target + 1]
    return _fit(rng.choice(options))


def walking_line(chord: Chord, beats: int, nxt: Chord | None, prev: int, rng: random.Random) -> list[int]:
    root = _nearest(chord.root, prev, BASS_LOW, BASS_HIGH - 4)
    if beats == 1:
        return [root]
    next_root_pc = (nxt or chord).root
    target = _nearest(next_root_pc, root, BASS_LOW, BASS_HIGH - 4)
    third = chord.tone("third") or 4
    fifth = chord.tone("fifth") or 7
    seventh = chord.tone("seventh") or 10
    scale_second = 2 if chord.quality not in ("7b9", "7alt", "dim7", "o7") else 1

    middle_count = beats - 2
    patterns_up = [[third, fifth], [scale_second, third], [fifth, 9 if not chord.is_minor else seventh], [third, 12]]
    patterns_down = [[seventh - 12, fifth - 12], [-1, -(12 - seventh)], [fifth - 12, third - 12], [third, scale_second]]
    going_up = target > root or (target == root and rng.random() < 0.5)
    pattern = rng.choice(patterns_up if going_up else patterns_down)

    notes = [root]
    for iv in pattern[:middle_count]:
        note = _fit(root + iv)
        if note == notes[-1]:
            note = _fit(root + fifth)
        notes.append(note)
    approach = _approach(target, notes[-1], rng)
    if approach == notes[-1]:
        approach = _fit(target + (1 if approach < target else -1))
    notes.append(approach)
    return notes


def bass_part(slots: list[Slot], style: str, swing: float, rng: random.Random) -> list[dict]:
    events: list[dict] = []
    prev = 36
    for i, slot in enumerate(slots):
        chord = slot.chord
        if chord is None:
            continue
        nxt = _next_chord(slots, i)
        root = _nearest(chord.root, prev, BASS_LOW, BASS_HIGH - 10)
        third = chord.tone("third") or 4
        fifth = chord.tone("fifth") or 7
        sixth = 9 if chord.tone("fifth") == 7 else fifth
        seventh = chord.tone("seventh") or 10

        if style == "swing":
            line = walking_line(chord, slot.beats, nxt, prev, rng)
            for b, note in enumerate(line):
                accent = 0.85 if b == 0 else 0.72
                _event(events, slot.start + b, "bass", note, 0.95, accent + rng.uniform(-0.05, 0.05))
                # Occasional swung "skip" note ahead of the next beat.
                if 0 < b < len(line) - 1 and rng.random() < 0.08:
                    _event(events, slot.start + b + swing, "bass", note, 0.3, 0.45)
            prev = line[-1]
        elif style == "shuffle":
            boogie = [0, third, fifth, sixth, seventh, sixth, fifth, third] if not chord.is_minor else [0, third, fifth, seventh, 12, seventh, fifth, third]
            per_beat = boogie[: slot.beats * 2] if slot.beats < 4 else boogie
            if slot.beats == 2:
                per_beat = [0, third, fifth, sixth]
            if slot.beats == 1:
                per_beat = [0, fifth]
            for k, iv in enumerate(per_beat):
                t = slot.start + k // 2 + (swing if k % 2 else 0)
                _event(events, t, "bass", root + iv, 0.55 if k % 2 == 0 else 0.3, 0.82 if k % 2 == 0 else 0.6)
            prev = root
        elif style == "rock":
            pattern = [0, 0, 0, 0, fifth, fifth, sixth, fifth] if slot.beats >= 4 else [0, 0, fifth, fifth][: slot.beats * 2]
            for k, iv in enumerate(pattern):
                _event(events, slot.start + k * 0.5, "bass", root + iv, 0.42, 0.8 if k % 2 == 0 else 0.62)
            prev = root
        else:  # slow 12/8 feel
            steps = [0, third, fifth, sixth][: slot.beats] if slot.beats >= 4 else [0, fifth][: slot.beats]
            for b, iv in enumerate(steps):
                _event(events, slot.start + b, "bass", root + iv, 0.9, 0.8)
            target = _nearest((nxt or chord).root, root, BASS_LOW, BASS_HIGH - 4)
            pickup = _approach(target, root + steps[-1], rng)
            _event(events, slot.start + slot.beats - 1 + swing, "bass", pickup, 0.3, 0.55)
            prev = root
    return events


# ---------------------------------------------------------------- piano


def voicing_pcs(chord: Chord) -> list[int]:
    """Pick 3-4 pitch classes that sound like the chord without the root."""
    iv = set(chord.intervals)
    third = chord.tone("third")
    seventh = chord.tone("seventh")
    fifth = chord.tone("fifth")
    chosen: list[int] = []
    if chord.quality in ("dim7", "o7"):
        chosen = [3, 6, 9, 0]
    elif seventh is None:
        chosen = [0, third or 4, fifth or 7]
        if 9 in iv:
            chosen.append(9)
        elif 14 in iv:
            chosen.append(14)
    else:
        chosen = [third if third is not None else 5, seventh]
        extensions = [x for x in sorted(iv) if x > 12]
        if extensions:
            chosen += extensions[:2]
        elif chord.is_dominant or chord.is_minor or 11 in iv:
            chosen.append(14)
        if fifth is not None and fifth != 7:
            chosen.append(fifth)  # altered fifths are characteristic
        if len(chosen) < 4 and fifth == 7 and not extensions:
            chosen.append(9 if chord.is_dominant else 7)
    pcs: list[int] = []
    for x in chosen:
        pc = (chord.root + x) % 12
        if pc not in pcs:
            pcs.append(pc)
    return pcs[:4]


def voice(pcs: list[int], center: float, low: int = 50, high: int = 77) -> list[int]:
    """Choose the close-position inversion closest to ``center``."""
    best: list[int] | None = None
    best_score = 1e9
    ordered = sorted(pcs)
    for rot in range(len(ordered)):
        cycle = ordered[rot:] + ordered[:rot]
        for base_oct in range(3, 7):
            notes: list[int] = []
            cur = base_oct * 12 + cycle[0]
            notes.append(cur)
            for pc in cycle[1:]:
                nxt = cur + ((pc - cur) % 12 or 12)
                notes.append(nxt)
                cur = nxt
            if notes[0] < low or notes[-1] > high:
                continue
            score = abs(sum(notes) / len(notes) - center)
            if score < best_score:
                best, best_score = notes, score
    if best is None:
        best = [_nearest(pc, int(center), 40, 90) for pc in pcs]
    return best


COMP_PATTERNS_SWING = [
    [(0, 1.2), (3, 0.5)],  # Charleston
    [(2, 0.5), (6, 0.5)],  # 2 and 4
    [(3, 1.0), (7, 0.9)],  # anticipations
    [(0, 2.5)],
    [(1, 0.4), (5, 0.6)],
    [(2, 0.4), (5, 0.4), (7, 0.6)],
    [],
]


def piano_part(slots: list[Slot], style: str, swing: float, rng: random.Random, total_beats: float) -> list[dict]:
    events: list[dict] = []

    def chord_at(t: float) -> Chord | None:
        t = t % total_beats
        for slot in slots:
            if slot.start <= t < slot.start + slot.beats:
                return slot.chord
        return None

    def eighth(bar_start: float, idx: int) -> float:
        return bar_start + idx // 2 + (swing if idx % 2 else 0)

    center = float(PIANO_CENTER)
    cache: dict[Chord, list[int]] = {}

    def play(t: float, dur: float, vel: float, look_ahead: float = 0.0) -> None:
        nonlocal center
        chord = chord_at(t + look_ahead)
        if chord is None:
            return
        if chord not in cache or abs(sum(cache[chord]) / len(cache[chord]) - center) > 4:
            cache[chord] = voice(voicing_pcs(chord), center)
        notes = cache[chord]
        center = 0.7 * center + 0.3 * (sum(notes) / len(notes))
        center = 0.9 * center + 0.1 * PIANO_CENTER  # drift back to the middle
        for n in notes:
            _event(events, t + rng.uniform(0, 0.015), "piano", n, dur, vel + rng.uniform(-0.04, 0.04))

    bar_count = int(total_beats // BEATS_PER_BAR)
    for bar in range(bar_count):
        start = bar * BEATS_PER_BAR
        if style == "swing":
            pattern = rng.choice(COMP_PATTERNS_SWING)
            # Make sure every chord change gets at least one hit.
            changes = [s.start - start for s in slots if start < s.start < start + BEATS_PER_BAR]
            for idx, dur in pattern:
                play(eighth(start, idx), dur, 0.5 if idx % 2 else 0.45, look_ahead=0.4 if idx == 7 else 0.0)
            for c in changes:
                if not any(abs(eighth(start, idx) - (start + c)) < 0.9 for idx, _ in pattern):
                    play(start + c, 0.8, 0.45)
            if not pattern:
                play(eighth(start, 3), 0.6, 0.42)
        elif style == "shuffle":
            for idx in (2, 6):
                play(eighth(start, idx), 0.35, 0.55)
            if rng.random() < 0.5:
                play(eighth(start, 3), 0.3, 0.42)
            if rng.random() < 0.3:
                play(eighth(start, 7), 0.5, 0.45, look_ahead=0.4)
        elif style == "rock":
            play(start, 1.4, 0.48)
            play(start + 1.5, 0.4, 0.4)
            play(start + 2, 1.4, 0.45)
            if rng.random() < 0.4:
                play(start + 3.5, 0.45, 0.4, look_ahead=0.6)
        else:  # slow: triplet chords, accents on the beats
            for beat in range(BEATS_PER_BAR):
                for trip in range(3):
                    t = start + beat + trip / 3
                    play(t, 0.3, 0.38 if trip == 0 else 0.24)
    return events


# ---------------------------------------------------------------- drums


def drum_part(bar_count: int, bars_per_chorus: int, style: str, swing: float, rng: random.Random) -> list[dict]:
    events: list[dict] = []
    for bar in range(bar_count):
        s = bar * BEATS_PER_BAR
        last_of_chorus = (bar + 1) % bars_per_chorus == 0
        first_of_chorus = bar % bars_per_chorus == 0
        if first_of_chorus and bar > 0:
            _event(events, s, "drums", CRASH, 1.5, 0.55)

        if style == "swing":
            for b in range(4):
                _event(events, s + b, "drums", RIDE, 0.5, 0.62 if b % 2 else 0.5)
                _event(events, s + b, "drums", KICK, 0.3, 0.18)
            for b in (1, 3):
                _event(events, s + b + swing, "drums", RIDE, 0.3, 0.42)
                _event(events, s + b, "drums", PEDAL_HAT, 0.2, 0.55)
            if rng.random() < 0.35:
                b = rng.choice([1, 2, 3])
                _event(events, s + b + swing, "drums", SNARE, 0.2, 0.25)
            if last_of_chorus:
                _event(events, s + 3 + swing, "drums", SNARE, 0.2, 0.55)
        elif style == "shuffle":
            for b in range(4):
                _event(events, s + b, "drums", HAT, 0.2, 0.55)
                _event(events, s + b + swing, "drums", HAT, 0.15, 0.35)
            for b in (0, 2):
                _event(events, s + b, "drums", KICK, 0.3, 0.85)
            for b in (1, 3):
                _event(events, s + b, "drums", SNARE, 0.3, 0.8)
            if rng.random() < 0.3:
                _event(events, s + 2 + swing, "drums", KICK, 0.2, 0.5)
            if last_of_chorus:
                _event(events, s + 3 + 1 / 3, "drums", SNARE, 0.2, 0.5)
                _event(events, s + 3 + swing, "drums", SNARE, 0.2, 0.65)
        elif style == "rock":
            for k in range(8):
                _event(events, s + k * 0.5, "drums", HAT, 0.2, 0.55 if k % 2 == 0 else 0.4)
            for t in (0, 2, 2.5):
                _event(events, s + t, "drums", KICK, 0.3, 0.85)
            for b in (1, 3):
                _event(events, s + b, "drums", SNARE, 0.3, 0.85)
            if last_of_chorus:
                for t in (3.25, 3.5, 3.75):
                    _event(events, s + t, "drums", SNARE, 0.2, 0.6)
        else:  # slow
            for b in range(4):
                for trip in range(3):
                    _event(events, s + b + trip / 3, "drums", RIDE, 0.3, 0.45 if trip == 0 else 0.28)
            for b in (0, 2):
                _event(events, s + b, "drums", KICK, 0.4, 0.8)
            for b in (1, 3):
                _event(events, s + b, "drums", SNARE, 0.4, 0.75)
            if rng.random() < 0.4:
                _event(events, s + 2 + swing, "drums", KICK, 0.2, 0.45)
            if last_of_chorus:
                _event(events, s + 3 + 1 / 3, "drums", SNARE, 0.2, 0.45)
                _event(events, s + 3 + swing, "drums", SNARE, 0.2, 0.6)
    return events


def arrange(bars: list[list[str]], style: str, choruses: int = 1, seed: int = 0) -> dict:
    if style not in STYLES:
        raise ValueError(f"Unknown style {style!r}")
    swing = STYLES[style]["swing"]
    rng = random.Random(f"{seed}-{style}")
    slots = build_timeline(bars, choruses)
    bar_count = len(bars) * choruses
    total_beats = bar_count * BEATS_PER_BAR

    events = (
        bass_part(slots, style, swing, rng)
        + piano_part(slots, style, swing, rng, total_beats)
        + drum_part(bar_count, len(bars), style, swing, rng)
    )
    events = [e for e in events if e["t"] < total_beats]
    events.sort(key=lambda e: (e["t"], e["inst"], e["note"]))
    return {
        "style": style,
        "beatsPerBar": BEATS_PER_BAR,
        "barsPerChorus": len(bars),
        "choruses": choruses,
        "totalBeats": total_beats,
        "events": events,
    }
