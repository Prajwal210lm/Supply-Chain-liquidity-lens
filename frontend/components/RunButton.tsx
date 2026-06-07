"use client";

type Status = "idle" | "loading" | "done" | "error";

export default function RunButton({
  status,
  onClick,
}: {
  status: Status;
  onClick: () => void;
}) {
  const loading = status === "loading";
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="px-5 py-2 bg-gray-900 text-white text-sm font-medium tracking-wide uppercase
                 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-700 transition-colors"
    >
      {loading ? (
        <span className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 bg-white rounded-full animate-pulse" />
          Running pipeline…
        </span>
      ) : (
        "Run Diagnosis"
      )}
    </button>
  );
}
