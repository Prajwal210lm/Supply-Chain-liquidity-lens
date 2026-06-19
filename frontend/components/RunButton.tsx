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

  const base =
    "inline-flex items-center gap-2 px-5 py-2 text-[12.5px] font-semibold tracking-[0.06em] uppercase rounded-full " +
    "cursor-pointer transition-[transform,background-color,border-color,box-shadow] duration-200 ease-out " +
    "disabled:opacity-50 disabled:cursor-not-allowed";

  const ghost = "border border-white/20 text-white/85 hover:text-white hover:border-white/40 bg-white/5 hover:bg-white/10";

  if (variant === "ghost") {
    return (
      <button onClick={onClick} disabled={loading} className={`${base} ${ghost}`}>
        {loading ? <Spinner /> : "Run Diagnosis"}
      </button>
    );
  }

  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`${base} text-white hover:-translate-y-0.5`}
      style={{ background: "linear-gradient(180deg, var(--navy-700), var(--navy-800))", boxShadow: "var(--elev-2)" }}
    >
      {loading ? <Spinner /> : "Run Diagnosis"}
    </button>
  );
}

function Spinner() {
  return (
    <span className="flex items-center gap-2">
      <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
      Running…
    </span>
  );
}
