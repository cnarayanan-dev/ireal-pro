export type Instrument = "bass" | "piano" | "drums";

export interface NoteEvent {
  t: number;
  inst: Instrument;
  note: number;
  dur: number;
  vel: number;
}

export interface Song {
  id: string;
  title: string;
  composer: string;
  style: string;
  key: string;
  tempo: number;
  chart: string;
  builtin: boolean;
}

export interface SongDetail extends Song {
  originalKey: string;
  bars: string[][];
}

export interface Arrangement {
  song: SongDetail;
  style: string;
  beatsPerBar: number;
  barsPerChorus: number;
  choruses: number;
  totalBeats: number;
  events: NoteEvent[];
}

export interface StyleInfo {
  id: string;
  name: string;
  description: string;
}

export interface Meta {
  keys: string[];
  styles: StyleInfo[];
}

export type SongInput = Omit<Song, "id" | "builtin">;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join(", ");
    } catch {
      // keep the status text
    }
    throw new Error(message);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  meta: () => request<Meta>("/api/meta"),
  songs: () => request<Song[]>("/api/songs"),
  song: (id: string) => request<SongDetail>(`/api/songs/${encodeURIComponent(id)}`),
  arrangement: (id: string, opts: { key: string; style: string; choruses: number; seed: number }) => {
    const q = new URLSearchParams({
      key: opts.key,
      style: opts.style,
      choruses: String(opts.choruses),
      seed: String(opts.seed),
    });
    return request<Arrangement>(`/api/songs/${encodeURIComponent(id)}/arrangement?${q}`);
  },
  createSong: (song: SongInput) => request<SongDetail>("/api/songs", { method: "POST", body: JSON.stringify(song) }),
  updateSong: (id: string, song: SongInput) =>
    request<SongDetail>(`/api/songs/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify(song) }),
  deleteSong: (id: string) => request<void>(`/api/songs/${encodeURIComponent(id)}`, { method: "DELETE" }),
};
