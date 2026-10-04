"use client";

const QUALITY_DISPLAY: Record<string, string> = {
  maj7: "Δ7",
  M7: "Δ7",
  "^7": "Δ7",
  "^": "Δ7",
  maj9: "Δ9",
  "^9": "Δ9",
  m7b5: "ø7",
  "-7b5": "ø7",
  h7: "ø7",
  h: "ø7",
  dim7: "°7",
  o7: "°7",
  dim: "°",
  o: "°",
  "-": "m",
  "-7": "m7",
  "-6": "m6",
  "-9": "m9",
};

function pretty(text: string): string {
  return text.replace(/b/g, "♭").replace(/#/g, "♯");
}

export function ChordSymbol({ symbol }: { symbol: string }) {
  if (symbol === "N.C.") return <span className="chord nc">N.C.</span>;
  const m = symbol.match(/^([A-G])([#b]?)(.*?)(?:\/([A-G][#b]?))?$/);
  if (!m) return <span className="chord">{symbol}</span>;
  const [, letter, acc, quality, bass] = m;
  const q = QUALITY_DISPLAY[quality] ?? quality;
  return (
    <span className="chord">
      <span className="root">
        {letter}
        {acc && <span className="acc">{pretty(acc)}</span>}
      </span>
      {q && <sup className="quality">{pretty(q)}</sup>}
      {bass && <span className="bass">/{pretty(bass)}</span>}
    </span>
  );
}

interface Props {
  bars: string[][];
  currentBar?: number | null;
  range?: { start: number; end: number } | null;
  onBarClick?: (index: number, shift: boolean) => void;
}

export default function ChordChart({ bars, currentBar = null, range = null, onBarClick }: Props) {
  return (
    <div className="chart" role="grid" aria-label="Chord chart">
      {bars.map((bar, i) => {
        const inRange = range !== null && i >= range.start && i <= range.end;
        const classes = [
          "bar",
          i === currentBar ? "current" : "",
          inRange ? "in-range" : "",
          i === bars.length - 1 ? "final" : "",
          i % 4 === 0 ? "row-start" : "",
        ]
          .filter(Boolean)
          .join(" ");
        const repeat = i > 0 && bar.join(" ") === bars[i - 1].join(" ") && bar.length === 1;
        return (
          <button
            type="button"
            key={i}
            className={classes}
            onClick={(e) => onBarClick?.(i, e.shiftKey)}
            disabled={!onBarClick}
            title={`Bar ${i + 1}`}
          >
            <span className="bar-number">{i + 1}</span>
            <span className={`bar-chords n${bar.length}`}>
              {repeat ? (
                <span className="repeat" aria-label={`repeat ${bar[0]}`}>
                  %
                </span>
              ) : (
                bar.map((c, k) => <ChordSymbol key={k} symbol={c} />)
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
}
