import pytest
from fastapi.testclient import TestClient

from app import main
from app.arranger import STYLES, arrange
from app.songs import BUILTIN_SONGS
from app.store import SongStore
from app.theory import ChordError, parse_chart, parse_chord, transpose_symbol


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "store", SongStore(tmp_path / "songs.json"))
    return TestClient(main.app)


def test_parse_chord_variants():
    assert parse_chord("Bb7").root == 10
    assert parse_chord("F#m7b5").quality == "m7b5"
    assert parse_chord("C7/E").bass == 4
    with pytest.raises(ChordError):
        parse_chord("H7")
    with pytest.raises(ChordError):
        parse_chord("Cwhat")


def test_parse_chart_repeat_and_split():
    bars = parse_chart("C7 | % | F7 F#dim7 | N.C.")
    assert bars == [["C7"], ["C7"], ["F7", "F#dim7"], ["N.C."]]


def test_transpose_spelling():
    assert transpose_symbol("C7", 5, prefer_flats=True) == "F7"
    assert transpose_symbol("F7", 5, prefer_flats=True) == "Bb7"
    assert transpose_symbol("A7/C#", 2, prefer_flats=False) == "B7/D#"


@pytest.mark.parametrize("song", BUILTIN_SONGS, ids=lambda s: s["id"])
@pytest.mark.parametrize("style", list(STYLES))
def test_every_song_arranges_in_every_style(song, style):
    bars = parse_chart(song["chart"])
    result = arrange(bars, style, choruses=2, seed=3)
    assert result["totalBeats"] == len(bars) * 4 * 2
    insts = {e["inst"] for e in result["events"]}
    assert insts == {"bass", "piano", "drums"}
    for e in result["events"]:
        assert 0 <= e["t"] < result["totalBeats"]
        assert 0 < e["vel"] <= 1
        if e["inst"] == "bass":
            assert 24 <= e["note"] <= 55
        if e["inst"] == "piano":
            assert 40 <= e["note"] <= 90


def test_walking_bass_hits_root_on_downbeats():
    bars = parse_chart("F7 | Bb7 | F7 | Cm7 F7")
    result = arrange(bars, "swing", seed=1)
    downbeats = {e["t"]: e["note"] % 12 for e in result["events"] if e["inst"] == "bass" and e["t"] % 4 == 0}
    assert downbeats == {0: 5, 4: 10, 8: 5, 12: 0}


def test_arrangement_is_deterministic():
    bars = parse_chart("C7 | F7 | C7 | G7")
    assert arrange(bars, "swing", seed=7) == arrange(bars, "swing", seed=7)


def test_list_and_get_transposed(client):
    songs = client.get("/api/songs").json()
    assert any(s["id"] == "basic-12-bar-blues" for s in songs)
    song = client.get("/api/songs/basic-12-bar-blues", params={"key": "Bb"}).json()
    assert song["key"] == "Bb"
    assert song["bars"][0] == ["Bb7"]
    assert song["bars"][4] == ["Eb7"]


def test_arrangement_endpoint(client):
    r = client.get("/api/songs/jazz-blues/arrangement", params={"key": "C", "style": "shuffle", "choruses": 2})
    assert r.status_code == 200
    data = r.json()
    assert data["song"]["bars"][0] == ["C7"]
    assert data["totalBeats"] == 12 * 4 * 2
    assert client.get("/api/songs/jazz-blues/arrangement", params={"style": "polka"}).status_code == 422
    assert client.get("/api/songs/nope/arrangement").status_code == 404


def test_crud_user_song(client):
    body = {"title": "My Blues", "key": "G", "style": "swing", "tempo": 150, "chart": "G7|C7|G7|%"}
    created = client.post("/api/songs", json=body)
    assert created.status_code == 201
    song = created.json()
    assert song["chart"] == "G7 | C7 | G7 | G7"
    assert song["builtin"] is False

    body["title"] = "Renamed"
    assert client.put(f"/api/songs/{song['id']}", json=body).json()["title"] == "Renamed"
    assert client.delete(f"/api/songs/{song['id']}").status_code == 204
    assert client.get(f"/api/songs/{song['id']}").status_code == 404


def test_builtin_songs_are_read_only(client):
    assert client.delete("/api/songs/jazz-blues").status_code == 403


def test_bad_chart_rejected(client):
    body = {"title": "Bad", "chart": "C7 | Xm7"}
    assert client.post("/api/songs", json=body).status_code == 422
    assert client.post("/api/arrange", json={"chart": "C7 | Xm7"}).status_code == 422
