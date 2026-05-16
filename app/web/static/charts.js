(function () {
  "use strict";

  const THEME_OPTIONS = {
    dark: {
      background: "#0e1117",
      text: "#d1d4dc",
      grid: "#1e222d",
      border: "#2a2e39",
      upColor: "#26a69a",
      downColor: "#ef5350",
      lineColor: "#2962ff",
    },
    light: {
      background: "#ffffff",
      text: "#131722",
      grid: "#eeeeee",
      border: "#cccccc",
      upColor: "#26a69a",
      downColor: "#ef5350",
      lineColor: "#2962ff",
    },
  };

  function getQueryParam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
  }

  function showError(container, message) {
    container.innerHTML = "";
    const el = document.createElement("div");
    el.className = "chart-error";
    el.textContent = message;
    container.appendChild(el);
    document.body.dataset.chartReady = "true";
  }

  function applyExportMode() {
    if (getQueryParam("export") === "true") {
      document.body.classList.add("export-mode");
    }
  }

  function applySeriesStyle(style, defaults) {
    const merged = Object.assign({}, defaults);
    if (!style) return merged;
    if (style.color) merged.color = style.color;
    if (style.line_width) merged.lineWidth = style.line_width;
    if (style.up_color) merged.upColor = style.up_color;
    if (style.down_color) merged.downColor = style.down_color;
    if (style.opacity !== undefined && style.opacity !== null) {
      merged.opacity = style.opacity;
    }
    return merged;
  }

  function addSeries(chart, series, theme) {
    const palette = THEME_OPTIONS[theme] || THEME_OPTIONS.dark;
    let handle = null;
    const data = series.data || [];

    switch (series.type) {
      case "candlestick": {
        handle = chart.addCandlestickSeries(
          applySeriesStyle(series.style, {
            upColor: palette.upColor,
            downColor: palette.downColor,
            borderUpColor: palette.upColor,
            borderDownColor: palette.downColor,
            wickUpColor: palette.upColor,
            wickDownColor: palette.downColor,
          })
        );
        break;
      }
      case "bar": {
        handle = chart.addBarSeries(
          applySeriesStyle(series.style, {
            upColor: palette.upColor,
            downColor: palette.downColor,
          })
        );
        break;
      }
      case "line": {
        handle = chart.addLineSeries(
          applySeriesStyle(series.style, {
            color: palette.lineColor,
            lineWidth: 2,
          })
        );
        break;
      }
      case "area": {
        handle = chart.addAreaSeries(
          applySeriesStyle(series.style, {
            lineColor: palette.lineColor,
            topColor: "rgba(41, 98, 255, 0.4)",
            bottomColor: "rgba(41, 98, 255, 0.0)",
          })
        );
        break;
      }
      case "histogram": {
        const opts = applySeriesStyle(series.style, {
          color: palette.upColor,
          priceFormat: { type: "volume" },
          priceScaleId: "volume",
        });
        handle = chart.addHistogramSeries(opts);
        chart.priceScale("volume").applyOptions({
          scaleMargins: { top: 0.8, bottom: 0 },
        });
        break;
      }
      default:
        return;
    }

    if (handle && data.length > 0) {
      handle.setData(data);
    }
  }

  async function render(chartId, apiBase) {
    const container = document.getElementById("chart-container");
    const titleEl = document.getElementById("chart-title");
    if (!container) return;

    try {
      const response = await fetch(`${apiBase}/api/charts/${chartId}`);
      if (!response.ok) {
        if (response.status === 404) {
          showError(container, "Chart not found.");
        } else if (response.status === 410) {
          showError(container, "Chart has been removed.");
        } else {
          showError(container, `Failed to load chart (status ${response.status}).`);
        }
        return;
      }
      const payload = await response.json();
      const meta = payload.payload.meta || {};
      const theme = meta.theme === "light" ? "light" : "dark";
      const palette = THEME_OPTIONS[theme];

      document.body.classList.add(`theme-${theme}`);
      if (titleEl) {
        titleEl.textContent = meta.title || payload.title || payload.instrument?.symbol || "";
      }

      const chart = LightweightCharts.createChart(container, {
        width: container.clientWidth,
        height: container.clientHeight,
        autoSize: true,
        layout: {
          background: { color: palette.background },
          textColor: palette.text,
        },
        grid: {
          vertLines: { color: palette.grid },
          horzLines: { color: palette.grid },
        },
        timeScale: {
          borderColor: palette.border,
          timeVisible: false,
        },
        rightPriceScale: { borderColor: palette.border },
      });

      const allSeries = payload.payload.series || [];
      if (allSeries.every((s) => (s.data || []).length === 0)) {
        showError(container, "No data available.");
        return;
      }

      for (const series of allSeries) {
        addSeries(chart, series, theme);
      }

      chart.timeScale().fitContent();

      setTimeout(() => {
        chart.resize(container.clientWidth, container.clientHeight);
        document.body.dataset.chartReady = "true";
      }, 250);
    } catch (err) {
      showError(container, `Failed to load chart: ${err.message || err}`);
    }
  }

  window.ChartService = {
    render,
    applyExportMode,
  };
})();
