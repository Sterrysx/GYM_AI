/**
 * MuscleMap — Cyberpunk "Level 2" interactive anatomical body map.
 *
 * Features:
 *  • Clean SVG bodies (no text labels) with neon glow by intensity
 *  • Framer-Motion glassmorphism tooltip on hover/tap
 *  • RPG level cards with XP bars, tier gates, and 1RM strength locks
 *  • Smooth CSS transitions on all path elements
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Loader2, Swords, Star, ChevronRight, X, TrendingUp,
  Dumbbell, Trophy, Target, Zap, Lock, ShieldCheck, Flame,
} from 'lucide-react';
import { fetchMuscleLevels } from '../api/client';

// ── Cyberpunk neon palette (0-7 intensity scale) ─────────────────────────────
//    0-1 : dim grey / slate          — no glow
//    2-3 : cyan                      — medium glow
//    4-5 : purple                    — strong glow
//    6-7 : emerald → crimson         — intense glow
const NEON = [
  // 0  Untrained
  { fill: 'rgba(63,63,70,0.30)',  stroke: '#3f3f46', glow: '',                                              tier: 'Untrained',  tierColor: 'text-zinc-600', accent: '#52525b' },
  // 1  Novice
  { fill: 'rgba(100,116,139,0.30)', stroke: '#64748b', glow: '',                                            tier: 'Novice',     tierColor: 'text-slate-400', accent: '#64748b' },
  // 2  Trained
  { fill: 'rgba(6,182,212,0.35)',  stroke: '#06b6d4', glow: 'drop-shadow(0 0 8px rgba(6,182,212,0.6))',     tier: 'Trained',    tierColor: 'text-cyan-400', accent: '#06b6d4' },
  // 3  Intermediate
  { fill: 'rgba(6,182,212,0.50)',  stroke: '#22d3ee', glow: 'drop-shadow(0 0 10px rgba(6,182,212,0.75))',   tier: 'Intermediate', tierColor: 'text-cyan-300', accent: '#22d3ee' },
  // 4  Advanced
  { fill: 'rgba(168,85,247,0.40)', stroke: '#a855f7', glow: 'drop-shadow(0 0 12px rgba(168,85,247,0.8))',   tier: 'Advanced',   tierColor: 'text-purple-400', accent: '#a855f7' },
  // 5  Expert
  { fill: 'rgba(168,85,247,0.55)', stroke: '#c084fc', glow: 'drop-shadow(0 0 14px rgba(168,85,247,0.9))',   tier: 'Expert',     tierColor: 'text-purple-300', accent: '#c084fc' },
  // 6  Elite
  { fill: 'rgba(16,185,129,0.50)', stroke: '#10b981', glow: 'drop-shadow(0 0 20px rgba(16,185,129,1))',     tier: 'Elite',      tierColor: 'text-emerald-400', accent: '#10b981' },
  // 7  Legend
  { fill: 'rgba(239,68,68,0.55)',  stroke: '#ef4444', glow: 'drop-shadow(0 0 22px rgba(239,68,68,1))',      tier: 'Legend',     tierColor: 'text-red-400', accent: '#ef4444' },
];

function getNeon(level) {
  // Map any level (0-99) to the 0-7 neon scale
  const idx = Math.min(Math.floor(level / 8), 7); // 0-7 = 0, 8-15 = 1, 16-23 = 2, ...
  // But for the new system levels can be 0-60+, so use tiers:
  // 0 → 0, 1-4 → 1, 5-9 → 2, 10-14 → 3, 15-19 → 4, 20-29 → 5, 30-39 → 6, 40+ → 7
  if (level <= 0) return NEON[0];
  if (level <= 4) return NEON[1];
  if (level <= 9) return NEON[2];
  if (level <= 14) return NEON[3];
  if (level <= 19) return NEON[4];
  if (level <= 29) return NEON[5];
  if (level <= 39) return NEON[6];
  return NEON[7];
}

// ── Muscle-group → SVG element ids ───────────────────────────────────────────
const MUSCLE_SVG_IDS = {
  chest:      { front: ['chest'] },
  shoulders:  { front: ['shoulders-l', 'shoulders-r'] },
  abs:        { front: ['abs'] },
  biceps:     { front: ['biceps-l', 'biceps-r'] },
  forearms:   { front: ['forearms-l', 'forearms-r'] },
  triceps:    { front: ['triceps-l', 'triceps-r'], back: ['triceps-bl', 'triceps-br'] },
  quads:      { front: ['quads-l', 'quads-r'] },
  calves:     { front: ['calves-l', 'calves-r'], back: ['calves-bl', 'calves-br'] },
  back:       { back: ['back-upper', 'back-lat-l', 'back-lat-r'] },
  traps:      { back: ['traps'] },
  rear_delts: { back: ['rear_delts-l', 'rear_delts-r'] },
  lower_back: { back: ['lower_back'] },
  glutes:     { back: ['glutes'] },
  hamstrings: { back: ['hamstrings-l', 'hamstrings-r'] },
};

// ── Glassmorphism Tooltip ────────────────────────────────────────────────────
function NeonTooltip({ muscle, position }) {
  if (!muscle || !position) return null;
  const neon = getNeon(muscle.level);
  const gate = muscle.gate_blocked ? 'GATE LOCKED' : null;

  return (
    <AnimatePresence>
      <motion.div
        key={muscle.muscle}
        initial={{ opacity: 0, y: 10, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 10, scale: 0.95 }}
        transition={{ duration: 0.15, ease: 'easeOut' }}
        className="absolute z-40 pointer-events-none px-3.5 py-2.5 rounded-xl border bg-black/80 backdrop-blur-md min-w-[160px]"
        style={{
          left: position.x,
          top: position.y,
          borderColor: `${neon.stroke}66`,
          boxShadow: neon.glow ? `0 0 20px ${neon.stroke}40` : 'none',
        }}
      >
        <div className="flex items-center gap-2 mb-1">
          <div
            className="w-7 h-7 rounded-md flex items-center justify-center font-black text-xs border"
            style={{ borderColor: neon.stroke, background: neon.fill, color: neon.stroke }}
          >
            {muscle.level}
          </div>
          <div>
            <div className="text-xs font-bold text-white">{muscle.display_name}</div>
            <div className={`text-[0.55rem] font-semibold ${neon.tierColor}`}>{neon.tier}</div>
          </div>
        </div>
        {/* XP mini bar */}
        <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden mt-1">
          <div className="h-full rounded-full transition-all duration-500" style={{ width: `${muscle.xp_pct}%`, background: neon.stroke }} />
        </div>
        <div className="flex justify-between mt-0.5">
          <span className="text-[0.45rem] text-zinc-500">Lv.{muscle.level}</span>
          <span className="text-[0.45rem] text-zinc-500">{Math.round(muscle.xp_pct)}% → Lv.{muscle.level + 1}</span>
        </div>
        {gate && (
          <div className="flex items-center gap-1 mt-1.5 text-[0.55rem] text-amber-400">
            <Lock size={8} />
            <span className="font-semibold">{gate}</span>
            <span className="text-zinc-500 ml-0.5">— {muscle.gate_message}</span>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}


// ── Body SVG Viewer with neon glow ───────────────────────────────────────────
function BodyView({ svgUrl, muscleLevels, view, onMuscleClick, onMuscleHover, onMuscleLeave, selectedMuscle }) {
  const containerRef = useRef(null);
  const [svgLoaded, setSvgLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setSvgLoaded(false);
    fetch(svgUrl)
      .then((r) => r.text())
      .then((text) => {
        if (cancelled || !containerRef.current) return;
        containerRef.current.innerHTML = text;
        setSvgLoaded(true);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [svgUrl]);

  useEffect(() => {
    if (!svgLoaded || !containerRef.current) return;
    const svgEl = containerRef.current.querySelector('svg');
    if (!svgEl) return;

    // Reset
    svgEl.querySelectorAll('.muscle-region').forEach((el) => {
      el.style.fill = 'rgba(50,50,50,0.2)';
      el.style.stroke = '#444';
      el.style.strokeWidth = '0.6';
      el.style.filter = '';
      el.style.transition = 'all 0.3s ease-in-out';
    });

    // Apply neon colours
    for (const [muscle, ids] of Object.entries(MUSCLE_SVG_IDS)) {
      const pathIds = ids[view] || [];
      const data = muscleLevels.find((m) => m.muscle === muscle);
      if (!data) continue;
      const neon = getNeon(data.level);

      for (const pathId of pathIds) {
        const el = svgEl.getElementById(pathId);
        if (!el) continue;
        el.style.fill = neon.fill;
        el.style.stroke = neon.stroke;
        el.style.strokeWidth = selectedMuscle === muscle ? '2' : '1';
        el.style.filter = selectedMuscle === muscle
          ? `${neon.glow} drop-shadow(0 0 4px ${neon.stroke})`
          : neon.glow;
        el.style.cursor = 'pointer';

        el.onclick = (e) => { e.stopPropagation(); onMuscleClick(muscle); };
        el.onmouseenter = (e) => {
          const rect = containerRef.current.getBoundingClientRect();
          onMuscleHover(muscle, { x: e.clientX - rect.left + 10, y: e.clientY - rect.top - 80 });
        };
        el.onmouseleave = () => onMuscleLeave();
        el.ontouchstart = (e) => {
          e.preventDefault();
          const touch = e.touches[0];
          const rect = containerRef.current.getBoundingClientRect();
          onMuscleHover(muscle, { x: touch.clientX - rect.left + 10, y: touch.clientY - rect.top - 80 });
          setTimeout(() => onMuscleClick(muscle), 300);
        };
      }
    }
  }, [svgLoaded, muscleLevels, view, selectedMuscle, onMuscleClick, onMuscleHover, onMuscleLeave]);

  return (
    <div
      ref={containerRef}
      className="relative flex-1 flex items-center justify-center [&>svg]:max-h-[55vh] [&>svg]:w-auto"
    />
  );
}


// ── XP Bar ───────────────────────────────────────────────────────────────────
function XpBar({ pct, level }) {
  const neon = getNeon(level);
  return (
    <div className="relative w-full h-3 bg-zinc-900 rounded-full overflow-hidden border border-zinc-800">
      <motion.div
        className="absolute inset-y-0 left-0 rounded-full"
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(pct, 100)}%` }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        style={{ background: `linear-gradient(90deg, ${neon.stroke}55, ${neon.stroke})` }}
      />
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-[0.5rem] font-bold text-white/80 drop-shadow">{Math.round(pct)}%</span>
      </div>
    </div>
  );
}


// ── Tier Gate Badge ──────────────────────────────────────────────────────────
function GateBadge({ gate }) {
  if (!gate) return null;
  return (
    <div className="flex items-center gap-1.5 bg-amber-500/10 border border-amber-500/30 rounded-lg px-2.5 py-1.5 mb-3">
      <Lock size={11} className="text-amber-400 shrink-0" />
      <div>
        <div className="text-[0.6rem] font-bold text-amber-400 uppercase tracking-wide">Strength Gate</div>
        <div className="text-[0.6rem] text-zinc-400">{gate}</div>
      </div>
    </div>
  );
}


// ── Muscle Detail Panel (slide-up sheet) ─────────────────────────────────────
function MuscleDetailPanel({ muscle, onClose }) {
  if (!muscle) return null;
  const neon = getNeon(muscle.level);
  const targetNeon = getNeon(muscle.target_level);
  const xpRemaining = Math.max(0, muscle.xp_for_next - muscle.xp_in_level);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center" onClick={onClose}>
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
      <motion.div
        initial={{ y: '100%', opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: '100%', opacity: 0 }}
        transition={{ type: 'spring', damping: 28, stiffness: 300 }}
        className="relative w-full max-w-lg bg-zinc-950 border-t rounded-t-2xl p-5 pb-8"
        style={{ borderColor: `${neon.stroke}44` }}
        onClick={(e) => e.stopPropagation()}
      >
        <button onClick={onClose} className="absolute top-3 right-3 text-zinc-500 active:text-zinc-300 cursor-pointer p-1">
          <X size={18} />
        </button>
        <div className="w-10 h-1 rounded-full mx-auto mb-4" style={{ background: `${neon.stroke}66` }} />

        {/* Title */}
        <div className="flex items-center gap-3 mb-4">
          <div
            className="w-14 h-14 rounded-xl flex items-center justify-center border-2"
            style={{ borderColor: neon.stroke, background: neon.fill, boxShadow: neon.glow ? `0 0 16px ${neon.stroke}55` : 'none' }}
          >
            <span className="text-xl font-black" style={{ color: neon.stroke }}>{muscle.level}</span>
          </div>
          <div>
            <h3 className="text-lg font-bold">{muscle.display_name}</h3>
            <div className="flex items-center gap-2 text-xs">
              <span className={`font-semibold ${neon.tierColor}`}>{neon.tier}</span>
              <ChevronRight size={10} className="text-zinc-600" />
              <span className="text-zinc-500">Target: <span className={`font-semibold ${targetNeon.tierColor}`}>Lv.{muscle.target_level}</span></span>
            </div>
          </div>
        </div>

        {/* Gate */}
        {muscle.gate_blocked && <GateBadge gate={muscle.gate_message} />}

        {/* XP Progress */}
        <div className="mb-4">
          <div className="flex justify-between text-xs text-zinc-500 mb-1">
            <span>Level {muscle.level}</span>
            <span>Level {muscle.level + 1}</span>
          </div>
          <XpBar pct={muscle.xp_pct} level={muscle.level} />
          <div className="flex justify-between text-[0.6rem] text-zinc-600 mt-1">
            <span>{Math.round(muscle.xp_in_level).toLocaleString()} XP</span>
            <span>{Math.round(muscle.xp_for_next).toLocaleString()} XP</span>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-2 mb-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-2.5 text-center">
            <Zap size={12} className="mx-auto mb-1 text-cyan-400" />
            <div className="text-sm font-bold">{Math.round(muscle.xp).toLocaleString()}</div>
            <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">Total XP</div>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-2.5 text-center">
            <Target size={12} className="mx-auto mb-1 text-purple-400" />
            <div className="text-sm font-bold">{Math.round(xpRemaining).toLocaleString()}</div>
            <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">XP to Next</div>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-2.5 text-center">
            {muscle.estimated_1rm ? (
              <>
                <Flame size={12} className="mx-auto mb-1 text-amber-400" />
                <div className="text-sm font-bold">{muscle.estimated_1rm}kg</div>
                <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">Est. 1RM</div>
              </>
            ) : (
              <>
                <Trophy size={12} className="mx-auto mb-1 text-amber-400" />
                <div className="text-sm font-bold">{muscle.target_level}</div>
                <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">Target Lv</div>
              </>
            )}
          </div>
        </div>

        {/* How to level up */}
        {xpRemaining > 0 && (
          <div className="bg-cyan-500/5 border border-cyan-500/20 rounded-lg p-3 mb-4">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-cyan-400 mb-1">
              <TrendingUp size={12} />
              How to level up
            </div>
            <p className="text-[0.7rem] text-zinc-400 leading-relaxed">
              {muscle.gate_blocked ? (
                <>
                  <span className="text-amber-300 font-semibold">Strength gate active.</span>{' '}
                  {muscle.gate_message}
                </>
              ) : (
                <>
                  You need <span className="text-cyan-300 font-semibold">{Math.round(xpRemaining).toLocaleString()} more XP</span> to reach Level {muscle.level + 1}.
                  {' '}XP scales with intensity — lifting heavier (closer to your 1RM) earns exponentially more.
                  {' '}Try <span className="text-zinc-200 font-semibold">{Math.ceil(xpRemaining / 30)} reps at 30kg</span> or <span className="text-zinc-200 font-semibold">{Math.ceil(xpRemaining / 60)} reps at 60kg</span>.
                </>
              )}
            </p>
          </div>
        )}

        {/* Contributing Exercises */}
        <div>
          <div className="flex items-center gap-1.5 text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-2">
            <Dumbbell size={11} />
            Contributing Exercises
          </div>
          {muscle.exercises?.length > 0 ? (
            <div className="space-y-1.5 max-h-40 overflow-y-auto">
              {muscle.exercises.map((ex) => (
                <div key={ex.exercise_id} className="flex items-center justify-between bg-zinc-900/60 border border-zinc-800/50 rounded-lg px-3 py-2">
                  <span className="text-xs font-medium truncate flex-1">{ex.name}</span>
                  <div className="flex items-center gap-3 shrink-0 text-xs text-zinc-400">
                    <span>{ex.sets}s</span>
                    <span>{ex.reps}r</span>
                    <span className="font-semibold" style={{ color: neon.stroke }}>{Math.round(ex.volume).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-zinc-600 text-center py-3">No exercises logged yet.</p>
          )}
        </div>
      </motion.div>
    </div>
  );
}


// ── Neon Legend ───────────────────────────────────────────────────────────────
function NeonLegend() {
  return (
    <div className="flex flex-wrap gap-1.5 justify-center px-4 py-2">
      {NEON.map((n, i) => (
        <div key={i} className="flex items-center gap-1">
          <div
            className="w-3 h-3 rounded-sm border transition-all"
            style={{ background: n.fill, borderColor: n.stroke, filter: n.glow || 'none' }}
          />
          <span className={`text-[0.5rem] ${n.tierColor}`}>{n.tier.slice(0, 3)}</span>
        </div>
      ))}
    </div>
  );
}


// ── Muscle Cards Grid ────────────────────────────────────────────────────────
function MuscleCards({ muscles, onSelect }) {
  const sorted = [...muscles].sort((a, b) => b.level - a.level || b.xp - a.xp);
  return (
    <div className="grid grid-cols-2 gap-1.5 px-3 pb-4">
      {sorted.map((m) => {
        const neon = getNeon(m.level);
        const atTarget = m.level >= m.target_level;
        return (
          <motion.button
            key={m.muscle}
            whileTap={{ scale: 0.97 }}
            onClick={() => onSelect(m.muscle)}
            className="flex items-center gap-2 bg-zinc-950 border border-zinc-800/60 rounded-lg px-2.5 py-2 text-left cursor-pointer active:bg-zinc-900 transition-colors"
          >
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center border shrink-0 transition-all duration-300"
              style={{ borderColor: neon.stroke, background: neon.fill, boxShadow: neon.glow ? `0 0 8px ${neon.stroke}44` : 'none' }}
            >
              <span className="text-xs font-black" style={{ color: neon.stroke }}>{m.level}</span>
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1">
                <span className="text-[0.65rem] font-semibold truncate">{m.display_name}</span>
                {m.gate_blocked && <Lock size={7} className="text-amber-400 shrink-0" />}
              </div>
              <div className="flex items-center gap-1 mt-0.5">
                <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${m.xp_pct}%`, background: neon.stroke }}
                  />
                </div>
                {atTarget ? (
                  <Star size={8} className="text-amber-400 shrink-0" fill="currentColor" />
                ) : (
                  <span className="text-[0.45rem] text-zinc-600 shrink-0">→{m.target_level}</span>
                )}
              </div>
            </div>
          </motion.button>
        );
      })}
    </div>
  );
}


// ── Main Export ───────────────────────────────────────────────────────────────
export default function MuscleMap() {
  const [levels, setLevels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('front');
  const [selectedMuscle, setSelectedMuscle] = useState(null);
  const [detailMuscle, setDetailMuscle] = useState(null);
  const [tooltip, setTooltip] = useState({ muscle: null, pos: null });

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchMuscleLevels();
        setLevels(data.muscle_levels || []);
      } catch { /* ignore */ }
      finally { setLoading(false); }
    })();
  }, []);

  const handleMuscleClick = useCallback((muscle) => {
    setSelectedMuscle(muscle);
    setTooltip({ muscle: null, pos: null });
    const data = levels.find((m) => m.muscle === muscle);
    if (data) setDetailMuscle(data);
  }, [levels]);

  const handleMuscleHover = useCallback((muscle, pos) => {
    const data = levels.find((m) => m.muscle === muscle);
    if (data) setTooltip({ muscle: data, pos });
  }, [levels]);

  const handleMuscleLeave = useCallback(() => {
    setTooltip({ muscle: null, pos: null });
  }, []);

  const totalLevel = levels.reduce((s, m) => s + m.level, 0);
  const totalXp = levels.reduce((s, m) => s + m.xp, 0);
  const gatedCount = levels.filter((m) => m.gate_blocked).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-zinc-500 text-sm">
        <Loader2 size={18} className="animate-spin" />
        Loading muscle map…
      </div>
    );
  }

  return (
    <div className="pb-24">
      {/* Header */}
      <div className="px-4 pt-3 pb-2">
        <div className="flex items-center gap-2 mb-2">
          <Swords size={16} className="text-cyan-400" />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">Muscle Map</h2>
        </div>
        <div className="flex gap-2 mb-3">
          <div className="flex-1 bg-zinc-950 border border-zinc-800/60 rounded-xl px-3 py-2 text-center">
            <div className="text-lg font-black text-cyan-400">{totalLevel}</div>
            <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">Total Level</div>
          </div>
          <div className="flex-1 bg-zinc-950 border border-zinc-800/60 rounded-xl px-3 py-2 text-center">
            <div className="text-lg font-black text-purple-400">{Math.round(totalXp).toLocaleString()}</div>
            <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">Total XP</div>
          </div>
          <div className="flex-1 bg-zinc-950 border border-zinc-800/60 rounded-xl px-3 py-2 text-center">
            <div className="text-lg font-black text-emerald-400">{levels.length}</div>
            <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">Muscles</div>
          </div>
          {gatedCount > 0 && (
            <div className="flex-1 bg-zinc-950 border border-amber-500/20 rounded-xl px-3 py-2 text-center">
              <div className="text-lg font-black text-amber-400">{gatedCount}</div>
              <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">Gated</div>
            </div>
          )}
        </div>
      </div>

      {/* View Toggle */}
      <div className="flex items-center justify-center gap-2 px-4 mb-2">
        {['front', 'back'].map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`px-5 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wide transition-all cursor-pointer border ${
              view === v
                ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-400'
                : 'bg-zinc-900/60 border-zinc-800/50 text-zinc-500'
            }`}
          >
            {v}
          </button>
        ))}
      </div>

      {/* Body SVG + tooltip */}
      <div className="relative flex justify-center px-4 py-2 min-h-[50vh]">
        <BodyView
          svgUrl={view === 'front' ? '/body_front.svg' : '/body_back.svg'}
          muscleLevels={levels}
          view={view}
          onMuscleClick={handleMuscleClick}
          onMuscleHover={handleMuscleHover}
          onMuscleLeave={handleMuscleLeave}
          selectedMuscle={selectedMuscle}
        />
        <NeonTooltip muscle={tooltip.muscle} position={tooltip.pos} />
      </div>

      <NeonLegend />

      <p className="text-center text-[0.6rem] text-zinc-600 mb-3">Tap a muscle to see your level & how to progress</p>

      <MuscleCards muscles={levels} onSelect={handleMuscleClick} />

      <AnimatePresence>
        {detailMuscle && (
          <MuscleDetailPanel muscle={detailMuscle} onClose={() => { setDetailMuscle(null); setSelectedMuscle(null); }} />
        )}
      </AnimatePresence>
    </div>
  );
}
