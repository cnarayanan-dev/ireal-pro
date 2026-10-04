# Blues Loop

An iReal Pro style practice tool focused on looping blues backing tracks.
Pick a blues, choose a key, style and tempo, and it plays bass, piano and drums
in a loop while the chord chart highlights the current bar.

- **Backend:** Python + FastAPI. Stores chord charts, transposes them and generates
  the arrangement (walking or boogie bass, piano comping, drum grooves).
- **Frontend:** Next.js (App Router, TypeScript). Shows the chart and plays the
  arrangement with the Web Audio API using built-in synths. No samples needed.

## Features

- 10 built-in blues forms: 12-bar, quick change, jazz, bebop, Bird blues, minor,
  slow, 8-bar, straight-eighth and funky ninth blues
- 4 styles: Jazz Swing, Blues Shuffle, Slow Blues 12/8, Straight Blues Rock
- Endless looping, or a fixed number of repeats
- Loop any range of bars (click a bar, then click a second bar)
- Transpose to all 12 keys
- Tempo change live, plus automatic speed-up after each pass
- Count-in, per-instrument volume and mute
- "New variation" re-generates the bass line and comping
- Create, edit and delete your own charts

## Running

Backend (port 8000):

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (port 3000), in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The frontend proxies `/api/*` to the backend. Set
`BACKEND_URL` if the backend runs elsewhere.

## Tests

```bash
cd backend && python -m pytest
cd frontend && npm run typecheck && npm run build
```

## Chart format

Bars are separated by `|`. Chords inside a bar are separated by spaces and
split the bar evenly.

```
F7 | Bb7 | F7 | Cm7 F7 | Bb7 | Bdim7 | F7 | D7 | Gm7 | C7 | F7 D7 | Gm7 C7
```

- `%` repeats the previous bar
- `N.C.` means no chord
- Slash chords like `C7/E` are supported
- Qualities include `7 9 13 7b9 7#9 7alt m m6 m7 m9 m7b5 dim dim7 maj7 6 sus4 7sus4 aug`

## API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/meta` | Keys and styles |
| GET | `/api/songs` | All songs |
| GET | `/api/songs/{id}?key=Bb` | One song, optionally transposed |
| GET | `/api/songs/{id}/arrangement?key=&style=&choruses=&seed=` | Note events for playback |
| POST | `/api/songs` | Create a song |
| PUT | `/api/songs/{id}` | Update a user song |
| DELETE | `/api/songs/{id}` | Delete a user song |
| POST | `/api/arrange` | Arrange an ad-hoc chart |

User songs are saved to `backend/data/user_songs.json` (override with `SONGS_FILE`).
