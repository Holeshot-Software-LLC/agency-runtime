"use strict";
(function installAgencyCharts(root, factory) {
  const charts = factory();
  if (typeof module === "object" && module.exports) module.exports = charts;
  if (root) root.AgencyCharts = charts;
}(typeof globalThis === "object" ? globalThis : this, function createAgencyCharts() {
  const SVG_NS = "http://www.w3.org/2000/svg";
  const SUCCESS = new Set(["success", "completed", "ok"]);
  const FAILED = new Set(["failed", "failure", "error", "cancelled", "timed_out", "timeout"]);
  const SKIPPED = new Set(["skipped", "blocked", "not_run"]);
  let chartSequence = 0;
  function boundedInteger(value, fallback, minimum, maximum) {
    const number = Number(value);
    if (!Number.isFinite(number)) return fallback;
    return Math.max(minimum, Math.min(Math.trunc(number), maximum));
  }
  function timestamp(value) {
    if (value instanceof Date) return value.valueOf();
    if (typeof value === "number") return Number.isFinite(value) ? value : NaN;
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : NaN;
  }
  function rows(activity, name) {
    return Array.isArray(activity?.[name]) ? activity[name] : [];
  }
  function bucketActivity(activity, options = {}) {
    const bucketCount = boundedInteger(options.bucketCount, 24, 1, 48);
    const bucketMs = boundedInteger(options.bucketMs, 60000, 10000, 3600000);
    const requestedNow = options.now === undefined ? Date.now() : timestamp(options.now);
    const now = Number.isFinite(requestedNow) ? requestedNow : Date.now();
    const currentStart = Math.floor(now / bucketMs) * bucketMs;
    const windowStart = currentStart - ((bucketCount - 1) * bucketMs);
    const buckets = Array.from({ length: bucketCount }, (_, index) => ({
      startMs: windowStart + (index * bucketMs),
      endMs: windowStart + ((index + 1) * bucketMs),
      routes: 0,
      delegations: 0,
    }));
    function observe(items, field, fallbackField) {
      items.forEach((item) => {
        if (!item || typeof item !== "object") return;
        const observedAt = timestamp(item[field] || (fallbackField ? item[fallbackField] : null));
        if (!Number.isFinite(observedAt) || observedAt < windowStart || observedAt > now) return;
        const index = Math.min(
          bucketCount - 1,
          Math.floor((observedAt - windowStart) / bucketMs),
        );
        buckets[index][field === "created_at" ? "routes" : "delegations"] += 1;
      });
    }
    observe(rows(activity, "routing"), "created_at");
    observe(rows(activity, "delegations"), "completed_at", "started_at");
    return buckets;
  }
  function outcomeCounts(activity) {
    const counts = { success: 0, failed: 0, skipped: 0, unknown: 0, total: 0 };
    rows(activity, "delegations").forEach((delegation) => {
      const status = delegation && typeof delegation === "object"
        ? String(delegation.status || "unknown").trim().toLowerCase()
        : "unknown";
      counts.total += 1;
      if (SUCCESS.has(status)) counts.success += 1;
      else if (FAILED.has(status)) counts.failed += 1;
      else if (SKIPPED.has(status)) counts.skipped += 1;
      else counts.unknown += 1;
    });
    return counts;
  }
  function retryDelay(attempt, random = Math.random) {
    const normalizedAttempt = boundedInteger(attempt, 1, 1, 31);
    const exponential = Math.min(30000, 2000 * (2 ** (normalizedAttempt - 1)));
    let sample;
    try { sample = typeof random === "function" ? Number(random()) : Number(random); }
    catch { sample = 0; }
    const unit = Number.isFinite(sample) ? Math.max(0, Math.min(sample, 1)) : 0;
    const jitter = Math.floor(Math.min(500, exponential * 0.2) * unit);
    return Math.min(30000, exponential + jitter);
  }
  function svgNode(documentRef, tag, attributes = {}, text) {
    const node = documentRef.createElementNS(SVG_NS, tag);
    Object.entries(attributes).forEach(([name, value]) => node.setAttribute(name, String(value)));
    if (text !== undefined) node.textContent = String(text);
    return node;
  }
  function chartDocument(root) {
    return root?.ownerDocument || (typeof document === "object" ? document : null);
  }
  function accessibleSvg(documentRef, title, description, viewBox, summaryId = "") {
    chartSequence += 1;
    const titleId = `agency-chart-title-${chartSequence}`;
    const descriptionId = `agency-chart-description-${chartSequence}`;
    const svg = svgNode(documentRef, "svg", {
      class: "signal-chart-svg",
      viewBox,
      preserveAspectRatio: "xMidYMid meet",
      role: "group",
      "aria-labelledby": titleId,
      "aria-describedby": [descriptionId, summaryId].filter(Boolean).join(" "),
    });
    svg.append(
      svgNode(documentRef, "title", { id: titleId }, title),
      svgNode(documentRef, "desc", { id: descriptionId }, description),
    );
    return svg;
  }
  function linePoints(buckets, key, width, height, left, top, maximum) {
    const step = buckets.length > 1 ? width / (buckets.length - 1) : 0;
    return buckets.map((bucket, index) => {
      const x = left + (index * step);
      const y = top + height - ((bucket[key] / maximum) * height);
      return { x, y };
    });
  }
  function pathFromPoints(points) {
    let path = `M${points[0].x.toFixed(2)},${points[0].y.toFixed(2)}`;
    for (let index = 1; index < points.length; index += 1) {
      const previous = points[index - 1];
      const point = points[index];
      const midpoint = (previous.x + point.x) / 2;
      path += ` C${midpoint.toFixed(2)},${previous.y.toFixed(2)}`;
      path += ` ${midpoint.toFixed(2)},${point.y.toFixed(2)}`;
      path += ` ${point.x.toFixed(2)},${point.y.toFixed(2)}`;
    }
    return path;
  }
  function areaFromPoints(points, baseline) {
    const first = points[0];
    const last = points[points.length - 1];
    return `${pathFromPoints(points)} L${last.x.toFixed(2)},${baseline} L${first.x.toFixed(2)},${baseline} Z`;
  }
  function renderActivityChart(root, summaryRoot, activity, options = {}) {
    const buckets = bucketActivity(activity, options);
    const routes = buckets.reduce((total, bucket) => total + bucket.routes, 0);
    const delegations = buckets.reduce((total, bucket) => total + bucket.delegations, 0);
    const minutes = Math.round(
      (buckets.length * (buckets[0].endMs - buckets[0].startMs)) / 60000,
    );
    const summary = `${routes} observed routes · ${delegations} delegations · last ${minutes} minutes`;
    if (summaryRoot) summaryRoot.textContent = summary;
    const documentRef = chartDocument(root);
    if (!root || !documentRef) return buckets;
    const svg = accessibleSvg(
      documentRef,
      "Observed routing and delegation activity",
      `${summary}. Counts reflect the bounded metadata returned by the local runtime.`,
      "0 0 720 240",
      summaryRoot?.id || "",
    );
    const left = 36;
    const top = 22;
    const plotWidth = 660;
    const plotHeight = 172;
    const baseline = top + plotHeight;
    const maximum = Math.max(1, ...buckets.flatMap((bucket) => [bucket.routes, bucket.delegations]));
    for (let index = 0; index <= 4; index += 1) {
      const y = top + ((plotHeight / 4) * index);
      svg.append(svgNode(documentRef, "line", {
        class: "grid-line",
        "data-chart-grid": "true",
        x1: left,
        y1: y,
        x2: left + plotWidth,
        y2: y,
      }));
    }
    svg.append(
      svgNode(documentRef, "text", {
        class: "axis-label axis-label-y",
        "aria-hidden": "true",
        x: left - 9,
        y: top + 3,
        "text-anchor": "end",
      }, maximum),
      svgNode(documentRef, "text", {
        class: "axis-label axis-label-y",
        "aria-hidden": "true",
        x: left - 9,
        y: baseline + 3,
        "text-anchor": "end",
      }, 0),
    );
    const routePoints = linePoints(buckets, "routes", plotWidth, plotHeight, left, top, maximum);
    const delegationPoints = linePoints(buckets, "delegations", plotWidth, plotHeight, left, top, maximum);
    svg.append(
      svgNode(documentRef, "path", {
        class: "series-area series-routing",
        "data-chart-area": "true",
        "data-series": "routing",
        d: areaFromPoints(routePoints, baseline),
      }),
      svgNode(documentRef, "path", {
        class: "series-area series-delegations",
        "data-chart-area": "true",
        "data-series": "delegations",
        d: areaFromPoints(delegationPoints, baseline),
      }),
      svgNode(documentRef, "path", {
        class: "series-line series-routing",
        "data-series": "routing",
        d: pathFromPoints(routePoints),
      }),
      svgNode(documentRef, "path", {
        class: "series-line series-delegations",
        "data-series": "delegations",
        d: pathFromPoints(delegationPoints),
      }),
    );
    routePoints.forEach((point, index) => {
      if (!buckets[index].routes) return;
      const circle = svgNode(documentRef, "circle", {
        class: "chart-point",
        "data-chart-point": "true",
        "data-series": "routing",
        cx: point.x.toFixed(2),
        cy: point.y.toFixed(2),
        r: 2.4,
        tabindex: 0,
        role: "img",
        "aria-label": `${buckets[index].routes} routes in this minute`,
      });
      circle.append(svgNode(documentRef, "title", {}, `${buckets[index].routes} routes`));
      svg.append(circle);
    });
    delegationPoints.forEach((point, index) => {
      if (!buckets[index].delegations) return;
      const circle = svgNode(documentRef, "circle", {
        class: "chart-point",
        "data-chart-point": "true",
        "data-series": "delegations",
        cx: point.x.toFixed(2),
        cy: point.y.toFixed(2),
        r: 2.4,
        tabindex: 0,
        role: "img",
        "aria-label": `${buckets[index].delegations} delegations in this minute`,
      });
      circle.append(svgNode(documentRef, "title", {}, `${buckets[index].delegations} delegations`));
      svg.append(circle);
    });
    const first = buckets[0]?.startMs;
    const last = buckets[buckets.length - 1]?.startMs;
    if (Number.isFinite(first) && Number.isFinite(last)) {
      const timeFormat = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" });
      svg.append(
        svgNode(documentRef, "text", { class: "axis-label", "data-chart-label": "start", x: left, y: 224 }, timeFormat.format(first)),
        svgNode(documentRef, "text", { class: "axis-label axis-label-end", "data-chart-label": "end", "text-anchor": "end", x: left + plotWidth, y: 224 }, timeFormat.format(last)),
      );
    }
    root.replaceChildren(svg);
    root.dataset.routes = String(routes);
    root.dataset.delegations = String(delegations);
    return buckets;
  }
  function renderOutcomeChart(root, summaryRoot, activity) {
    const counts = outcomeCounts(activity);
    const summary = `${counts.total} observed delegations · ${counts.success} completed · ${counts.failed} failed · ${counts.skipped} skipped · ${counts.unknown} unknown`;
    if (summaryRoot) summaryRoot.textContent = summary;
    const documentRef = chartDocument(root);
    if (!root || !documentRef) return counts;
    const svg = accessibleSvg(
      documentRef,
      "Observed delegation outcomes",
      `${summary}. Outcomes describe bounded stored delegation evidence.`,
      "0 0 240 240",
      summaryRoot?.id || "",
    );
    const center = 120;
    const radius = 72;
    svg.append(svgNode(documentRef, "circle", {
      class: "ring-track",
      cx: center,
      cy: center,
      r: radius,
      pathLength: 100,
      "stroke-width": 18,
    }));
    let offset = 0;
    [
      ["success", "Completed", counts.success],
      ["failed", "Failed", counts.failed],
      ["skipped", "Skipped", counts.skipped],
      ["unknown", "Unknown", counts.unknown],
    ].forEach(([name, label, value]) => {
      if (!counts.total || !value) return;
      const share = (value / counts.total) * 100;
      const segment = svgNode(documentRef, "circle", {
        class: `ring-segment ring-${name}`,
        cx: center,
        cy: center,
        r: radius,
        pathLength: 100,
        "stroke-width": 18,
        "stroke-linecap": "butt",
        "stroke-dasharray": `${share.toFixed(3)} ${(100 - share).toFixed(3)}`,
        "stroke-dashoffset": (-offset).toFixed(3),
        transform: `rotate(-90 ${center} ${center})`,
        tabindex: 0,
        role: "img",
        "aria-label": `${label}: ${value} (${share.toFixed(1)}%)`,
      });
      segment.append(svgNode(documentRef, "title", {}, `${label}: ${value}`));
      svg.append(segment);
      offset += share;
    });
    svg.append(
      svgNode(documentRef, "text", {
        class: "outcome-total",
        x: center,
        y: 116,
        fill: "#f0f5f6",
        "font-size": 32,
        "font-weight": 700,
        "text-anchor": "middle",
      }, counts.total),
      svgNode(documentRef, "text", {
        class: "outcome-caption",
        x: center,
        y: 139,
        fill: "#728296",
        "font-size": 11,
        "text-anchor": "middle",
      }, "delegations"),
    );
    root.replaceChildren(svg);
    root.dataset.total = String(counts.total);
    return counts;
  }
  return {
    bucketActivity,
    outcomeCounts,
    retryDelay,
    renderActivityChart,
    renderOutcomeChart,
  };
}));
