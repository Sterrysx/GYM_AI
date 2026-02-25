import { useState, useEffect, useRef, useCallback } from 'react';
import { ChevronDown, ChevronRight, Timer, CheckCircle2, Loader2, Play, Pause, RotateCcw, TrendingDown } from 'lucide-react';
import { logExercise, fetchAbsHistory } from '../api/client';

/**
 * Abs Routine — 6-minute sequential countdown timer.
 *
 * Layout:
 *   Part 1  (first 3 exercises, 2 min 30 s)
 *   Rest    (30 s)
 *   Part 2  (last 4 exercises, 3 min)
 *   ────────
 *   Total   6:00
 *
 * After the timer finishes the user selects how many seconds they
 * couldn't hold.  That value is stored in `rpe` on the first
 * exercise's workout_log row so we can chart improvement over weeks.
 */

// ── Incomplete-time buckets ──────────────────────────────────────────────────
const INCOMPLETE_OPTIONS = [
  { label: '0 s',  value: 0  },
  { label: '5 s',  value: 5  },
  { label: '10 s', value: 10 },
  { label: '15 s', value: 15 },
  { label: '20 s', value: 20 },
  { label: '30 s', value: 30 },
  { label: '45 s', value: 45 },
  { label: '60 s', value: 60 },
  { label: '90 s+', value: 90 },
];

export default function AbsAccordion({ exercises, week, day, showToast, onReload }) {
  const [open, setOpen] = useState(false);
  const [completing, setCompleting] = useState(false);
  const alreadyLogged = exercises.every((ex) => ex.all_logged);

  // Timer state
  const [phase, setPhase] = useState('idle'); // idle | running | paused | pick | done
  const [elapsed, setElapsed] = useState(0);
  const rafRef = useRef(null);
  const startTsRef = useRef(null);
  const pausedAtRef = useRef(0);

  // History
  const [history, setHistory] = useState([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  // ── Exercise timing ────────────────────────────────────────────────────────
  const exSecs = exercises.map((ex) => {
    const m = String(ex.target_reps).match(/(\d+)/);
    return m ? parseInt(m[1], 10) : 30;
  });
  const part1Count = Math.min(3, exercises.length);
  const part1Secs = exSecs.slice(0, part1Count).reduce((a, b) => a + b, 0);
  const restSecs = 30;
  const part2Secs = exSecs.slice(part1Count).reduce((a, b) => a + b, 0);
  const totalSecs = part1Secs + restSecs + part2Secs;

  // ── Derived display values ─────────────────────────────────────────────────
  const remaining = Math.max(totalSecs - elapsed, 0);
  const pct = totalSecs > 0 ? Math.min(elapsed / totalSecs, 1) : 0;

  let phaseLabel = '';
  let activeIdx = -1;
  if (elapsed < part1Secs) {
    phaseLabel = 'Part 1';
    let acc = 0;
    for (let i = 0; i < part1Count; i++) {
      acc += exSecs[i];
      if (elapsed < acc) { activeIdx = i; break; }
    }
  } else if (elapsed < part1Secs + restSecs) {
    phaseLabel = 'Rest';
  } else {
    phaseLabel = 'Part 2';
    let acc = part1Secs + restSecs;
    for (let i = part1Count; i < exercises.length; i++) {
      acc += exSecs[i];
      if (elapsed < acc) { activeIdx = i; break; }
    }
  }

  // ── Timer loop (rAF) ──────────────────────────────────────────────────────
  const tick = useCallback(() => {
    if (!startTsRef.current) return;
    const now = performance.now();
    const secs = pausedAtRef.current + (now - startTsRef.current) / 1000;
    const clamped = Math.min(Math.floor(secs), totalSecs);
    setElapsed(clamped);
    if (clamped >= totalSecs) {
      setPhase('pick');
      return;
    }
    rafRef.current = requestAnimationFrame(tick);
  }, [totalSecs]);

  useEffect(() => {
    if (phase === 'running') {
      startTsRef.current = performance.now();
      rafRef.current = requestAnimationFrame(tick);
    }
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [phase, tick]);

  // ── Controls ───────────────────────────────────────────────────────────────
  const handleStart = () => {
    pausedAtRef.current = 0;
    setElapsed(0);
    setPhase('running');
  };

  const handlePause = () => {
    cancelAnimationFrame(rafRef.current);
    pausedAtRef.current = elapsed;
    startTsRef.current = null;
    setPhase('paused');
  };

  const handleResume = () => setPhase('running');

  const handleReset = () => {
    cancelAnimationFrame(rafRef.current);
    startTsRef.current = null;
    pausedAtRef.current = 0;
    setElapsed(0);
    setPhase('idle');
  };

  // ── Log routine ────────────────────────────────────────────────────────────
  const handleLog = async (incompleteSecs) => {
    setCompleting(true);
    try {
      for (let i = 0; i < exercises.length; i++) {
        const ex = exercises[i];
        const secs = exSecs[i];
        const sets = ex.sets ?? 1;
        const exId = ex.exercise_id ?? ex.exercise?.toLowerCase().replace(/\s+/g, '_');
        await logExercise({
          week_id: week,
          day,
          exercise_id: exId,
          actual_weight: Array(sets).fill(1),
          actual_reps: Array(sets).fill(secs),
          rpe: i === 0 ? incompleteSecs : null,
        });
      }
      setPhase('done');
      showToast?.(`Abs routine logged! ${incompleteSecs > 0 ? `(${incompleteSecs}s incomplete)` : 'Full completion 🔥'}`);
      onReload?.();
    } catch (err) {
      showToast?.(err.response?.data?.detail ?? err.message, true);
    } finally {
      setCompleting(false);
    }
  };

  // ── Load history on open ───────────────────────────────────────────────────
  useEffect(() => {
    if (open && !historyLoaded) {
      fetchAbsHistory()
        .then((d) => setHistory(d.history || []))
        .catch(() => {})
        .finally(() => setHistoryLoaded(true));
    }
  }, [open, historyLoaded]);

  // ── Helpers ────────────────────────────────────────────────────────────────
  const fmt = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  const totalMin = Math.floor(totalSecs / 60);
  const totalSec = totalSecs % 60;
  const durationStr = totalMin > 0
    ? `${totalMin}m ${totalSec > 0 ? totalSec + 's' : ''}`.trim()
    : `${totalSecs}s`;
  const p1Pct = (part1Secs / totalSecs) * 100;
  const restPct = (restSecs / totalSecs) * 100;

  return (
    <div className="mx-3 my-2 bg-zinc-950 rounded-xl border border-zinc-800 overflow-hidden">
      {/* ── Accordion toggle ─────────────────────────────────── */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left cursor-pointer"
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-zinc-800">
            {alreadyLogged || phase === 'done' ? (
              <CheckCircle2 size={16} className="text-emerald-400" />
            ) : (
              <Timer size={16} className="text-amber-400" />
            )}
          </div>
          <div>
            <p className="text-sm font-bold text-zinc-200">
              Abs Routine{' '}
              {(alreadyLogged || phase === 'done') && <span className="text-emerald-400 text-xs ml-1">✓</span>}
            </p>
            <p className="text-xs text-zinc-500">
              {exercises.length} exercises · {durationStr}
            </p>
          </div>
        </div>
        <div className="text-zinc-500">
          {open ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
        </div>
      </button>

      {/* ── Expanded content ─────────────────────────────────── */}
      {open && (
        <div className="border-t border-zinc-800">

          {/* ── Exercise list ────────────────────────────────── */}
          <div className="divide-y divide-zinc-800/60">
            {exercises.map((ex, idx) => {
              const isActive = idx === activeIdx && (phase === 'running' || phase === 'paused');
              const isPart1 = idx < part1Count;
              return (
                <div
                  key={idx}
                  className={`flex items-center justify-between px-4 py-2.5 gap-3 transition-colors ${
                    isActive ? 'bg-cyan-500/10' : ''
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    {isActive && <Play size={12} className="text-cyan-400 shrink-0" />}
                    <span className={`text-sm leading-snug ${isActive ? 'text-cyan-300 font-semibold' : 'text-zinc-400'}`}>
                      {ex.exercise}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-[0.6rem] font-semibold px-1.5 py-0.5 rounded ${
                      isPart1 ? 'bg-sky-500/10 text-sky-400' : 'bg-violet-500/10 text-violet-400'
                    }`}>
                      {isPart1 ? 'P1' : 'P2'}
                    </span>
                    <span className="flex items-center gap-1 text-xs font-semibold text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded-md">
                      <Timer size={11} />
                      {ex.target_reps}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* ── Timer section ────────────────────────────────── */}
          {!alreadyLogged && phase !== 'done' && phase !== 'pick' && (
            <div className="px-4 py-4 border-t border-zinc-800 space-y-3">

              {/* Countdown display */}
              {(phase === 'running' || phase === 'paused') && (
                <div className="text-center space-y-2">
                  <p className="text-[0.65rem] font-bold uppercase tracking-widest text-zinc-500">
                    {phaseLabel === 'Rest' ? (
                      <span className="text-amber-400">— Rest —</span>
                    ) : (
                      phaseLabel
                    )}
                  </p>
                  <div className="text-4xl font-black tabular-nums text-cyan-400">
                    {fmt(remaining)}
                  </div>

                  {/* Segmented progress bar */}
                  <div className="relative w-full h-2.5 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="absolute inset-y-0 left-0 bg-sky-600/30 rounded-l-full"
                      style={{ width: `${p1Pct}%` }}
                    />
                    <div
                      className="absolute inset-y-0 bg-amber-600/30"
                      style={{ left: `${p1Pct}%`, width: `${restPct}%` }}
                    />
                    <div
                      className="absolute inset-y-0 right-0 bg-violet-600/30 rounded-r-full"
                      style={{ left: `${p1Pct + restPct}%` }}
                    />
                    <div
                      className="absolute inset-y-0 left-0 bg-cyan-500 rounded-full transition-all duration-300 ease-linear"
                      style={{ width: `${pct * 100}%` }}
                    />
                  </div>

                  {activeIdx >= 0 && (
                    <p className="text-xs text-zinc-400">{exercises[activeIdx]?.exercise}</p>
                  )}
                  {phaseLabel === 'Rest' && (
                    <p className="text-xs text-amber-400/70">Breathe…</p>
                  )}
                </div>
              )}

              {/* Controls */}
              <div className="flex gap-2">
                {phase === 'idle' && (
                  <button
                    onClick={handleStart}
                    className="flex-1 py-3 rounded-xl font-bold text-sm uppercase tracking-wide flex items-center justify-center gap-2 bg-cyan-600 text-white active:bg-cyan-500 cursor-pointer transition-all"
                  >
                    <Play size={16} />
                    Start 6-min Routine
                  </button>
                )}
                {phase === 'running' && (
                  <button
                    onClick={handlePause}
                    className="flex-1 py-3 rounded-xl font-bold text-sm uppercase tracking-wide flex items-center justify-center gap-2 bg-zinc-700 text-white active:bg-zinc-600 cursor-pointer transition-all"
                  >
                    <Pause size={16} />
                    Pause
                  </button>
                )}
                {phase === 'paused' && (
                  <>
                    <button
                      onClick={handleResume}
                      className="flex-1 py-3 rounded-xl font-bold text-sm uppercase tracking-wide flex items-center justify-center gap-2 bg-cyan-600 text-white active:bg-cyan-500 cursor-pointer transition-all"
                    >
                      <Play size={16} />
                      Resume
                    </button>
                    <button
                      onClick={handleReset}
                      className="py-3 px-4 rounded-xl text-zinc-500 active:text-zinc-300 cursor-pointer"
                    >
                      <RotateCcw size={16} />
                    </button>
                  </>
                )}
              </div>

              {/* Quick log */}
              {phase === 'idle' && (
                <button
                  onClick={() => setPhase('pick')}
                  disabled={completing}
                  className="w-full py-2 rounded-lg text-xs text-zinc-500 border border-zinc-800 flex items-center justify-center gap-1 cursor-pointer active:text-zinc-300 disabled:opacity-50"
                >
                  {completing ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
                  Quick log (skip timer)
                </button>
              )}
            </div>
          )}

          {/* ── Incomplete-time picker ───────────────────────── */}
          {phase === 'pick' && !alreadyLogged && (
            <div className="px-4 py-4 border-t border-zinc-800 space-y-3">
              <p className="text-center text-xs text-zinc-400 font-semibold">
                How many seconds couldn't you complete?
              </p>
              <div className="grid grid-cols-3 gap-1.5">
                {INCOMPLETE_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => handleLog(opt.value)}
                    disabled={completing}
                    className={`py-2.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer active:scale-95 disabled:opacity-50 ${
                      opt.value === 0
                        ? 'bg-emerald-900/30 border-emerald-700/50 text-emerald-400'
                        : 'bg-zinc-900 border-zinc-700 text-zinc-300 active:bg-zinc-800'
                    }`}
                  >
                    {completing ? '…' : opt.label}
                  </button>
                ))}
              </div>
              <button
                onClick={handleReset}
                className="w-full py-2 rounded-lg text-xs text-zinc-600 flex items-center justify-center gap-1 cursor-pointer active:text-zinc-400"
              >
                <RotateCcw size={12} /> Back
              </button>
            </div>
          )}

          {/* ── Completed state ───────────────────────────────── */}
          {(alreadyLogged || phase === 'done') && (
            <div className="px-4 py-3 border-t border-zinc-800 text-center text-sm text-emerald-400 font-semibold">
              ✓ Completed — XP earned
            </div>
          )}

          {/* ── Incomplete-time history ───────────────────────── */}
          {history.length > 0 && (
            <div className="px-4 py-3 border-t border-zinc-800">
              <div className="flex items-center gap-2 mb-2">
                <TrendingDown size={13} className="text-zinc-500" />
                <span className="text-[0.65rem] font-semibold text-zinc-500 uppercase tracking-wide">
                  Incomplete Over Weeks
                </span>
              </div>
              <div className="flex items-end gap-1 h-12">
                {history.map((h, i) => {
                  const maxVal = Math.max(...history.map((x) => x.incomplete_secs), 1);
                  const barH = Math.max((h.incomplete_secs / maxVal) * 100, 4);
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
                      <div
                        className={`w-full rounded-sm transition-all ${
                          h.incomplete_secs === 0 ? 'bg-emerald-500' : 'bg-sky-500'
                        }`}
                        style={{ height: `${barH}%` }}
                        title={`W${h.week_id}D${h.day}: ${h.incomplete_secs}s`}
                      />
                      <span className="text-[0.5rem] text-zinc-600">W{h.week_id}</span>
                    </div>
                  );
                })}
              </div>
              <p className="text-[0.5rem] text-zinc-600 mt-1 text-center">
                {history[history.length - 1]?.incomplete_secs === 0
                  ? 'Last session: full completion!'
                  : `Last: ${history[history.length - 1]?.incomplete_secs}s incomplete`}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
