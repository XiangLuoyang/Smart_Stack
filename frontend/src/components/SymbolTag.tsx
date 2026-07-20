import { useEffect, useState } from "react";
import { useStore } from "../stores/useStore";

interface Props {
  code: string;
  showCode?: boolean;
  strongName?: boolean;
}

/** Render a stock as "company name" with the code subdued, loading the name on demand. */
export default function SymbolTag({ code, showCode = true, strongName = false }: Props) {
  const name = useStore((s) => s.symbolNames[code]);
  const loadSymbolNames = useStore((s) => s.loadSymbolNames);
  const [fallback, setFallback] = useState<string | null>(null);

  useEffect(() => {
    if (!code) return;
    if (!name) void loadSymbolNames([code]);
  }, [code, name, loadSymbolNames]);

  // Show resolved name; if backend lookup returns empty, keep code only (no "--").
  const display = name || fallback;
  if (!display) {
    // Asks backend once; if it comes back empty we just show the code.
    void loadSymbolNames([code]).then(() => {
      const resolved = useStore.getState().symbolNames[code];
      if (resolved === "" || resolved === undefined) setFallback(code);
    });
  }

  return (
    <span>
      <span style={{ fontWeight: strongName ? 600 : 400 }}>{display || code}</span>
      {showCode && name && (
        <span style={{ color: "#6e7681", fontSize: 11, marginLeft: 4 }}>{code}</span>
      )}
    </span>
  );
}