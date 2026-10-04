"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ChordChart from "@/components/ChordChart";
import { api, type Arrangement, type Instrument, type Meta, type SongDetail } from "@/lib/api";
import { LoopPlayer, type SegmentSpec } from "@/lib/audio";

const CHORUSES = 4;
const REPEAT_OPTIONS = [0, 1, 2, 3, 4, 8, 16];
const TEMPO_STEPS = [0, 1, 2, 3, 5, 10];
const INSTRUMENTS: Instrument[] = ["piano", "bass", "drums"];

type Range = { start: number; end: number };

export default function PlayerPage() {
  const { id } = useParams<{ id: string }>();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [song, setSong] = useState<SongDetail | null>(null);
  const [key, setKey] = useState<string | null>(null);
  const [style, setStyle] = useState<string | null>(null);
  const [bpm, setBpm] = useState(120);
  const [seed, setSeed] = useState(0);
  const [arrangement, setArrangement] = useState<Arrangement | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [playing, setPlaying] = useState(false);
  const [repeats, setRepeats] = useState(0);
  const [tempoStep, setTempoStep] = useState(0);
  const [countIn, setCountIn] = useState(true);
  const [volumes, setVolumes] = useState<Record<Instrument, number>>({ piano: 0.6, bass: 0.9, drums: 0.7 });
  const [muted, setMuted] = useState<Record<Instrument, boolean>>({ piano: false, bass: false, drums: false });
  const [range, setRange] = useState<Range | null>(null);
  const [anchor, setAnchor] = useState<number | null>(null);

  const [currentBar, setCurrentBar] = useState<number | null>(null);
  const [pass, setPass] = useState(1);
  const [countdown, setCountdown] = useState<number | null>(null);

  const playerRef = useRef<LoopPlayer | null>(null);
  const startBpmRef = useRef(bpm);

  // Initial load: song defaults and metadata.
  useEffect(() => {
    let cancelled = false;
    Promise.all([api.song(id), api.meta()])
      .then(([s, m]) => {
        if (cancelled) return;
        setSong(s);
        setMeta(m);
        setKey(s.key);
        setStyle(s.style);
        setBpm(s.tempo);
      })
      .catch((e: Error) => setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  // Fetch the arrangement whenever key, style or variation changes.
  useEffect(() => {
    if (!key || !style) return;
    let cancelled = false;
    api
      .arrangement(id, { key, style, choruses: CHORUSES, seed })
      .then((a) => {
        if (!cancelled) setArrangement(a);
      })
      .catch((e: Error) => setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [id, key, style, seed]);

  const bars = arrangement?.song.bars ?? song?.bars ?? [];
  const barsPerChorus = arrangement?.barsPerChorus ?? bars.length;

  const segments = useMemo<SegmentSpec[]>(() => {
    if (!arrangement) return [];
    const n = arrangement.barsPerChorus;
    const bpb = arrangement.beatsPerBar;
    return Array.from({ length: arrangement.choruses }, (_, c) =>
      range
        ? { start: (c * n + range.start) * bpb, end: (c * n + range.end + 1) * bpb }
        : { start: c * n * bpb, end: (c + 1) * n * bpb },
    );
  }, [arrangement, range]);

  const getPlayer = useCallback(() => {
    if (!playerRef.current) {
      const p = new LoopPlayer();
      p.onTempoChange = (b) => setBpm(b);
      p.onEnded = () => {
        setPlaying(false);
        setCurrentBar(null);
        setCountdown(null);
      };
      playerRef.current = p;
    }
    return playerRef.current;
  }, []);

  // Push events and settings into the audio engine.
  useEffect(() => {
    if (arrangement && segments.length && playerRef.current) {
      playerRef.current.load(arrangement.events, segments);
    }
  }, [arrangement, segments]);

  useEffect(() => {
    const p = playerRef.current;
    if (!p) return;
    p.maxPasses = repeats;
    p.tempoStep = tempoStep;
    p.countIn = countIn;
  }, [repeats, tempoStep, countIn]);

  useEffect(() => {
    const p = playerRef.current;
    if (!p) return;
    for (const inst of INSTRUMENTS) p.setVolume(inst, muted[inst] ? 0 : volumes[inst]);
  }, [volumes, muted]);

  // Cleanup on unmount.
  useEffect(
    () => () => {
      playerRef.current?.stop();
      playerRef.current?.ctx.close();
      playerRef.current = null;
    },
    [],
  );

  // Animation loop for the bar cursor.
  useEffect(() => {
    if (!playing) return;
    let frame = 0;
    const update = () => {
      const pos = playerRef.current?.position();
      if (pos && arrangement) {
        setCountdown(pos.countIn);
        if (pos.countIn === null) {
          setCurrentBar(Math.floor(pos.sourceBeat / arrangement.beatsPerBar) % arrangement.barsPerChorus);
          setPass(pos.pass);
        }
      }
      frame = requestAnimationFrame(update);
    };
    frame = requestAnimationFrame(update);
    return () => cancelAnimationFrame(frame);
  }, [playing, arrangement]);

  const start = useCallback(async () => {
    if (!arrangement) return;
    const p = getPlayer();
    p.maxPasses = repeats;
    p.tempoStep = tempoStep;
    p.countIn = countIn;
    for (const inst of INSTRUMENTS) p.setVolume(inst, muted[inst] ? 0 : volumes[inst]);
    p.setTempo(bpm);
    p.load(arrangement.events, segments);
    startBpmRef.current = bpm;
    setPass(1);
    await p.start();
    setPlaying(true);
  }, [arrangement, getPlayer, repeats, tempoStep, countIn, muted, volumes, bpm, segments]);

  const stop = useCallback(() => {
    playerRef.current?.stop();
    setPlaying(false);
    setCurrentBar(null);
    setCountdown(null);
    if (tempoStep !== 0) {
      setBpm(startBpmRef.current);
      playerRef.current?.setTempo(startBpmRef.current);
    }
  }, [tempoStep]);

  const toggle = useCallback(() => (playing ? stop() : start()), [playing, start, stop]);

  // Space bar toggles playback.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (e.code !== "Space" || ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)) return;
      e.preventDefault();
      toggle();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle]);

  function changeTempo(value: number) {
    const v = Math.max(30, Math.min(320, Math.round(value) || 30));
    setBpm(v);
    startBpmRef.current = v;
    playerRef.current?.setTempo(v);
  }

  function onBarClick(i: number, shift: boolean) {
    if (shift && range) {
      setRange({ start: Math.min(range.start, i), end: Math.max(range.end, i) });
      setAnchor(null);
    } else if (anchor !== null) {
      setRange({ start: Math.min(anchor, i), end: Math.max(anchor, i) });
      setAnchor(null);
    } else {
      setRange({ start: i, end: i });
      setAnchor(i);
    }
  }

  if (error) {
    return (
      <div className="page">
        <p className="error">{error}</p>
        <Link href="/">Back to library</Link>
      </div>
    );
  }
  if (!song || !meta || !key || !style) return <p className="page muted">Loading…</p>;

  const passLabel = range ? "Loop" : "Chorus";
  const loopLabel = range ? `Bars ${range.start + 1}–${range.end + 1}` : `Whole form (${barsPerChorus} bars)`;

  return (
    <div className="page player">
      <div className="song-head">
        <div>
          <h1>{song.title}</h1>
          <p className="muted">
            {[song.composer, meta.styles.find((s) => s.id === style)?.name].filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="status" aria-live="polite">
          {countdown !== null ? (
            <span className="count-in">{countdown}</span>
          ) : playing ? (
            <span>
              {passLabel} {pass}
              {repeats ? ` / ${repeats}` : ""}
            </span>
          ) : (
            <span className="muted">Stopped</span>
          )}
        </div>
      </div>

      <section className="transport" aria-label="Transport">
        <button type="button" className={`play ${playing ? "on" : ""}`} onClick={toggle} disabled={!arrangement}>
          {playing ? "■ Stop" : "▶ Play"}
        </button>

        <label className="field">
          <span>Tempo</span>
          <span className="tempo">
            <button type="button" onClick={() => changeTempo(bpm - 5)} aria-label="Slower">
              −
            </button>
            <input
              type="number"
              min={30}
              max={320}
              value={bpm}
              onChange={(e) => changeTempo(Number(e.target.value))}
              aria-label="Tempo in BPM"
            />
            <button type="button" onClick={() => changeTempo(bpm + 5)} aria-label="Faster">
              +
            </button>
          </span>
        </label>

        <label className="field">
          <span>Key</span>
          <select value={key} onChange={(e) => setKey(e.target.value)}>
            {meta.keys.map((k) => (
              <option key={k} value={k}>
                {k}
                {k === song.key ? " (original)" : ""}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Style</span>
          <select value={style} onChange={(e) => setStyle(e.target.value)}>
            {meta.styles.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Repeat</span>
          <select value={repeats} onChange={(e) => setRepeats(Number(e.target.value))}>
            {REPEAT_OPTIONS.map((r) => (
              <option key={r} value={r}>
                {r === 0 ? "∞ Loop forever" : `${r}×`}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Speed up</span>
          <select value={tempoStep} onChange={(e) => setTempoStep(Number(e.target.value))}>
            {TEMPO_STEPS.map((s) => (
              <option key={s} value={s}>
                {s === 0 ? "Off" : `+${s} bpm / ${passLabel.toLowerCase()}`}
              </option>
            ))}
          </select>
        </label>

        <label className="check">
          <input type="checkbox" checked={countIn} onChange={(e) => setCountIn(e.target.checked)} />
          Count-in
        </label>

        <button type="button" className="ghost" onClick={() => setSeed((s) => s + 1)} title="Generate new bass and comping">
          ↻ New variation
        </button>
      </section>

      <section className="loop-bar" aria-label="Loop range">
        <span>
          <strong>Looping:</strong> {loopLabel}
          {anchor !== null && <em> (click another bar to finish the range)</em>}
        </span>
        <span className="muted hint">Click a bar to loop it, click a second bar to loop the range in between.</span>
        {range && (
          <button
            type="button"
            className="ghost small"
            onClick={() => {
              setRange(null);
              setAnchor(null);
            }}
          >
            Loop whole form
          </button>
        )}
      </section>

      <ChordChart bars={bars} currentBar={currentBar} range={range} onBarClick={onBarClick} />

      <section className="mixer" aria-label="Mixer">
        {INSTRUMENTS.map((inst) => (
          <div key={inst} className="channel">
            <button
              type="button"
              className={`mute ${muted[inst] ? "on" : ""}`}
              onClick={() => setMuted((m) => ({ ...m, [inst]: !m[inst] }))}
              aria-pressed={muted[inst]}
            >
              {muted[inst] ? "Muted" : "Mute"}
            </button>
            <label>
              <span className="channel-name">{inst}</span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={volumes[inst]}
                onChange={(e) => setVolumes((v) => ({ ...v, [inst]: Number(e.target.value) }))}
              />
            </label>
          </div>
        ))}
      </section>

      <p className="muted small">
        Space bar plays and stops. Key, style and loop range changes take effect at the next pass.
        {!song.builtin && (
          <>
            {" "}
            <Link href={`/new?edit=${song.id}`}>Edit chart</Link>
          </>
        )}
      </p>
    </div>
  );
}
