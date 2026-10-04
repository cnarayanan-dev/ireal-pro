/**
 * Web Audio loop player.
 *
 * The backend sends note events in beats. This module turns them into sound
 * with small synthesizers and a look-ahead scheduler, so playback stays tight
 * and the tempo can change while a loop is running.
 *
 * A "loop" is a list of segments (a whole chorus, or a user-selected range of
 * bars inside each chorus). Segments play back to back and the list repeats.
 */
import type { Instrument, NoteEvent } from "./api";

const LOOKAHEAD_SEC = 0.12;
const TICK_MS = 25;
const COUNT_IN_BEATS = 4;

export interface SegmentSpec {
  start: number; // source beat, inclusive
  end: number; // source beat, exclusive
}

interface Segment extends SegmentSpec {
  length: number;
  events: { v: number; e: NoteEvent }[];
}

interface PlayedSegment {
  startBeat: number;
  segment: Segment;
  pass: number;
}

export interface Position {
  countIn: number | null; // beats left in the count-in, or null
  sourceBeat: number;
  pass: number; // 1-based number of the segment pass being heard
}

function midiToFreq(note: number): number {
  return 440 * Math.pow(2, (note - 69) / 12);
}

export class LoopPlayer {
  readonly ctx: AudioContext;
  private master: GainNode;
  private buses: Record<Instrument, GainNode>;
  private noise: AudioBuffer;

  bpm = 120;
  tempoStep = 0; // bpm added after each pass
  maxPasses = 0; // 0 = loop forever
  countIn = true;
  onTempoChange?: (bpm: number) => void;
  onEnded?: () => void;

  private segments: Segment[] = [];
  private pending: Segment[] | null = null;
  private playing = false;
  private timer: ReturnType<typeof setInterval> | null = null;
  private anchorTime = 0;
  private anchorBeat = 0;
  private segIndex = 0;
  private eventIndex = 0;
  private segStartBeat = 0;
  private passes = 0;
  private stopAtBeat: number | null = null;
  private history: PlayedSegment[] = [];

  constructor() {
    const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    this.ctx = new Ctx();
    const comp = this.ctx.createDynamicsCompressor();
    comp.threshold.value = -14;
    comp.ratio.value = 3;
    this.master = this.ctx.createGain();
    this.master.gain.value = 0.9;
    this.master.connect(comp).connect(this.ctx.destination);
    this.buses = {
      bass: this.bus(0.9),
      piano: this.bus(0.6),
      drums: this.bus(0.7),
    };
    this.noise = this.ctx.createBuffer(1, this.ctx.sampleRate, this.ctx.sampleRate);
    const data = this.noise.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
  }

  private bus(level: number): GainNode {
    const g = this.ctx.createGain();
    g.gain.value = level;
    g.connect(this.master);
    return g;
  }

  get isPlaying(): boolean {
    return this.playing;
  }

  setVolume(inst: Instrument, value: number): void {
    this.buses[inst].gain.setTargetAtTime(value, this.ctx.currentTime, 0.02);
  }

  /** Load events. While playing, the change takes effect at the next segment boundary. */
  load(events: NoteEvent[], specs: SegmentSpec[]): void {
    const sorted = [...events].sort((a, b) => a.t - b.t);
    const segments = specs.map((spec) => ({
      ...spec,
      length: spec.end - spec.start,
      events: sorted.filter((e) => e.t >= spec.start && e.t < spec.end).map((e) => ({ v: e.t - spec.start, e })),
    }));
    if (this.playing) this.pending = segments;
    else this.segments = segments;
  }

  async start(): Promise<void> {
    if (this.playing || this.segments.length === 0) return;
    await this.ctx.resume();
    this.master.gain.cancelScheduledValues(this.ctx.currentTime);
    this.master.gain.setValueAtTime(0.9, this.ctx.currentTime + 0.06);
    this.playing = true;
    this.segIndex = 0;
    this.eventIndex = 0;
    this.passes = 0;
    this.stopAtBeat = null;
    this.anchorTime = this.ctx.currentTime + 0.08;
    this.anchorBeat = this.countIn ? -COUNT_IN_BEATS : 0;
    this.segStartBeat = 0;
    this.history = [{ startBeat: 0, segment: this.segments[0], pass: 1 }];
    if (this.countIn) {
      for (let b = -COUNT_IN_BEATS; b < 0; b++) {
        this.playDrum(b === -COUNT_IN_BEATS ? 37 : 42, this.timeOf(b), b === -COUNT_IN_BEATS ? 0.9 : 0.7);
      }
    }
    this.timer = setInterval(() => this.tick(), TICK_MS);
    this.tick();
  }

  stop(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    if (!this.playing) return;
    this.playing = false;
    if (this.pending) {
      this.segments = this.pending;
      this.pending = null;
    }
    // Fade out to silence notes that were already scheduled.
    const now = this.ctx.currentTime;
    this.master.gain.cancelScheduledValues(now);
    this.master.gain.setValueAtTime(this.master.gain.value, now);
    this.master.gain.linearRampToValueAtTime(0, now + 0.05);
  }

  setTempo(bpm: number): void {
    if (this.playing) {
      const now = this.ctx.currentTime;
      this.anchorBeat = this.beatAt(now);
      this.anchorTime = now;
    }
    this.bpm = bpm;
  }

  private timeOf(beat: number): number {
    return this.anchorTime + ((beat - this.anchorBeat) * 60) / this.bpm;
  }

  private beatAt(time: number): number {
    return this.anchorBeat + ((time - this.anchorTime) * this.bpm) / 60;
  }

  position(): Position | null {
    if (!this.playing) return null;
    const latency = this.ctx.outputLatency || this.ctx.baseLatency || 0;
    const beat = this.beatAt(this.ctx.currentTime - latency);
    if (beat < 0) return { countIn: Math.ceil(-beat), sourceBeat: 0, pass: 1 };
    for (let i = this.history.length - 1; i >= 0; i--) {
      const h = this.history[i];
      if (beat >= h.startBeat) {
        const offset = Math.min(beat - h.startBeat, h.segment.length - 1e-6);
        return { countIn: null, sourceBeat: h.segment.start + offset, pass: h.pass };
      }
    }
    const first = this.history[0];
    return { countIn: null, sourceBeat: first.segment.start, pass: first.pass };
  }

  private tick(): void {
    if (!this.playing) return;
    const now = this.ctx.currentTime;
    const horizon = now + LOOKAHEAD_SEC;

    if (this.stopAtBeat !== null) {
      if (this.timeOf(this.stopAtBeat) <= now) {
        this.stop();
        this.onEnded?.();
      }
      return;
    }

    for (;;) {
      const seg = this.segments[this.segIndex];
      if (this.eventIndex >= seg.events.length) {
        const endBeat = this.segStartBeat + seg.length;
        if (this.timeOf(endBeat) > horizon) break;
        this.advanceSegment(endBeat);
        if (this.stopAtBeat !== null) break;
        continue;
      }
      const item = seg.events[this.eventIndex];
      const beat = this.segStartBeat + item.v;
      const time = this.timeOf(beat);
      if (time > horizon) break;
      if (time >= now - 0.02) this.playEvent(item.e, Math.max(time, now));
      this.eventIndex++;
    }
  }

  private advanceSegment(endBeat: number): void {
    this.passes++;
    if (this.maxPasses > 0 && this.passes >= this.maxPasses) {
      this.stopAtBeat = endBeat;
      return;
    }
    if (this.tempoStep !== 0) {
      // Re-anchor exactly at the boundary so the tempo change lands on beat one.
      this.anchorTime = this.timeOf(endBeat);
      this.anchorBeat = endBeat;
      this.bpm = Math.max(30, Math.min(400, this.bpm + this.tempoStep));
      this.onTempoChange?.(this.bpm);
    }
    if (this.pending) {
      this.segments = this.pending;
      this.pending = null;
    }
    this.segIndex = (this.segIndex + 1) % this.segments.length;
    this.eventIndex = 0;
    this.segStartBeat = endBeat;
    this.history.push({ startBeat: endBeat, segment: this.segments[this.segIndex], pass: this.passes + 1 });
    if (this.history.length > 4) this.history.shift();
  }

  private playEvent(e: NoteEvent, time: number): void {
    const seconds = (e.dur * 60) / this.bpm;
    if (e.inst === "bass") this.playBass(e.note, time, seconds, e.vel);
    else if (e.inst === "piano") this.playPiano(e.note, time, seconds, e.vel);
    else this.playDrum(e.note, time, e.vel);
  }

  // ------------------------------------------------------------- synths

  private envGain(dest: AudioNode, time: number, peak: number, attack: number, decayTo: number, decay: number, end: number, release: number): GainNode {
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, time);
    g.gain.exponentialRampToValueAtTime(Math.max(peak, 0.0002), time + attack);
    g.gain.exponentialRampToValueAtTime(Math.max(decayTo, 0.0001), time + attack + decay);
    g.gain.setValueAtTime(Math.max(decayTo, 0.0001), Math.max(end, time + attack + decay));
    g.gain.exponentialRampToValueAtTime(0.0001, Math.max(end, time + attack + decay) + release);
    g.connect(dest);
    return g;
  }

  private playBass(note: number, time: number, dur: number, vel: number): void {
    const f = midiToFreq(note);
    const end = time + Math.max(dur * 0.9, 0.05);
    const filter = this.ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.Q.value = 2;
    filter.frequency.setValueAtTime(1400, time);
    filter.frequency.exponentialRampToValueAtTime(380, time + 0.18);
    const g = this.envGain(this.buses.bass, time, 0.55 * vel, 0.006, 0.32 * vel, 0.25, end, 0.06);
    filter.connect(g);
    const body = this.ctx.createOscillator();
    body.type = "triangle";
    body.frequency.value = f;
    const sub = this.ctx.createOscillator();
    sub.type = "sine";
    sub.frequency.value = f;
    const pluck = this.ctx.createOscillator();
    pluck.type = "sawtooth";
    pluck.frequency.value = f;
    const pluckGain = this.ctx.createGain();
    pluckGain.gain.setValueAtTime(0.25, time);
    pluckGain.gain.exponentialRampToValueAtTime(0.001, time + 0.12);
    body.connect(filter);
    sub.connect(filter);
    pluck.connect(pluckGain).connect(filter);
    for (const o of [body, sub, pluck]) {
      o.start(time);
      o.stop(end + 0.1);
    }
  }

  private playPiano(note: number, time: number, dur: number, vel: number): void {
    const f = midiToFreq(note);
    const end = time + Math.max(dur, 0.08);
    const peak = 0.16 * vel;
    const g = this.envGain(this.buses.piano, time, peak, 0.004, peak * 0.35, 0.9, end, 0.15);
    const filter = this.ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(5000, time);
    filter.frequency.exponentialRampToValueAtTime(1800, time + 0.4);
    filter.connect(g);
    const partials: [OscillatorType, number, number][] = [
      ["triangle", 1, 1],
      ["sine", 2, 0.35],
      ["sine", 3.01, 0.08],
    ];
    for (const [type, ratio, level] of partials) {
      const o = this.ctx.createOscillator();
      o.type = type;
      o.frequency.value = f * ratio;
      o.detune.value = (Math.random() - 0.5) * 6;
      const lg = this.ctx.createGain();
      lg.gain.value = level;
      o.connect(lg).connect(filter);
      o.start(time);
      o.stop(end + 0.2);
    }
  }

  private noiseBurst(time: number, type: BiquadFilterType, freq: number, q: number, peak: number, decay: number): void {
    const src = this.ctx.createBufferSource();
    src.buffer = this.noise;
    const filter = this.ctx.createBiquadFilter();
    filter.type = type;
    filter.frequency.value = freq;
    filter.Q.value = q;
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(peak, time);
    g.gain.exponentialRampToValueAtTime(0.0001, time + decay);
    src.connect(filter).connect(g).connect(this.buses.drums);
    src.start(time, Math.random() * 0.5);
    src.stop(time + decay + 0.02);
  }

  private tone(time: number, type: OscillatorType, from: number, to: number, peak: number, decay: number): void {
    const o = this.ctx.createOscillator();
    o.type = type;
    o.frequency.setValueAtTime(from, time);
    o.frequency.exponentialRampToValueAtTime(to, time + decay * 0.6);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(peak, time);
    g.gain.exponentialRampToValueAtTime(0.0001, time + decay);
    o.connect(g).connect(this.buses.drums);
    o.start(time);
    o.stop(time + decay + 0.02);
  }

  private playDrum(note: number, time: number, vel: number): void {
    switch (note) {
      case 36: // kick
        this.tone(time, "sine", 150, 42, 0.9 * vel, 0.32);
        break;
      case 37: // side stick
        this.tone(time, "square", 1700, 1500, 0.12 * vel, 0.03);
        this.noiseBurst(time, "bandpass", 2500, 2, 0.3 * vel, 0.04);
        break;
      case 38: // snare
        this.tone(time, "triangle", 210, 160, 0.35 * vel, 0.1);
        this.noiseBurst(time, "highpass", 1200, 0.7, 0.45 * vel, 0.18);
        break;
      case 42: // closed hat
        this.noiseBurst(time, "highpass", 7500, 0.8, 0.22 * vel, 0.05);
        break;
      case 44: // pedal hat
        this.noiseBurst(time, "highpass", 6000, 1, 0.16 * vel, 0.06);
        break;
      case 49: // crash
        this.noiseBurst(time, "highpass", 4000, 0.5, 0.35 * vel, 1.6);
        break;
      case 51: // ride
        this.noiseBurst(time, "bandpass", 9000, 1.2, 0.3 * vel, 0.45);
        this.tone(time, "triangle", 3100, 3000, 0.025 * vel, 0.35);
        break;
      default:
        this.noiseBurst(time, "highpass", 5000, 1, 0.15 * vel, 0.05);
    }
  }
}
