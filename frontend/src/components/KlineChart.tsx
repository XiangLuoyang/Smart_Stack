import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  IChartApi,
  ISeriesApi,
  LineData,
} from "lightweight-charts";
import type { KlineBar } from "../types";

interface Props {
  bars: KlineBar[];
}

export default function KlineChart({ bars }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const ma5Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma20Ref = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#1e1e2d" },
        textColor: "#d1d4dc",
      },
      grid: {
        vertLines: { color: "#2a2e39" },
        horzLines: { color: "#2a2e39" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#2a2e39" },
      timeScale: {
        borderColor: "#2a2e39",
        timeVisible: false,
      },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
    });
    chartRef.current = chart;
    candleRef.current = chart.addCandlestickSeries({
      upColor: "#ef5350",
      downColor: "#26a69a",
      borderVisible: false,
      wickUpColor: "#ef5350",
      wickDownColor: "#26a69a",
    });
    volumeRef.current = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
    });
    chart.priceScale("vol").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });
    ma5Ref.current = chart.addLineSeries({
      color: "#ffa726",
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    ma20Ref.current = chart.addLineSeries({
      color: "#42a5f5",
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!candleRef.current || bars.length === 0) return;
    candleRef.current.setData(
      bars.map((b) => ({
        time: b.date,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      }))
    );
    volumeRef.current?.setData(
      bars.map((b) => ({
        time: b.date,
        value: b.volume,
        color: b.close >= b.open ? "#ef535080" : "#26a69a80",
      }))
    );
    const toLine = (field: "ma5" | "ma20"): LineData[] =>
      bars
        .filter((b) => b[field] != null)
        .map((b) => ({ time: b.date, value: b[field] as number }));
    ma5Ref.current?.setData(toLine("ma5"));
    ma20Ref.current?.setData(toLine("ma20"));
    chartRef.current?.timeScale().fitContent();
  }, [bars]);

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
}
