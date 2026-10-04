"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, type Meta, type Song } from "@/lib/api";

export default function LibraryPage() {
  const [songs, setSongs] = useState<Song[] | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [query, setQuery] = useState("");
  const [style, setStyle] = useState("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.songs(), api.meta()])
      .then(([s, m]) => {
        setSongs(s);
        setMeta(m);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (songs ?? []).filter(
      (s) =>
        (style === "all" || s.style === style) &&
        (!q || s.title.toLowerCase().includes(q) || s.composer.toLowerCase().includes(q)),
    );
  }, [songs, query, style]);

  const styleName = (id: string) => meta?.styles.find((s) => s.id === id)?.name ?? id;

  async function remove(song: Song) {
    if (!confirm(`Delete "${song.title}"?`)) return;
    try {
      await api.deleteSong(song.id);
      setSongs((prev) => prev?.filter((s) => s.id !== song.id) ?? null);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="page">
      <div className="library-head">
        <h1>Library</h1>
        <div className="filters">
          <input
            type="search"
            placeholder="Search songs"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search songs"
          />
          <select value={style} onChange={(e) => setStyle(e.target.value)} aria-label="Filter by style">
            <option value="all">All styles</option>
            {meta?.styles.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <p className="error">
          {error}. Is the backend running on port 8000?
        </p>
      )}
      {!songs && !error && <p className="muted">Loading…</p>}

      <ul className="song-list">
        {filtered.map((song) => (
          <li key={song.id}>
            <Link href={`/song/${song.id}`} className="song-card">
              <span className="song-title">{song.title}</span>
              <span className="song-meta">
                {song.composer || "Unknown"} · {styleName(song.style)}
              </span>
              <span className="song-badges">
                <span className="badge">{song.key}</span>
                <span className="badge">{song.tempo} bpm</span>
                {!song.builtin && <span className="badge mine">mine</span>}
              </span>
            </Link>
            {!song.builtin && (
              <div className="song-actions">
                <Link href={`/new?edit=${song.id}`}>Edit</Link>
                <button type="button" className="link danger" onClick={() => remove(song)}>
                  Delete
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
      {songs && filtered.length === 0 && <p className="muted">No songs match.</p>}
    </div>
  );
}
