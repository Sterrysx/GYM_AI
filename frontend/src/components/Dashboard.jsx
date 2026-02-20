import { useState, useEffect, useCallback } from 'react';
import {
  Scale, Activity, Dumbbell, Loader2,
  TrendingDown, TrendingUp, Minus, Footprints, Flame, Moon,
  Target, Settings2, X, Check,
} from 'lucide-react';
import { fetchMetrics, fetchTargets, updateTargets } from '../api/client';
import {
  ComposedChart, BarChart,
  Line, Area, Bar,
  XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';

// ── Colour palette ────────────────────────────────────────────────────────────
const C = {
  cyan:    '#22d3ee',
  purple:  '#a78bfa',
  orange:  '#fb923c',
  emerald: '#34d399',
  amber:   '#fbbf24',
  rose:    '#f472b6',
  sky:     '#38bdf8',
  indigo:  '#818cf8',
};

// ── Shared axis / grid props (font bumped to 11 and more left room) ─────────
const xProps = {
  tick: { fill: '#a1a1aa', fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: '#3f3f46' },
};
const yProps = (orientation = 'left', width = 44) => ({
  orientation,
  tick: { fill: '#a1a1aa', fontSize: 11 },
  tickLine: false,
  axisLine: false,
  width,
});
const gridProps = { strokeDasharray: '3 3', stroke: '#27272a' };
const legendProps = { wrapperStyle: { fontSize: '0.7rem', color: '#a1a1aa' }, iconType: 'circle', iconSize: 8 };

// ── Helpers ───────────────────────────────────────────────────────────────────
const SHORT_DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
/**
 * Format a YYYY-MM-DD or DD-MM-YYYY date string.
 * When dataLen ≤ 7, returns "Mon 16"; otherwise returns the raw date.
 */
const fmtXDate = (dateStr, dataLen) => {
  if (!dateStr) return '';
  if (dataLen > 7) return dateStr;
  // Try to parse as a Date — handles YYYY-MM-DD directly
  const d = new Date(dateStr + 'T00:00:00');
  if (isNaN(d)) return dateStr;
  return `${SHORT_DAYS[d.getDay()]} ${d.getDate()}`;
};

/** Convert decimal hours to "Xh Ym" */
const fmtHM = (hrs) => {
  if (hrs == null) return '—';
  const h = Math.floor(hrs);
  const m = Math.round((hrs - h) * 60);
  return `${h}h ${m}m`;
};
/** Convert minutes to "Xh Ym" */
const fmtMinHM = (mins) => {
  if (mins == null) return '—';
  const m = Math.round(mins);
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return h > 0 ? `${h}h ${rm}m` : `${rm}m`;
};

// ── Time-range button bar ─────────────────────────────────────────────────────
const RANGES = [
  { key: 'lifetime', label: 'All' },
  { key: 'month',    label: '30 d' },
  { key: 'week',     label: '7 d' },
  { key: 'day',      label: 'Today' },
];

function RangeBar({ value, onChange }) {
  return (
    <div className="flex gap-1 px-1">
      {RANGES.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={`flex-1 py-1.5 rounded-lg text-[0.65rem] font-semibold transition-all cursor-pointer ${
            value === key ? 'bg-zinc-800 text-zinc-200' : 'text-zinc-500 active:bg-zinc-900'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

// ── Chart card wrapper ────────────────────────────────────────────────────────
function ChartCard({ title, children }) {
  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl pt-4 pb-2 overflow-hidden">
      <p className="text-[0.6rem] text-zinc-500 uppercase tracking-widest font-semibold px-4 mb-3">
        {title}
      </p>
      {children}
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────
function Empty({ label }) {
  return (
    <div className="flex items-center justify-center h-32 text-zinc-600 text-xs">
      No {label} data yet
    </div>
  );
}

// ── Dark tooltip ──────────────────────────────────────────────────────────────
const HOUR_KEYS = new Set(['Total (hrs)', 'Sleep_Total_Hrs']);

function DarkTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-zinc-900/95 border border-zinc-700 rounded-lg px-3 py-2 text-xs shadow-2xl backdrop-blur">
      <p className="text-zinc-400 font-semibold mb-1.5">{label}</p>
      {payload.map((e, i) => {
        let display = e.value;
        if (HOUR_KEYS.has(e.name) && typeof display === 'number') {
          display = fmtHM(display);
        } else if (typeof display === 'number') {
          display = display.toLocaleString();
        }
        return (
          <p key={i} className="flex items-center gap-2 leading-5">
            <span className="inline-block w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: e.color }} />
            <span className="text-zinc-400">{e.name}:</span>
            <span className="font-bold text-white ml-auto pl-3">{display}</span>
          </p>
        );
      })}
    </div>
  );
}

// ── Summary metric card ───────────────────────────────────────────────────────
function MetricCard({ icon: Icon, label, value, unit, color, delta, sub }) {
  const dir = delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat';
  const TrendIcon = dir === 'up' ? TrendingUp : dir === 'down' ? TrendingDown : Minus;
  const tc = dir === 'up' ? 'text-rose-400' : dir === 'down' ? 'text-emerald-400' : 'text-zinc-600';
  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl px-2.5 py-2.5 flex items-center gap-2 min-w-0 overflow-hidden">
      <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
        style={{ backgroundColor: `${color}18` }}>
        <Icon size={16} style={{ color }} />
      </div>
      <div className="min-w-0 flex-1 overflow-hidden">
        <p className="text-[0.55rem] text-zinc-500 uppercase tracking-widest truncate">{label}</p>
        <div className="flex items-baseline gap-1">
          <span className="text-lg font-black leading-none" style={{ color }}>{value ?? '—'}</span>
          {unit && <span className="text-[0.6rem] text-zinc-500">{unit}</span>}
        </div>
        {sub && <p className="text-[0.5rem] text-zinc-600 mt-0.5 truncate">{sub}</p>}
      </div>
      {delta != null && (
        <div className={`flex items-center gap-0.5 ${tc} shrink-0`}>
          <TrendIcon size={12} />
          <span className="text-[0.6rem] font-bold">{Math.abs(delta).toFixed(1)}</span>
        </div>
      )}
    </div>
  );
}

// ── Target edit modal ─────────────────────────────────────────────────────────
function TargetModal({ targets, onSave, onClose }) {
  const [wt, setWt] = useState(targets.weight_kg);
  const [bf, setBf] = useState(targets.bodyfat_pct);
  const [mu, setMu] = useState(targets.muscle_kg);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await onSave({ weight_kg: +wt, bodyfat_pct: +bf, muscle_kg: +mu });
      onClose();
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-6"
         onClick={onClose}>
      <div className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-xs p-5 space-y-4"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-zinc-200 flex items-center gap-2"><Target size={16} className="text-sky-400" /> Set Targets</h2>
          <button onClick={onClose} className="text-zinc-500 cursor-pointer"><X size={18} /></button>
        </div>
        {[
          { label: 'Weight (kg)', val: wt, set: setWt, step: 0.5 },
          { label: 'Body Fat (%)', val: bf, set: setBf, step: 0.5 },
          { label: 'Muscle (kg)', val: mu, set: setMu, step: 0.5 },
        ].map(({ label, val, set, step }) => (
          <div key={label}>
            <label className="text-[0.6rem] text-zinc-500 uppercase tracking-widest">{label}</label>
            <input
              type="number" step={step} value={val}
              onChange={(e) => set(e.target.value)}
              className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-sky-500"
            />
          </div>
        ))}
        <button onClick={save} disabled={saving}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-sky-500 text-black text-xs font-bold uppercase tracking-wide cursor-pointer disabled:opacity-50">
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
          {saving ? 'Saving…' : 'Save Targets'}
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
export default function Dashboard() {
  const [bodyComp, setBodyComp]       = useState([]);
  const [appleHealth, setAppleHealth] = useState([]);
  const [targets, setTargets]         = useState({ weight_kg: 67.5, bodyfat_pct: 13, muscle_kg: 58 });
  const [range, setRange]             = useState('lifetime');
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);
  const [showTargetModal, setShowTargetModal] = useState(false);

  const loadData = useCallback(async (r) => {
    setLoading(true); setError(null);
    try {
      const res = await fetchMetrics(r);
      setBodyComp(res.body_comp ?? []);
      setAppleHealth(res.apple_health ?? []);
      if (res.targets) setTargets(res.targets);
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { loadData(range); }, [range, loadData]);

  const handleRangeChange = (r) => setRange(r);

  const handleSaveTargets = async (t) => {
    await updateTargets(t);
    setTargets(t);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-zinc-500 text-sm">
        <Loader2 size={18} className="animate-spin" /> Loading metrics…
      </div>
    );
  }
  if (error) {
    return <div className="text-center py-24 text-red-400 text-sm px-6">{error}</div>;
  }

  const latestB = bodyComp.at(-1)    ?? {};
  const prevB   = bodyComp.at(-2)    ?? null;
  const latestA = appleHealth.at(-1) ?? {};

  const d = (key) => prevB ? (latestB[key] ?? 0) - (prevB[key] ?? 0) : null;

  // Common chart margins (more room on left)
  const cMargin = { top: 4, right: 8, bottom: 0, left: -4 };

  return (
    <div className="px-3 pt-4 pb-16 space-y-3 overflow-x-hidden">

      {/* ── Time range selector ── */}
      <RangeBar value={range} onChange={handleRangeChange} />

      {/* ══ TARGETS ══ */}
      <div className="flex items-center justify-between px-1 pt-1">
        <p className="text-[0.6rem] text-zinc-600 uppercase tracking-widest font-bold">Targets</p>
        <button onClick={() => setShowTargetModal(true)}
          className="flex items-center gap-1 text-[0.6rem] text-sky-400 font-semibold cursor-pointer active:opacity-60">
          <Settings2 size={12} /> Edit
        </button>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <MetricCard icon={Scale}    label="Weight"   value={targets.weight_kg}   unit="kg" color={C.cyan}    delta={null} sub={`Current: ${latestB.Weight_kg ?? '—'} kg`} />
        <MetricCard icon={Activity} label="Body Fat" value={targets.bodyfat_pct} unit="%"  color={C.purple}  delta={null} sub={`Current: ${latestB.BodyFat_pct ?? '—'}%`} />
        <MetricCard icon={Dumbbell} label="Muscle"   value={targets.muscle_kg}   unit="kg" color={C.emerald} delta={null} sub={`Current: ${latestB.MuscleMass_kg ?? '—'} kg`} />
      </div>

      {/* ══ BODY COMPOSITION ══ */}
      <p className="text-[0.6rem] text-zinc-600 uppercase tracking-widest font-bold px-1 pt-2">Body Composition</p>

      <div className="grid grid-cols-3 gap-2">
        <MetricCard icon={Scale}    label="Weight"   value={latestB.Weight_kg}     unit="kg" color={C.cyan}    delta={d('Weight_kg')} />
        <MetricCard icon={Activity} label="Body Fat" value={latestB.BodyFat_pct}   unit="%"  color={C.purple}  delta={d('BodyFat_pct')} />
        <MetricCard icon={Dumbbell} label="Muscle"   value={latestB.MuscleMass_kg} unit="kg" color={C.emerald} delta={d('MuscleMass_kg')} />
      </div>

      {/* Chart — Weight Progress to Target */}
      <ChartCard title="Weight → Target">
        {bodyComp.length === 0 ? <Empty label="weight" /> : (
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={bodyComp} margin={cMargin}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="Date" {...xProps} tickFormatter={(v) => fmtXDate(v, bodyComp.length)} />
              <YAxis {...yProps('left', 44)} domain={['dataMin - 2', 'dataMax + 2']} />
              <Tooltip content={<DarkTooltip />} allowEscapeViewBox={{ x: false, y: false }} />
              <ReferenceLine y={targets.weight_kg} stroke={C.cyan} strokeDasharray="6 3" strokeOpacity={0.5} label={{ value: `Target ${targets.weight_kg}kg`, position: 'insideTopLeft', fill: C.cyan, fontSize: 9, fontWeight: 600, opacity: 0.7 }} />
              <Area type="monotone" dataKey="Weight_kg" name="Weight (kg)" stroke={C.cyan} strokeWidth={2.5} fill={C.cyan} fillOpacity={0.06} dot={{ r: 3, fill: C.cyan, strokeWidth: 0 }} activeDot={{ r: 5 }} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      {/* Chart — Body Fat Progress to Target */}
      <ChartCard title="Body Fat → Target">
        {bodyComp.length === 0 ? <Empty label="body fat" /> : (
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={bodyComp} margin={cMargin}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="Date" {...xProps} tickFormatter={(v) => fmtXDate(v, bodyComp.length)} />
              <YAxis {...yProps('left', 44)} domain={['dataMin - 2', 'dataMax + 2']} />
              <Tooltip content={<DarkTooltip />} allowEscapeViewBox={{ x: false, y: false }} />
              <ReferenceLine y={targets.bodyfat_pct} stroke={C.purple} strokeDasharray="6 3" strokeOpacity={0.5} label={{ value: `Target ${targets.bodyfat_pct}%`, position: 'insideTopLeft', fill: C.purple, fontSize: 9, fontWeight: 600, opacity: 0.7 }} />
              <Area type="monotone" dataKey="BodyFat_pct" name="Body Fat (%)" stroke={C.purple} strokeWidth={2.5} fill={C.purple} fillOpacity={0.06} dot={{ r: 3, fill: C.purple, strokeWidth: 0 }} activeDot={{ r: 5 }} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      {/* Chart — Muscle Progress to Target */}
      <ChartCard title="Muscle Mass → Target">
        {bodyComp.length === 0 ? <Empty label="muscle" /> : (
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={bodyComp} margin={cMargin}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="Date" {...xProps} tickFormatter={(v) => fmtXDate(v, bodyComp.length)} />
              <YAxis {...yProps('left', 44)} domain={['dataMin - 2', 'dataMax + 2']} />
              <Tooltip content={<DarkTooltip />} allowEscapeViewBox={{ x: false, y: false }} />
              <ReferenceLine y={targets.muscle_kg} stroke={C.emerald} strokeDasharray="6 3" strokeOpacity={0.5} label={{ value: `Target ${targets.muscle_kg}kg`, position: 'insideBottomLeft', fill: C.emerald, fontSize: 9, fontWeight: 600, opacity: 0.7 }} />
              <Area type="monotone" dataKey="MuscleMass_kg" name="Muscle (kg)" stroke={C.emerald} strokeWidth={2.5} fill={C.emerald} fillOpacity={0.06} dot={{ r: 3, fill: C.emerald, strokeWidth: 0 }} activeDot={{ r: 5 }} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      {/* ══ ACTIVITY ══ */}
      <p className="text-[0.6rem] text-zinc-600 uppercase tracking-widest font-bold px-1 pt-2">Activity</p>

      <div className="grid grid-cols-3 gap-2">
        <MetricCard icon={Footprints} label="Steps"    value={latestA.Steps?.toLocaleString()} unit="steps" color={C.orange} delta={null} />
        <MetricCard icon={Flame}      label="Active"   value={latestA.Active_Kcal}              unit="kcal"  color={C.rose}   delta={null} />
        <MetricCard icon={Activity}   label="Distance" value={latestA.Distance_Km?.toFixed(3)}  unit="km"    color={C.amber}  delta={null} />
      </div>

      {/* Chart — Steps */}
      <ChartCard title="Steps">
        {appleHealth.length === 0 ? <Empty label="steps" /> : (
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={appleHealth} margin={cMargin}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="Date" {...xProps} tickFormatter={(v) => fmtXDate(v, appleHealth.length)} />
              <YAxis {...yProps('left', 48)} tickFormatter={(v) => v >= 1000 ? `${(v/1000).toFixed(1)}k` : v} />
              <Tooltip content={<DarkTooltip />} allowEscapeViewBox={{ x: false, y: false }} />
              <Area type="monotone" dataKey="Steps" name="Steps" stroke={C.orange} strokeWidth={2} fill={C.orange} fillOpacity={0.1} dot={{ r: 3, fill: C.orange, strokeWidth: 0 }} activeDot={{ r: 5 }} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      {/* Chart — Distance */}
      <ChartCard title="Distance (km)">
        {appleHealth.length === 0 ? <Empty label="distance" /> : (
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={appleHealth} margin={cMargin}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="Date" {...xProps} tickFormatter={(v) => fmtXDate(v, appleHealth.length)} />
              <YAxis {...yProps('left', 48)} tickFormatter={(v) => v.toFixed(2)} />
              <Tooltip content={<DarkTooltip />} allowEscapeViewBox={{ x: false, y: false }} />
              <Area type="monotone" dataKey="Distance_Km" name="Distance (km)" stroke={C.amber} strokeWidth={2.5} fill={C.amber} fillOpacity={0.08} dot={{ r: 3, fill: C.amber, strokeWidth: 0 }} activeDot={{ r: 5 }} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      {/* Chart — Energy Burn (lines) */}
      <ChartCard title="Energy Burn (kcal)">
        {appleHealth.length === 0 ? <Empty label="energy" /> : (
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={appleHealth} margin={cMargin}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="Date" {...xProps} tickFormatter={(v) => fmtXDate(v, appleHealth.length)} />
              <YAxis {...yProps('left', 48)} />
              <Tooltip content={<DarkTooltip />} allowEscapeViewBox={{ x: false, y: false }} />
              <Legend {...legendProps} />
              <Area type="monotone" dataKey="Active_Kcal"  name="Active (kcal)"  stroke={C.rose}   strokeWidth={2} fill={C.rose}   fillOpacity={0.08} dot={{ r: 3, fill: C.rose,   strokeWidth: 0 }} activeDot={{ r: 5 }} />
              <Line type="monotone" dataKey="Resting_Kcal" name="Resting (kcal)" stroke={C.indigo} strokeWidth={2} strokeDasharray="5 3" dot={{ r: 2, fill: C.indigo, strokeWidth: 0 }} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      {/* ══ SLEEP ══ */}
      <p className="text-[0.6rem] text-zinc-600 uppercase tracking-widest font-bold px-1 pt-2">Sleep</p>

      {/* 5 sleep metric cards: Total, Deep, REM, Core, Awake — all in Xh Ym */}
      <div className="grid grid-cols-3 gap-2">
        <MetricCard icon={Moon}     label="Total" value={fmtHM(latestA.Sleep_Total_Hrs)} unit="" color={C.indigo} delta={null} />
        <MetricCard icon={Activity} label="Deep"  value={fmtMinHM(latestA.Sleep_Deep_Min)} unit="" color={C.cyan}   delta={null} />
        <MetricCard icon={Activity} label="REM"   value={fmtMinHM(latestA.Sleep_REM_Min)}  unit="" color={C.purple} delta={null} />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <MetricCard icon={Activity} label="Core"  value={fmtMinHM(latestA.Sleep_Core_Min)}  unit="" color={C.sky}  delta={null} />
        <MetricCard icon={Activity} label="Awake" value={fmtMinHM(latestA.Sleep_Awake_Min)} unit="" color={C.rose} delta={null} />
      </div>

      {/* Chart — Apple-style horizontal sleep stages */}
      <ChartCard title="Sleep Stages">
        {appleHealth.length === 0 ? <Empty label="sleep" /> : (
          <ResponsiveContainer width="100%" height={Math.max(180, appleHealth.length * 32 + 40)}>
            <BarChart data={[...appleHealth].reverse()} layout="vertical" margin={{ top: 4, right: 8, bottom: 0, left: 2 }}>
              <CartesianGrid {...gridProps} horizontal={false} />
              <XAxis type="number" tick={{ fill: '#a1a1aa', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#3f3f46' }} unit="m" />
              <YAxis type="category" dataKey="Date" tick={{ fill: '#a1a1aa', fontSize: 10 }} tickLine={false} axisLine={false} width={58} />
              <Tooltip content={<DarkTooltip />} allowEscapeViewBox={{ x: false, y: false }} />
              <Legend {...legendProps} />
              <Bar dataKey="Sleep_Deep_Min"  name="Deep"  stackId="sleep" fill={C.indigo} fillOpacity={0.9} radius={0} />
              <Bar dataKey="Sleep_REM_Min"   name="REM"   stackId="sleep" fill={C.purple} fillOpacity={0.9} radius={0} />
              <Bar dataKey="Sleep_Core_Min"  name="Core"  stackId="sleep" fill={C.sky}    fillOpacity={0.7} radius={0} />
              <Bar dataKey="Sleep_Awake_Min" name="Awake" stackId="sleep" fill="#ef4444" fillOpacity={0.35} radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      {/* Chart — Total sleep trend */}
      <ChartCard title="Total Sleep">
        {appleHealth.length === 0 ? <Empty label="sleep" /> : (
          <ResponsiveContainer width="100%" height={180}>
            <ComposedChart data={appleHealth} margin={cMargin}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="Date" {...xProps} tickFormatter={(v) => fmtXDate(v, appleHealth.length)} />
              <YAxis {...yProps('left', 36)} domain={[0, 12]} tickFormatter={(v) => `${v}h`} />
              <Tooltip content={<DarkTooltip />} allowEscapeViewBox={{ x: false, y: false }} />
              <ReferenceLine y={8} stroke={C.emerald} strokeDasharray="6 3" strokeOpacity={0.35} label={{ value: '8h goal', position: 'insideTopLeft', fill: C.emerald, fontSize: 9, fontWeight: 600, opacity: 0.6 }} />
              <Area type="monotone" dataKey="Sleep_Total_Hrs" name="Total (hrs)" stroke={C.emerald} strokeWidth={2.5} fill={C.emerald} fillOpacity={0.08} dot={{ r: 3, fill: C.emerald, strokeWidth: 0 }} activeDot={{ r: 5 }} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      {/* ── Latest body detail table ── */}
      {Object.keys(latestB).length > 0 && (
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3">
          <p className="text-[0.6rem] text-zinc-500 uppercase tracking-widest font-semibold mb-2.5">
            Latest Body Metrics — {latestB.Date}
          </p>
          <div className="grid grid-cols-3 gap-x-4 gap-y-2.5">
            {[
              ['BMI',           latestB.BMI],
              ['Water',         latestB.Water_pct       != null ? `${latestB.Water_pct}%`              : '—'],
              ['Bone Mass',     latestB.BoneMass_kg     != null ? `${latestB.BoneMass_kg} kg`           : '—'],
              ['BMR',           latestB.BMR_kcal        != null ? `${latestB.BMR_kcal} kcal`            : '—'],
              ['Visceral Fat',  latestB.VisceralFat],
              ['Subcut. Fat',   latestB.SubcutaneousFat_pct != null ? `${latestB.SubcutaneousFat_pct}%` : '—'],
              ['Protein',       latestB.Protein_pct     != null ? `${latestB.Protein_pct}%`             : '—'],
              ['Metabolic Age', latestB.MetabolicAge],
            ].map(([label, val]) => (
              <div key={label}>
                <p className="text-[0.5rem] text-zinc-600 uppercase tracking-wider">{label}</p>
                <p className="text-sm font-bold text-zinc-300">{val ?? '—'}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Target edit modal ── */}
      {showTargetModal && (
        <TargetModal targets={targets} onSave={handleSaveTargets} onClose={() => setShowTargetModal(false)} />
      )}
    </div>
  );
}
