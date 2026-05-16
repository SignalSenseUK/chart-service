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
        return null;
    }

    if (handle && data.length > 0) {
      handle.setData(data);
    }
    
    return { handle, series };
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

      const seriesList = [];
      for (const series of allSeries) {
        const item = addSeries(chart, series, theme);
        if (item) seriesList.push(item);
      }

      const legend = document.createElement("div");
      legend.className = "chart-legend";
      container.appendChild(legend);

      function updateLegend(param) {
        const validCrosshair = param && param.time && param.point &&
                               param.point.x >= 0 && param.point.x <= container.clientWidth &&
                               param.point.y >= 0 && param.point.y <= container.clientHeight;
        
        let html = '';
        for (const item of seriesList) {
          if (!item.handle) continue;
          
          let val = "N/A";
          let color = item.series.style?.color || palette.text;
          
          if (validCrosshair) {
            const data = param.seriesData.get(item.handle);
            if (data) {
              if (item.series.type === "candlestick" || item.series.type === "bar") {
                val = `O: ${data.open} H: ${data.high} L: ${data.low} C: ${data.close}`;
              } else {
                val = data.value !== undefined ? data.value : "N/A";
              }
            }
          } else {
            const dataArr = item.series.data || [];
            if (dataArr.length > 0) {
               const last = dataArr[dataArr.length - 1];
               if (item.series.type === "candlestick" || item.series.type === "bar") {
                 val = `O: ${last.open} H: ${last.high} L: ${last.low} C: ${last.close}`;
               } else {
                 val = last.value !== undefined ? last.value : (last.close !== undefined ? last.close : "N/A");
               }
            }
          }
          
          const name = item.series.title || item.series.id || item.series.type;
          html += `<div class="chart-legend-item" style="color: ${color}">
            <span class="chart-legend-title">${name}</span><span>${val}</span>
          </div>`;
        }
        legend.innerHTML = html;
      }

      chart.subscribeCrosshairMove(updateLegend);
      updateLegend({}); // Initial populate

      setTimeout(() => {
        chart.resize(container.clientWidth, container.clientHeight);
        chart.timeScale().fitContent();
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
