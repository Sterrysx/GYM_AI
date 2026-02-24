/**
 * MuscleMap — Interactive anatomical body map with RPG-style muscle levels.
 * Renders front + back SVG body outlines, colours each muscle region by level,
 * and opens a detail panel on tap/click.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { Loader2, Swords, Star, ChevronRight, X, TrendingUp, Dumbbell, Trophy, Target, Zap } from 'lucide-react';
import { fetchMuscleLevels } from '../api/client';

// ── Level colours (RPG tiers) ────────────────────────────────────────────────
const LEVEL_COLORS = [
  { bg: 'rgba(113,113,122,0.25)', border: '#52525b', text: 'text-zinc-400', tier: 'Untrained', tierColor: 'text-zinc-500' },  // 0
  { bg: 'rgba(113,113,122,0.4)',  border: '#71717a', text: 'text-zinc-300', tier: 'Novice',    tierColor: 'text-zinc-400' },  // 1
  { bg: 'rgba(34,197,94,0.25)',   border: '#22c55e', text: 'text-emerald-400', tier: 'Beginner', tierColor: 'text-emerald-400' },  // 2
  { bg: 'rgba(34,197,94,0.4)',    border: '#16a34a', text: 'text-emerald-300', tier: 'Trained',  tierColor: 'text-emerald-300' },  // 3
  { bg: 'rgba(59,130,246,0.35)',  border: '#3b82f6', text: 'text-blue-400', tier: 'Intermediate', tierColor: 'text-blue-400' },  // 4
  { bg: 'rgba(59,130,246,0.5)',   border: '#2563eb', text: 'text-blue-300', tier: 'Advanced',  tierColor: 'text-blue-300' },  // 5
  { bg: 'rgba(168,85,247,0.4)',   border: '#a855f7', text: 'text-purple-400', tier: 'Expert',  tierColor: 'text-purple-400' },  // 6
  { bg: 'rgba(168,85,247,0.55)',  border: '#9333ea', text: 'text-purple-300', tier: 'Elite',   tierColor: 'text-purple-300' },  // 7
  { bg: 'rgba(245,158,11,0.45)',  border: '#f59e0b', text: 'text-amber-400', tier: 'Master',   tierColor: 'text-amber-400' },  // 8
  { bg: 'rgba(245,158,11,0.6)',   border: '#d97706', text: 'text-amber-300', tier: 'Grandmaster', tierColor: 'text-amber-300' },  // 9
  { bg: 'rgba(239,68,68,0.5)',    border: '#ef4444', text: 'text-red-400', tier: 'Legend',     tierColor: 'text-red-400' },  // 10+
];

function getLevelStyle(level) {
  return LEVEL_COLORS[Math.min(level, LEVEL_COLORS.length - 1)];
}

// ── Muscle-group → SVG element ids mapping ───────────────────────────────────
// Some muscles have left+right paths, some appear on both views
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


// ── XP Bar ───────────────────────────────────────────────────────────────────
function XpBar({ pct, level, tierColor }) {
  return (
    <div className="relative w-full h-3 bg-zinc-800 rounded-full overflow-hidden border border-zinc-700">
      <div
        className="absolute inset-y-0 left-0 rounded-full transition-all duration-700"
        style={{
          width: `${Math.min(pct, 100)}%`,
          background: `linear-gradient(90deg, ${getLevelStyle(level).border}88, ${getLevelStyle(level).border})`,
        }}
      />
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-[0.5rem] font-bold text-white/70 drop-shadow">{Math.round(pct)}%</span>
      </div>
    </div>
  );
}


// ── Muscle Detail Panel (slide-up sheet) ─────────────────────────────────────
function MuscleDetailPanel({ muscle, onClose }) {
  if (!muscle) return null;
  const style = getLevelStyle(muscle.level);
  const targetStyle = getLevelStyle(muscle.target_level);
  const xpRemaining = Math.max(0, muscle.xp_for_next - muscle.xp_in_level);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center" onClick={onClose}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      {/* Panel */}
      <div
        className="relative w-full max-w-lg bg-zinc-900 border-t border-zinc-700 rounded-t-2xl p-5 pb-8 animate-slideUp"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close */}
        <button onClick={onClose} className="absolute top-3 right-3 text-zinc-500 active:text-zinc-300 cursor-pointer p-1">
          <X size={18} />
        </button>

        {/* Handle */}
        <div className="w-10 h-1 bg-zinc-700 rounded-full mx-auto mb-4" />

        {/* Title */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center border-2"
            style={{ borderColor: style.border, background: style.bg }}>
            <span className="text-lg font-black" style={{ color: style.border }}>{muscle.level}</span>
          </div>
          <div>
            <h3 className="text-lg font-bold">{muscle.display_name}</h3>
            <div className="flex items-center gap-2 text-xs">
              <span className={`font-semibold ${style.tierColor}`}>{style.tier}</span>
              <ChevronRight size={10} className="text-zinc-600" />
              <span className="text-zinc-500">Target: <span className={`font-semibold ${targetStyle.tierColor}`}>Lv.{muscle.target_level} {targetStyle.tier}</span></span>
            </div>
          </div>
        </div>

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

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-2 mb-4">
          <div className="bg-zinc-800/60 border border-zinc-700/50 rounded-lg p-2.5 text-center">
            <Zap size={12} className="mx-auto mb-1 text-amber-400" />
            <div className="text-sm font-bold">{Math.round(muscle.xp).toLocaleString()}</div>
            <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">Total XP</div>
          </div>
          <div className="bg-zinc-800/60 border border-zinc-700/50 rounded-lg p-2.5 text-center">
            <Target size={12} className="mx-auto mb-1 text-sky-400" />
            <div className="text-sm font-bold">{Math.round(xpRemaining).toLocaleString()}</div>
            <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">XP to Next</div>
          </div>
          <div className="bg-zinc-800/60 border border-zinc-700/50 rounded-lg p-2.5 text-center">
            <Trophy size={12} className="mx-auto mb-1 text-purple-400" />
            <div className="text-sm font-bold">{muscle.target_level}</div>
            <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">Target Lv</div>
          </div>
        </div>

        {/* How to level up hint */}
        {xpRemaining > 0 && (
          <div className="bg-zinc-800/40 border border-zinc-700/30 rounded-lg p-3 mb-4">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-sky-400 mb-1">
              <TrendingUp size={12} />
              How to level up
            </div>
            <p className="text-[0.7rem] text-zinc-400 leading-relaxed">
              You need <span className="text-sky-300 font-semibold">{Math.round(xpRemaining).toLocaleString()} more XP</span> to reach Level {muscle.level + 1}.
              {' '}XP = weight × reps. For example, do <span className="text-zinc-200 font-semibold">{Math.ceil(xpRemaining / 10)} reps at 10kg</span> or <span className="text-zinc-200 font-semibold">{Math.ceil(xpRemaining / 20)} reps at 20kg</span>.
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
                <div key={ex.exercise_id} className="flex items-center justify-between bg-zinc-800/40 rounded-lg px-3 py-2">
                  <span className="text-xs font-medium truncate flex-1">{ex.name}</span>
                  <div className="flex items-center gap-3 shrink-0 text-xs text-zinc-400">
                    <span>{ex.sets} sets</span>
                    <span>{ex.reps} reps</span>
                    <span className="text-zinc-300 font-semibold">{Math.round(ex.volume).toLocaleString()} XP</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-zinc-600 text-center py-3">No exercises logged for this muscle yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}


// ── Body SVG Viewer ──────────────────────────────────────────────────────────
function BodyView({ svgUrl, muscleLevels, view, onMuscleClick, selectedMuscle }) {
  const containerRef = useRef(null);
  const [svgLoaded, setSvgLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
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

  // Color muscles whenever data or SVG changes
  useEffect(() => {
    if (!svgLoaded || !containerRef.current) return;
    const svgEl = containerRef.current.querySelector('svg');
    if (!svgEl) return;

    // Reset all regions
    svgEl.querySelectorAll('.muscle-region').forEach((el) => {
      el.style.fill = 'rgba(100,100,100,0.15)';
      el.style.stroke = '#666';
      el.style.strokeWidth = '0.8';
    });

    // Color by level
    for (const [muscle, ids] of Object.entries(MUSCLE_SVG_IDS)) {
      const pathIds = ids[view] || [];
      const data = muscleLevels.find((m) => m.muscle === muscle);
      if (!data) continue;
      const style = getLevelStyle(data.level);

      for (const pathId of pathIds) {
        const el = svgEl.getElementById(pathId);
        if (!el) continue;
        el.style.fill = style.bg;
        el.style.stroke = style.border;
        el.style.strokeWidth = selectedMuscle === muscle ? '2.5' : '1.2';
        el.style.cursor = 'pointer';
        el.style.filter = selectedMuscle === muscle ? `drop-shadow(0 0 6px ${style.border})` : '';

        // Click handler — use a closure to capture the muscle name
        el.onclick = (e) => {
          e.stopPropagation();
          onMuscleClick(muscle);
        };
      }
    }
  }, [svgLoaded, muscleLevels, view, selectedMuscle, onMuscleClick]);

  return (
    <div
      ref={containerRef}
      className="flex-1 flex items-center justify-center [&>svg]:max-h-[55vh] [&>svg]:w-auto"
    />
  );
}


// ── Level Legend ──────────────────────────────────────────────────────────────
function LevelLegend() {
  return (
    <div className="flex flex-wrap gap-1.5 justify-center px-4 py-2">
      {LEVEL_COLORS.slice(0, 8).map((c, i) => (
        <div key={i} className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm border" style={{ background: c.bg, borderColor: c.border }} />
          <span className="text-[0.5rem] text-zinc-500">{i}</span>
        </div>
      ))}
    </div>
  );
}


// ── Muscle Level Summary Cards ───────────────────────────────────────────────
function MuscleCards({ muscles, onSelect }) {
  const sorted = [...muscles].sort((a, b) => b.level - a.level || b.xp - a.xp);
  return (
    <div className="grid grid-cols-2 gap-1.5 px-3 pb-4">
      {sorted.map((m) => {
        const style = getLevelStyle(m.level);
        const target = getLevelStyle(m.target_level);
        const atTarget = m.level >= m.target_level;
        return (
          <button
            key={m.muscle}
            onClick={() => onSelect(m.muscle)}
            className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded-lg px-2.5 py-2 text-left cursor-pointer active:bg-zinc-800 transition-colors"
          >
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center border shrink-0"
              style={{ borderColor: style.border, background: style.bg }}
            >
              <span className="text-xs font-black" style={{ color: style.border }}>{m.level}</span>
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[0.65rem] font-semibold truncate">{m.display_name}</div>
              <div className="flex items-center gap-1 mt-0.5">
                <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${m.xp_pct}%`,
                      background: style.border,
                    }}
                  />
                </div>
                {atTarget ? (
                  <Star size={8} className="text-amber-400 shrink-0" fill="currentColor" />
                ) : (
                  <span className="text-[0.45rem] text-zinc-600 shrink-0">→{m.target_level}</span>
                )}
              </div>
            </div>
          </button>
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
    const data = levels.find((m) => m.muscle === muscle);
    if (data) setDetailMuscle(data);
  }, [levels]);

  const totalLevel = levels.reduce((s, m) => s + m.level, 0);
  const totalXp = levels.reduce((s, m) => s + m.xp, 0);

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
      {/* Header stats */}
      <div className="px-4 pt-3 pb-2">
        <div className="flex items-center gap-2 mb-2">
          <Swords size={16} className="text-purple-400" />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">Muscle Map</h2>
        </div>
        <div className="flex gap-3 mb-3">
          <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-2 text-center">
            <div className="text-lg font-black text-purple-400">{totalLevel}</div>
            <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">Total Level</div>
          </div>
          <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-2 text-center">
            <div className="text-lg font-black text-amber-400">{Math.round(totalXp).toLocaleString()}</div>
            <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">Total XP</div>
          </div>
          <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-2 text-center">
            <div className="text-lg font-black text-sky-400">{levels.length}</div>
            <div className="text-[0.55rem] text-zinc-500 uppercase tracking-wide">Muscles</div>
          </div>
        </div>
      </div>

      {/* View Toggle */}
      <div className="flex items-center justify-center gap-2 px-4 mb-2">
        <button
          onClick={() => setView('front')}
          className={`px-4 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wide transition-all cursor-pointer ${
            view === 'front'
              ? 'bg-purple-500/20 border border-purple-500/40 text-purple-400'
              : 'bg-zinc-800/60 border border-zinc-700/50 text-zinc-500'
          }`}
        >
          Front
        </button>
        <button
          onClick={() => setView('back')}
          className={`px-4 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wide transition-all cursor-pointer ${
            view === 'back'
              ? 'bg-purple-500/20 border border-purple-500/40 text-purple-400'
              : 'bg-zinc-800/60 border border-zinc-700/50 text-zinc-500'
          }`}
        >
          Back
        </button>
      </div>

      {/* Body SVG */}
      <div className="flex justify-center px-4 py-2 min-h-[50vh]">
        <BodyView
          svgUrl={view === 'front' ? '/body_front.svg' : '/body_back.svg'}
          muscleLevels={levels}
          view={view}
          onMuscleClick={handleMuscleClick}
          selectedMuscle={selectedMuscle}
        />
      </div>

      {/* Legend */}
      <LevelLegend />

      {/* Tap hint */}
      <p className="text-center text-[0.6rem] text-zinc-600 mb-3">Tap a muscle on the body or card below to see details</p>

      {/* Muscle Cards Grid */}
      <MuscleCards muscles={levels} onSelect={handleMuscleClick} />

      {/* Detail panel */}
      <MuscleDetailPanel muscle={detailMuscle} onClose={() => { setDetailMuscle(null); setSelectedMuscle(null); }} />
    </div>
  );
}
