"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import ChordChart from "@/components/ChordChart";
import { api, type Meta, type SongInput } from "@/lib/api";

const TEMPLATE = "C7 | F7 | C7 | C7 | F7 | F7 | C7 | C7 | G7 | F7 | C7 | G7";

/** Light client-side parse for the live preview. The backend validates on save. */
function previewBars(chart: string): string[][] {
  const bars: string[][] = [];
  for (const raw of chart.replace(/\n/g, "|").split("|")) {
    const tokens = raw.trim().split(/\s+/).filter(Boolean);
    if (!tokens.length) continue;
    if (tokens.length === 1 && tokens[0] === "%") {
      if (bars.length) bars.push([...bars[bars.length - 1]]);
      continue;
    }
    bars.push(tokens.slice(0, 4));
  }
  return bars;
}

function Editor() {
  const router = useRouter();
  const editId = useSearchParams().get("edit");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [form, setForm] = useState<SongInput>({
    title: "",
    composer: "",
    style: "shuffle",
    key: "C",
    tempo: 110,
    chart: TEMPLATE,
  });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.meta().then(setMeta).catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!editId) return;
    api
      .song(editId)
      .then((s) => setForm({ title: s.title, composer: s.composer, style: s.style, key: s.key, tempo: s.tempo, chart: s.chart }))
      .catch((e: Error) => setError(e.message));
  }, [editId]);

  const bars = useMemo(() => previewBars(form.chart), [form.chart]);

  function set<K extends keyof SongInput>(field: K, value: SongInput[K]) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const song = editId ? await api.updateSong(editId, form) : await api.createSong(form);
      router.push(`/song/${song.id}`);
    } catch (err) {
      setError((err as Error).message);
      setSaving(false);
    }
  }

  return (
    <div className="page">
      <h1>{editId ? "Edit chart" : "New chart"}</h1>
      <form className="editor" onSubmit={save}>
        <div className="editor-fields">
          <label className="field wide">
            <span>Title</span>
            <input required value={form.title} onChange={(e) => set("title", e.target.value)} placeholder="My Blues" />
          </label>
          <label className="field wide">
            <span>Composer</span>
            <input value={form.composer} onChange={(e) => set("composer", e.target.value)} placeholder="Optional" />
          </label>
          <label className="field">
            <span>Key</span>
            <select value={form.key} onChange={(e) => set("key", e.target.value)}>
              {(meta?.keys ?? [form.key]).map((k) => (
                <option key={k}>{k}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Style</span>
            <select value={form.style} onChange={(e) => set("style", e.target.value)}>
              {(meta?.styles ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Tempo</span>
            <input
              type="number"
              min={30}
              max={320}
              value={form.tempo}
              onChange={(e) => set("tempo", Number(e.target.value))}
            />
          </label>
        </div>

        <label className="field wide">
          <span>Chart</span>
          <textarea
            rows={4}
            value={form.chart}
            onChange={(e) => set("chart", e.target.value)}
            spellCheck={false}
            className="mono"
          />
        </label>
        <p className="muted small">
          Separate bars with <code>|</code>. Put two chords in a bar with a space (<code>Cm7 F7</code>). Use{" "}
          <code>%</code> to repeat the previous bar and <code>N.C.</code> for no chord. Qualities: 7, 9, 13, m7,
          m7b5, dim7, maj7, 6, 7#9, 7b9, sus4 and more.
        </p>

        <h2>Preview</h2>
        {bars.length ? <ChordChart bars={bars} /> : <p className="muted">Type some chords above.</p>}

        {error && <p className="error">{error}</p>}
        <div className="actions">
          <button type="submit" className="play" disabled={saving}>
            {saving ? "Saving…" : "Save and play"}
          </button>
          <button type="button" className="ghost" onClick={() => router.back()}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

export default function NewSongPage() {
  return (
    <Suspense fallback={<p className="page muted">Loading…</p>}>
      <Editor />
    </Suspense>
  );
}
