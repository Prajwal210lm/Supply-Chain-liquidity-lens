import Link from "next/link";

export default function NotFound() {
  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center text-center px-6 relative overflow-hidden"
      style={{ background: "linear-gradient(160deg, var(--ink-950) 0%, var(--navy-900) 50%, var(--navy-800) 100%)" }}
    >
      <div className="absolute inset-0 tx-dotgrid pointer-events-none" />

      <div className="relative z-10 max-w-md">
        <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--gold-soft)]/75 mb-6">Not Found</p>
        <p className="font-display text-[96px] text-[var(--text-on-dark)] leading-none mb-4 tnum">404</p>
        <h1 className="font-display text-[24px] text-[var(--text-on-dark)] mb-4 leading-[1.3]">
          This SKU isn&apos;t in the portfolio.
        </h1>
        <p className="text-[14px] text-[var(--text-on-dark-secondary)] leading-[1.7] mb-8">
          The page you're looking for doesn't exist, or has moved. The diagnostic itself is still
          right where you left it.
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-6 py-3 text-[13px] font-semibold tracking-[0.06em] uppercase text-white
                     rounded-full cursor-pointer shadow-[var(--elev-3)] hover:shadow-[var(--elev-4)]
                     transition-[transform,box-shadow] duration-200 ease-out hover:-translate-y-0.5"
          style={{ background: "linear-gradient(180deg, var(--navy-700), var(--navy-800))" }}
        >
          Back to Liquidity Lens
        </Link>
      </div>
    </div>
  );
}
