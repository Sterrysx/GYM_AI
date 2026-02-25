/**
 * MuscleMap — Cyberpunk body map using react-body-highlighter.
 *
 * Features:
 *  • Professional anatomical SVG via <Model /> (anterior + posterior)
 *  • Neon glow palette by level tier (cyan → purple → emerald → crimson)
 *  • Hover tooltips on each muscle region
 *  • Framer-Motion glassmorphism detail panel with:
 *      - Benchmark PR (anchor exercise 1RM)
 *      - Dynamic per-exercise level-up recommendations
 *      - XP progress bars and gate badges
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Model from 'react-body-highlighter';
import {
  Loader2, Swords, Star, ChevronRight, X, TrendingUp,
  Dumbbell, Trophy, Target, Zap, Lock, Flame,
} from 'lucide-react';
import { fetchMuscleLevels } from '../api/client';

// ── Cyberpunk neon palette (0-7 intensity scale) ─────────────────────────────
const NEON = [
  { fill: '#3f3f46', tier: 'Untrained',    tierColor: 'text-zinc-600', accent: '#52525b' },
  { fill: '#64748b', tier: 'Novice',       tierColor: 'text-slate-400', accent: '#64748b' },
  { fill: '#06b6d4', tier: 'Trained',      tierColor: 'text-cyan-400', accent: '#06b6d4' },
  { fill: '#22d3ee', tier: 'Intermediate', tierColor: 'text-cyan-300', accent: '#22d3ee' },
  { fill: '#a855f7', tier: 'Advanced',     tierColor: 'text-purple-400', accent: '#a855f7' },
  { fill: '#c084fc', tier: 'Expert',       tierColor: 'text-purple-300', accent: '#c084fc' },
  { fill: '#10b981', tier: 'Elite',        tierColor: 'text-emerald-400', accent: '#10b981' },
  { fill: '#ef4444', tier: 'Legend',       tierColor: 'text-red-400', accent: '#ef4444' },
];

function getNeonIndex(level) {
  if (level <= 0) return 0;
  if (level <= 4) return 1;
  if (level <= 9) return 2;
  if (level <= 14) return 3;
  if (level <= 19) return 4;
  if (level <= 29) return 5;
  if (level <= 39) return 6;
  return 7;
}

function getNeon(level) {
  return NEON[getNeonIndex(level)];
}

// Gradient palette for react-body-highlighter (indexed by frequency)
const HIGHLIGHT_COLORS = NEON.map((n) => n.fill);

// Polygon → muscle slug mapping (matches the library's internal SVG render order)
const ANTERIOR_POLYGON_MAP = [
  ...Array(2).fill('chest'),
  ...Array(2).fill('obliques'),
  ...Array(2).fill('abs'),
  ...Array(2).fill('biceps'),
  ...Array(2).fill('triceps'),
  ...Array(2).fill('neck'),
  ...Array(2).fill('front-deltoids'),
  ...Array(1).fill('head'),
  ...Array(2).fill('abductors'),
  ...Array(6).fill('quadriceps'),
  ...Array(2).fill('knees'),
  ...Array(4).fill('calves'),
  ...Array(4).fill('forearm'),
];

const POSTERIOR_POLYGON_MAP = [
  ...Array(1).fill('head'),
  ...Array(2).fill('trapezius'),
  ...Array(2).fill('back-deltoids'),
  ...Array(2).fill('upper-back'),
  ...Array(4).fill('triceps'),
  ...Array(2).fill('lower-back'),
  ...Array(4).fill('forearm'),
  ...Array(2).fill('gluteal'),
  ...Array(2).fill('adductor'),
  ...Array(4).fill('hamstring'),
  ...Array(2).fill('knees'),
  ...Array(4).fill('calves'),
  ...Array(1).fill('left-soleus'),
  ...Array(1).fill('right-soleus'),
];


// ── Hover Tooltip ────────────────────────────────────────────────────────────
function HoverTooltip({ info }) {
  if (!info) return null;
  const { muscle, cx, cy } = info;
  const neon = getNeon(muscle.level);
  const bm = muscle.benchmark;
  return (
    <div
      className="fixed z-[100] pointer-events-none bg-zinc-900/95 backdrop-blur-sm border border-zinc-700/80 rounded-lg px-3 py-2.5 shadow-2xl min-w-40"
      style={{
        left: cx + 16,
        top: cy,
        transform: 'translateY(-100%)',
      }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-xs font-bold text-zinc-100">{muscle.display_name}</span>
        <span
          className="text-[0.55rem] font-bold px-1.5 py-0.5 rounded"
          style={{ background: `${neon.fill}22`, color: neon.fill }}
        >
          Lv.{muscle.level}
        </span>
      </div>
      <div className="flex items-center gap-1.5 text-[0.55rem] text-zinc-400 mb-1.5">
        <span className={`font-semibold ${neon.tierColor}`}>{neon.tier}</span>
        <span>·</span>
        <span>{Math.round(muscle.xp).toLocaleString()} XP</span>
      </div>
      <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden mb-1">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${muscle.xp_pct}%`, background: neon.fill }}
        />
      </div>
      <div className="flex justify-between text-[0.45rem] text-zinc-600">
        <span>Lv.{muscle.level}</span>
        <span>{Math.round(muscle.xp_pct)}%</span>
        <span>Lv.{muscle.level + 1}</span>
      </div>
      {bm && (
        <div className="mt-1.5 pt-1.5 border-t border-zinc-800 text-[0.55rem] text-zinc-400">
          <span className="text-amber-400 font-semibold">{bm.estimated_1rm}kg</span> PR · {bm.exercise_name}
        </div>
      )}
      {muscle.gate_blocked && (
        <div className="mt-1 text-[0.5rem] text-amber-400 font-semibold">⚠ Strength Gate Active</div>
      )}
    </div>
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
        style={{ background: `linear-gradient(90deg, ${neon.fill}55, ${neon.fill})` }}
      />
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-[0.5rem] font-bold text-white/80 drop-shadow">{Math.round(pct)}%</span>
      </div>
    </div>
  );
}


// ── Gate Badge ───────────────────────────────────────────────────────────────
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
  const bm = muscle.benchmark; // {exercise_name, estimated_1rm, best_weight, best_reps} | null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center" onClick={onClose}>
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
      <motion.div
        initial={{ y: '100%', opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: '100%', opacity: 0 }}
        transition={{ type: 'spring', damping: 28, stiffness: 300 }}
        className="relative w-full max-w-lg bg-zinc-950 border-t rounded-t-2xl p-5 pb-8 max-h-[85vh] overflow-y-auto"
        style={{ borderColor: `${neon.fill}44` }}
        onClick={(e) => e.stopPropagation()}
      >
        <button onClick={onClose} className="absolute top-3 right-3 text-zinc-500 active:text-zinc-300 cursor-pointer p-1">
          <X size={18} />
        </button>
        <div className="w-10 h-1 rounded-full mx-auto mb-4" style={{ background: `${neon.fill}66` }} />

        {/* Title */}
        <div className="flex items-center gap-3 mb-4">
          <div
            className="w-14 h-14 rounded-xl flex items-center justify-center border-2"
            style={{ borderColor: neon.fill, background: `${neon.fill}22`, boxShadow: `0 0 16px ${neon.fill}55` }}
          >
            <span className="text-xl font-black" style={{ color: neon.fill }}>{muscle.level}</span>
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

        {/* Stats Grid */}
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
            {bm ? (
              <>
                <Flame size={12} className="mx-auto mb-1 text-amber-400" />
                <div className="text-sm font-bold">{bm.estimated_1rm}kg</div>
                <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">Benchmark PR</div>
                <div className="text-[0.45rem] text-zinc-600 mt-0.5 truncate">{bm.exercise_name}</div>
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

        {/* Level-Up Recommendations */}
        {xpRemaining > 0 && (
          <div className="bg-cyan-500/5 border border-cyan-500/20 rounded-lg p-3 mb-4">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-cyan-400 mb-1">
              <TrendingUp size={12} />
              How to reach Level {muscle.level + 1}
            </div>
            {muscle.gate_blocked ? (
              <p className="text-[0.7rem] text-zinc-400 leading-relaxed">
                <span className="text-amber-300 font-semibold">Strength gate active.</span>{' '}
                {muscle.gate_message}
              </p>
            ) : (
              <>
                <p className="text-[0.7rem] text-zinc-400 leading-relaxed mb-2">
                  You need <span className="text-cyan-300 font-semibold">{Math.round(xpRemaining).toLocaleString()} more XP</span> to reach Level {muscle.level + 1}.
                  Here's what to do next session:
                </p>
                {muscle.exercises?.filter(e => e.reps_to_next != null).length > 0 && (
                  <div className="space-y-1">
                    {muscle.exercises.filter(e => e.reps_to_next != null).slice(0, 4).map((ex) => (
                      <div key={ex.exercise_id} className="flex items-center justify-between bg-zinc-900/80 rounded-md px-2 py-1.5">
                        <span className="text-[0.65rem] text-zinc-300 truncate flex-1">{ex.name}</span>
                        <span className="text-[0.65rem] font-bold text-cyan-400 shrink-0 ml-2">
                          +{ex.reps_to_next} reps @ {ex.weight_for_calc}kg
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
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
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="text-xs font-medium truncate">{ex.name}</span>
                    <span className="text-[0.5rem] text-zinc-600 shrink-0">×{ex.ratio}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0 text-xs text-zinc-400">
                    <span>{ex.sets}s</span>
                    <span>{ex.reps}r</span>
                    <span className="font-semibold" style={{ color: neon.fill }}>{Math.round(ex.volume).toLocaleString()}</span>
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
          <div className="w-3 h-3 rounded-sm border border-zinc-700" style={{ background: n.fill }} />
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
              style={{ borderColor: neon.fill, background: `${neon.fill}22`, boxShadow: `0 0 8px ${neon.fill}44` }}
            >
              <span className="text-xs font-black" style={{ color: neon.fill }}>{m.level}</span>
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
                    style={{ width: `${m.xp_pct}%`, background: neon.fill }}
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
  const [view, setView] = useState('anterior');
  const [detailMuscle, setDetailMuscle] = useState(null);
  const [hoverInfo, setHoverInfo] = useState(null);
  const modelRef = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchMuscleLevels();
        setLevels(data.muscle_levels || []);
      } catch { /* ignore */ }
      finally { setLoading(false); }
    })();
  }, []);

  // Map backend muscle keys → library-supported SVG muscle slugs.
  // Some backend muscles don't have their own SVG region, so we merge them
  // into the closest visual equivalent for highlighting purposes.
  const MUSCLE_TO_SVG = {
    'chest': 'chest',
    'front-deltoids': 'front-deltoids',
    'side-deltoids': 'front-deltoids',   // no SVG region; highlight front delts
    'back-deltoids': 'back-deltoids',
    'triceps': 'triceps',
    'biceps': 'biceps',
    'forearm': 'forearm',
    'trapezius': 'trapezius',
    'upper-back': 'upper-back',
    'lower-back': 'lower-back',
    'lats': 'upper-back',               // no SVG region; highlight upper back
    'abs': 'abs',
    'obliques': 'obliques',
    'quadriceps': 'quadriceps',
    'hamstring': 'hamstring',
    'calves': 'calves',
    'gluteal': 'gluteal',
    'abductors': 'abductors',
  };

  // Build the data array for react-body-highlighter.
  // Aggregate frequency (max neon tier) when multiple backend muscles map to
  // the same SVG slug (e.g. lats + upper-back both → upper-back).
  const svgBuckets = {};
  for (const m of levels) {
    const slug = MUSCLE_TO_SVG[m.muscle];
    if (!slug) continue;                       // skip unknown muscles entirely
    const freq = getNeonIndex(m.level) + 1;    // 1-indexed for highlightedColors
    if (!svgBuckets[slug] || freq > svgBuckets[slug].freq) {
      svgBuckets[slug] = { freq, name: m.display_name };
    }
  }
  const modelData = Object.entries(svgBuckets).map(([slug, { freq, name }]) => ({
    name,
    muscles: [slug],
    frequency: freq,
  }));

  const handleModelClick = useCallback(({ muscle }) => {
    const data = levels.find((m) => m.muscle === muscle);
    if (data) setDetailMuscle(data);
  }, [levels]);

  // Build reverse map: SVG slug → backend muscle key(s)
  const svgToBackend = {};
  for (const [key, slug] of Object.entries(MUSCLE_TO_SVG)) {
    if (!svgToBackend[slug]) svgToBackend[slug] = [];
    svgToBackend[slug].push(key);
  }

  // Tag SVG polygons with data-muscle attributes after each render
  useEffect(() => {
    if (!modelRef.current) return;
    const polygons = modelRef.current.querySelectorAll('polygon');
    const map = view === 'anterior' ? ANTERIOR_POLYGON_MAP : POSTERIOR_POLYGON_MAP;
    polygons.forEach((p, i) => {
      if (map[i]) p.setAttribute('data-muscle', map[i]);
    });
  }, [view, levels, loading]);

  // Hover handler for the model container
  const handleModelPointerMove = useCallback((e) => {
    const slug = e.target.getAttribute?.('data-muscle');
    if (!slug) { setHoverInfo(null); return; }
    // Map SVG slug to backend muscle keys (reverse of MUSCLE_TO_SVG)
    const backendKeys = svgToBackend[slug] || [slug];
    const matches = levels.filter((m) => backendKeys.includes(m.muscle));
    if (matches.length === 0) { setHoverInfo(null); return; }
    const best = matches.sort((a, b) => b.level - a.level)[0];
    setHoverInfo({
      muscle: best,
      cx: e.clientX,
      cy: e.clientY,
    });
  }, [levels, svgToBackend]);

  const handleModelPointerLeave = useCallback(() => setHoverInfo(null), []);

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
        {[
          { key: 'anterior', label: 'Front' },
          { key: 'posterior', label: 'Back' },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setView(key)}
            className={`px-5 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wide transition-all cursor-pointer border ${
              view === key
                ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-400'
                : 'bg-zinc-900/60 border-zinc-800/50 text-zinc-500'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Body Model */}
      <div
        className="flex justify-center px-4 py-2 relative"
        ref={modelRef}
        onPointerMove={handleModelPointerMove}
        onPointerLeave={handleModelPointerLeave}
      >
        <Model
          data={modelData}
          style={{ width: '16rem', padding: '1rem' }}
          onClick={handleModelClick}
          type={view}
          bodyColor="#1f2937"
          highlightedColors={HIGHLIGHT_COLORS}
        />
        <HoverTooltip info={hoverInfo} />
      </div>

      <NeonLegend />

      <p className="text-center text-[0.6rem] text-zinc-600 mb-3">Tap a muscle to see your level & how to progress</p>

      <MuscleCards muscles={levels} onSelect={(muscle) => {
        const data = levels.find((m) => m.muscle === muscle);
        if (data) setDetailMuscle(data);
      }} />

      <AnimatePresence>
        {detailMuscle && (
          <MuscleDetailPanel muscle={detailMuscle} onClose={() => setDetailMuscle(null)} />
        )}
      </AnimatePresence>
    </div>
  );
}
