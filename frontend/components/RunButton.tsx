"use client";

type Status = "idle" | "loading" | "done" | "error";

export default function RunButton({
  status,
  onClick,
  variant = "solid",
}: {
  status: Status;
  onClick: () => void;
  variant?: "solid" | "ghost";
}) {
  const loading = status === "loading";

  const solidClasses =
    "bg-[var(--navy-700)] hover:bg-[var(--navy-800)] text-white shadow-md hover:shadow-lg";
  const ghostClasses =
    "border border-white/30 text-white hover:bg-white/10 bg-transparent";

  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`px-5 py-2 text-sm font-semibold tracking-wide uppercase rounded-full
                  transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed
                  ${variant === "ghost" ? ghostClasses : solidClasses}`}
    >
      {loading ? (
        <span className="flex items-center gap-2">
          <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          Running…
        </span>
      ) : (
        "Run Diagnosis"
      )}
    </button>
  );
}
