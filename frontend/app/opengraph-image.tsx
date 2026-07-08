import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Generic serif/sans fallbacks rather than the bundled Fraunces/Inter web
// fonts — ImageResponse renders in an isolated Satori context that doesn't
// see next/font, and embedding font files here isn't worth the added
// complexity for a single static share image.
export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px",
          background: "linear-gradient(160deg, #060A12 0%, #0B1322 50%, #122036 100%)",
          fontFamily: "Georgia, serif",
        }}
      >
        {/* Dot-grid texture */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.06) 1.5px, transparent 1.5px)",
            backgroundSize: "28px 28px",
          }}
        />

        {/* Brandmark */}
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 36 }}>
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: 14,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "rgba(189,154,74,0.14)",
              border: "1px solid rgba(189,154,74,0.32)",
            }}
          >
            <div
              style={{
                width: 26,
                height: 26,
                borderRadius: "50%",
                border: "2.5px solid #D8BE80",
              }}
            />
          </div>
          <div
            style={{
              fontSize: 26,
              fontFamily: "Georgia, serif",
              color: "#F3F1EA",
              letterSpacing: "0.01em",
            }}
          >
            Liquidity Lens
          </div>
        </div>

        {/* Headline */}
        <div
          style={{
            fontSize: 60,
            color: "#F3F1EA",
            lineHeight: 1.15,
            maxWidth: 920,
            marginBottom: 28,
          }}
        >
          AED 21.2M sits trapped in this portfolio, right now.
        </div>

        <div
          style={{
            fontSize: 24,
            fontFamily: "Verdana, sans-serif",
            color: "rgba(243,241,234,0.72)",
            letterSpacing: "0.01em",
          }}
        >
          A working-capital diagnostic for GCC distributors — where cash is trapped, why, and what to release first.
        </div>
      </div>
    ),
    { ...size }
  );
}
