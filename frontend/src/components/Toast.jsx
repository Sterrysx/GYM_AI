/**
 * Fixed-position toast notification with auto-dismiss.
 */
export default function Toast({ msg, isError, visible }) {
  return (
    <div
      className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-6 py-2.5 rounded-xl text-sm font-semibold border transition-opacity duration-300 pointer-events-none select-none ${
        visible ? 'opacity-100' : 'opacity-0'
      } ${
        isError
          ? 'bg-zinc-950 border-red-400 text-red-400'
          : 'bg-zinc-950 border-emerald-400 text-emerald-400'
      }`}
    >
      {msg}
    </div>
  );
}
