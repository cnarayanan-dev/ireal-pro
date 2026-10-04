"""FastAPI app for the iReal-style blues practice tool."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from .arranger import STYLES, arrange
from .store import SongStore
from .theory import (
    KEYS,
    ChordError,
    format_chart,
    interval_between_keys,
    key_prefers_flats,
    parse_chart,
    parse_note,
    transpose_bars,
)

app = FastAPI(title="Blues Loop API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

store = SongStore()


class SongIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    composer: str = Field(default="", max_length=120)
    style: str = "shuffle"
    key: str = "C"
    tempo: int = Field(default=120, ge=30, le=320)
    chart: str = Field(min_length=1, max_length=5000)

    @field_validator("style")
    @classmethod
    def _style(cls, v: str) -> str:
        if v not in STYLES:
            raise ValueError(f"style must be one of {sorted(STYLES)}")
        return v

    @field_validator("key")
    @classmethod
    def _key(cls, v: str) -> str:
        try:
            parse_note(v)
        except ChordError as e:
            raise ValueError(str(e)) from e
        return v

    @field_validator("chart")
    @classmethod
    def _chart(cls, v: str) -> str:
        try:
            return format_chart(parse_chart(v))
        except ChordError as e:
            raise ValueError(str(e)) from e


def _with_bars(song: dict, key: str | None) -> dict:
    bars = parse_chart(song["chart"])
    target = key or song["key"]
    if key:
        bars = transpose_bars(bars, interval_between_keys(song["key"], key), key_prefers_flats(key))
    return {**song, "key": target, "originalKey": song["key"], "bars": bars}


def _get_or_404(song_id: str) -> dict:
    song = store.get(song_id)
    if song is None:
        raise HTTPException(404, "Song not found")
    return song


def _check_key(key: str | None) -> None:
    if key is None:
        return
    try:
        parse_note(key)
    except ChordError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/meta")
def meta() -> dict:
    return {
        "keys": KEYS,
        "styles": [{"id": k, **v} for k, v in STYLES.items()],
    }


@app.get("/api/songs")
def list_songs() -> list[dict]:
    return store.all()


@app.get("/api/songs/{song_id}")
def get_song(song_id: str, key: str | None = None) -> dict:
    _check_key(key)
    return _with_bars(_get_or_404(song_id), key)


@app.post("/api/songs", status_code=201)
def create_song(song: SongIn) -> dict:
    return _with_bars(store.create(song.model_dump()), None)


@app.put("/api/songs/{song_id}")
def update_song(song_id: str, song: SongIn) -> dict:
    existing = _get_or_404(song_id)
    if existing["builtin"]:
        raise HTTPException(403, "Built-in songs are read-only")
    updated = store.update(song_id, song.model_dump())
    return _with_bars(updated, None)


@app.delete("/api/songs/{song_id}", status_code=204)
def delete_song(song_id: str) -> None:
    existing = _get_or_404(song_id)
    if existing["builtin"]:
        raise HTTPException(403, "Built-in songs are read-only")
    store.delete(song_id)


@app.get("/api/songs/{song_id}/arrangement")
def song_arrangement(
    song_id: str,
    key: str | None = None,
    style: str | None = None,
    choruses: int = Query(default=4, ge=1, le=16),
    seed: int = 0,
) -> dict:
    _check_key(key)
    song = _with_bars(_get_or_404(song_id), key)
    style = style or song["style"]
    if style not in STYLES:
        raise HTTPException(422, f"Unknown style {style!r}")
    return {"song": song, **arrange(song["bars"], style, choruses, seed)}


class ChartIn(BaseModel):
    chart: str
    style: str = "shuffle"
    choruses: int = Field(default=1, ge=1, le=16)
    seed: int = 0


@app.post("/api/arrange")
def arrange_chart(body: ChartIn) -> dict:
    """Arrange an ad-hoc chart, used by the editor's preview."""
    if body.style not in STYLES:
        raise HTTPException(422, f"Unknown style {body.style!r}")
    try:
        bars = parse_chart(body.chart)
    except ChordError as e:
        raise HTTPException(422, str(e)) from e
    return {"bars": bars, **arrange(bars, body.style, body.choruses, body.seed)}
