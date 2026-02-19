import { useState, useEffect } from 'react';
import { Scale, Activity, Dumbbell, Loader2, TrendingDown, TrendingUp, Minus } from 'lucide-react';
import { fetchMetrics } from '../api/client';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

/* ── Metric summary card ─────────────────────────────────────────────────── */
function MetricCard({ icon: Icon, label, value, unit, color, delta }) {
  const trend = delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat';
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor =
    trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-zinc-600';

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 flex items-center gap-3 flex-1 min-w-0">
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
        style={{ backgroundColor: `${color}15` }}
      >
        <Icon size={20} style={{ color }} />
      </div>
      <div className="min-w-0">
        <p className="text-[0.6rem] text-zinc-500 uppercase tracking-widest truncate">{label}</p>
        <div className="flex items-baseline gap-1.5">
          <span className="text-xl font-black leading-none" style={{ color }}>
            {value}
          </span>
          <span className="text-[0.65rem] text-zinc-500">{unit}</span>
        </div>
      </div>
      {delta !== null && delta !== undefined && (
        <div className={`ml-auto flex items-center gap-0.5 ${trendColor}`}>
          <TrendIcon size={13} />
          <span className="text-[0.6rem] font-bold">{Math.abs(delta).toFixed(1)}</span>
        </div>
      )}
    </div>
  );
}

/* ── Custom dark‑themed Recharts tooltip ─────────────────────────────────── */
function DarkTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-zinc-400 font-semibold mb-1">{label}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="flex items-center gap-2">
          <span
            className="inline-block w-2 h-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-zinc-300">{entry.name}:</span>
          <span className="font-bold text-white">{entry.value}</span>
        </p>
      ))}
    </div>
  );
}

/* ── Main Dashboard component ────────────────────────────────────────────── */
export default function Dashboard() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetchMetrics();
        if (!cancelled) setRecords(res.data ?? []);
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail ?? err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  /* ── Loading & error states ── */
  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-zinc-500 text-sm">
        <Loader2 size={18} className="animate-spin" />
        Loading metrics…
      </div>
    );
  }
  if (error) {
    return <div className="text-center py-24 text-red-400 text-sm px-6">{error}</div>;
  }
  if (records.length === 0) {
    return (
      <div className="text-center py-24 text-zinc-500 text-sm">
        No body composition data yet. Run <span className="text-sky-400 font-mono">make log-weight</span> to start tracking.
      </div>
    );
  }

  /* ── Derived values ── */
  const latest = records[records.length - 1];
  const prev = records.length > 1 ? records[records.length - 2] : null;

  const weightDelta = prev ? latest.Weight_kg - prev.Weight_kg : null;
  const bfDelta = prev ? latest.BodyFat_pct - prev.BodyFat_pct : null;
  const mmDelta = prev ? latest.MuscleMass_kg - prev.MuscleMass_kg : null;

  return (
    <div className="px-3 pt-4 pb-10 space-y-3">
      {/* ── Summary Cards ── */}
      <div className="flex gap-2">
        <MetricCard
          icon={Scale}
          label="Weight"
          value={latest.Weight_kg}
          unit="kg"
          color="#38bdf8"
          delta={weightDelta}
        />
        <MetricCard
          icon={Activity}
          label="Body Fat"
          value={latest.BodyFat_pct}
          unit="%"
          color="#a78bfa"
          delta={bfDelta}
        />
        <MetricCard
          icon={Dumbbell}
          label="Muscle"
          value={latest.MuscleMass_kg}
          unit="kg"
          color="#34d399"
          delta={mmDelta}
        />
      </div>

      {/* ── Weight + Body Fat Chart ── */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl px-2 pt-4 pb-2">
        <p className="text-[0.65rem] text-zinc-500 uppercase tracking-widest font-semibold px-2 mb-3">
          Weight &amp; Body Fat Trend
        </p>
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={records} margin={{ top: 5, right: 8, bottom: 5, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis
              dataKey="Date"
              tick={{ fill: '#71717a', fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: '#3f3f46' }}
            />
            {/* Left axis — Weight */}
            <YAxis
              yAxisId="weight"
              orientation="left"
              domain={['dataMin - 1', 'dataMax + 1']}
              tick={{ fill: '#71717a', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              width={40}
            />
            {/* Right axis — Body Fat % */}
            <YAxis
              yAxisId="bf"
              orientation="right"
              domain={['dataMin - 1', 'dataMax + 1']}
              tick={{ fill: '#71717a', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              width={35}
            />
            <Tooltip content={<DarkTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: '0.65rem', color: '#a1a1aa' }}
              iconType="circle"
              iconSize={8}
            />

            {/* Weight line */}
            <Line
              yAxisId="weight"
              type="monotone"
              dataKey="Weight_kg"
              name="Weight (kg)"
              stroke="#38bdf8"
              strokeWidth={2.5}
              dot={{ r: 4, fill: '#38bdf8', strokeWidth: 0 }}
              activeDot={{ r: 6, stroke: '#38bdf8', strokeWidth: 2, fill: '#000' }}
            />

            {/* Body Fat area */}
            <Area
              yAxisId="bf"
              type="monotone"
              dataKey="BodyFat_pct"
              name="Body Fat (%)"
              stroke="#a78bfa"
              strokeWidth={2}
              fill="#a78bfa"
              fillOpacity={0.08}
              dot={{ r: 3, fill: '#a78bfa', strokeWidth: 0 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* ── Muscle Mass + BMR Chart ── */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl px-2 pt-4 pb-2">
        <p className="text-[0.65rem] text-zinc-500 uppercase tracking-widest font-semibold px-2 mb-3">
          Muscle Mass &amp; BMR
        </p>
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={records} margin={{ top: 5, right: 8, bottom: 5, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis
              dataKey="Date"
              tick={{ fill: '#71717a', fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: '#3f3f46' }}
            />
            <YAxis
              yAxisId="muscle"
              orientation="left"
              domain={['dataMin - 1', 'dataMax + 1']}
              tick={{ fill: '#71717a', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              width={40}
            />
            <YAxis
              yAxisId="bmr"
              orientation="right"
              domain={['dataMin - 20', 'dataMax + 20']}
              tick={{ fill: '#71717a', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              width={40}
            />
            <Tooltip content={<DarkTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: '0.65rem', color: '#a1a1aa' }}
              iconType="circle"
              iconSize={8}
            />

            <Line
              yAxisId="muscle"
              type="monotone"
              dataKey="MuscleMass_kg"
              name="Muscle (kg)"
              stroke="#34d399"
              strokeWidth={2.5}
              dot={{ r: 4, fill: '#34d399', strokeWidth: 0 }}
              activeDot={{ r: 6, stroke: '#34d399', strokeWidth: 2, fill: '#000' }}
            />
            <Line
              yAxisId="bmr"
              type="monotone"
              dataKey="BMR_kcal"
              name="BMR (kcal)"
              stroke="#fbbf24"
              strokeWidth={1.5}
              strokeDasharray="5 3"
              dot={{ r: 3, fill: '#fbbf24', strokeWidth: 0 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* ── Full metrics table (last entry) ── */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3">
        <p className="text-[0.65rem] text-zinc-500 uppercase tracking-widest font-semibold mb-2">
          Latest Reading — {latest.Date}
        </p>
        <div className="grid grid-cols-3 gap-x-4 gap-y-2">
          {[
            ['BMI', latest.BMI],
            ['Water', `${latest.Water_pct}%`],
            ['Bone Mass', `${latest.BoneMass_kg} kg`],
            ['BMR', `${latest.BMR_kcal} kcal`],
            ['Visceral Fat', latest.VisceralFat],
            ['Subcut. Fat', `${latest.SubcutaneousFat_pct}%`],
            ['Protein', `${latest.Protein_pct}%`],
            ['Metabolic Age', latest.MetabolicAge],
          ].map(([label, val]) => (
            <div key={label}>
              <p className="text-[0.55rem] text-zinc-600 uppercase tracking-wider">{label}</p>
              <p className="text-sm font-bold text-zinc-300">{val}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
