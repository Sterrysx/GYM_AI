/**
 * Row of 5 day buttons. Active day is visually highlighted.
 */
export default function DaySelector({ activeDay, onSelect }) {
  return (
    <div className="flex gap-1.5">
      {[1, 2, 3, 4, 5].map((d) => (
        <button
          key={d}
          onClick={() => onSelect(d)}
          className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all cursor-pointer ${
            d === activeDay
              ? 'bg-sky-400 text-black border border-sky-400'
              : 'bg-zinc-950 text-zinc-500 border border-zinc-800 active:bg-zinc-800'
          }`}
        >
          Day {d}
        </button>
      ))}
    </div>
  );
}
