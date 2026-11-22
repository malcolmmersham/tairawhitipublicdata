"use strict";

const PLACE_COLOURS = ["#d6ede6", "#a5d9ca", "#68bcae", "#338e88", "#12585a"];
const PLACE_BOUNDARIES = "https://datafinder.stats.govt.nz/layer/111227-statistical-area-2-2023-generalised/";
let placeMap;

function placePaths(features) {
  const polygons = features.map(({ geometry }) =>
    geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates);
  const coordinates = polygons.flat(3);
  const lon = coordinates.map(p => p[0]), lat = coordinates.map(p => p[1]);
  const west = Math.min(...lon), east = Math.max(...lon), north = Math.max(...lat), south = Math.min(...lat);
  const longitudeScale = Math.cos((north + south) * Math.PI / 360);
  const width = (east - west) * longitudeScale, height = north - south;
  const scale = Math.min(400 / width, 420 / height);
  const xPad = (440 - width * scale) / 2, yPad = (460 - height * scale) / 2;
  return polygons.map(area => area.flatMap(polygon => polygon.map(ring =>
    ring.map(([x, y], i) => `${i ? "L" : "M"}${(xPad + (x - west) * longitudeScale * scale).toFixed(1)},${(yPad + (north - y) * scale).toFixed(1)}`).join("") + "Z"
  )).join(""));
}

function placeSelect(id, label, options) {
  const select = el("select", { id }, options.map(([value, text]) => el("option", { value, text })));
  return { select, field: el("div", { class: "sampling-field" }, el("label", { for: id, text: label }), select) };
}

function viewPlaces() {
  const indicators = Object.entries(D.indicators).filter(([, meta]) => meta.display === "places");
  const population = seriesFor("sa2_population").filter(s => s.geo_type === "sa2");
  if (!population.length) return el("p", { class: "empty", text: "Census place profiles are currently unavailable." });

  const areas = population.map(s => ({ code: s.geo, name: s.geo_name })).sort((a, b) => a.name.localeCompare(b.name, "en-NZ"));
  const byIndicator = new Map(indicators.map(([id]) =>
    [id, new Map(seriesFor(id).filter(s => s.geo_type === "sa2").map(s => [s.geo, s]))]));
  const indicator = placeSelect("places-indicator", "Indicator", indicators.map(([id, meta]) => [id, meta.name]));
  const year = placeSelect("places-year", "Year", []);
  const area = placeSelect("places-area", "Area", areas.map(({ code, name }) => [code, name]));
  area.select.value = population.reduce((largest, s) => s.points.at(-1)[1] > largest.points.at(-1)[1] ? s : largest).geo;
  const definition = el("p", { class: "note" });
  const mapHost = el("div", {}, el("p", { class: "note", text: "Loading SA2 boundaries…" }));
  const legend = el("div", { class: "places-legend" });
  const ranking = el("div", { class: "places-ranking" });
  const profile = el("section", { class: "places-profile", "aria-label": "Selected place profile" });
  const mapMarks = new Map(), rankMarks = new Map();
  let boundaries;

  const pickArea = code => {
    area.select.value = code;
    showProfile();
  };
  const valueText = (value, meta) => value == null ? "Unavailable" : fmt(value, meta.format);
  const showProfile = () => {
    const code = area.select.value;
    const id = indicator.select.value, meta = D.indicators[id];
    const series = byIndicator.get(id).get(code);
    const summary = el("table", {}, el("thead", {}, el("tr", {},
      el("th", { text: "Indicator" }), el("th", { class: "num", text: "2023 value" }))),
      el("tbody", {}, indicators.map(([key, item]) => {
        const point = byIndicator.get(key).get(code)?.points.find(p => p[0].startsWith("2023"));
        return el("tr", {}, el("th", { scope: "row" }, el("button", { type: "button", class: "link", text: item.name,
          onclick: () => { indicator.select.value = key; setYears(); render(); indicator.select.focus(); } })),
          el("td", { class: "num", text: valueText(point?.[1], item) }));
      })));
    const census = series?.points || [];
    const history = census.filter(p => p[1] != null).length > 1
      ? lineChart([{ label: series.geo_name, color: "var(--accent)", points: census, ptype: "year" }], meta)
      : null;
    profile.replaceChildren(el("h2", { text: area.select.selectedOptions[0].textContent }),
      el("div", { class: "places-grid" },
        el("article", { class: "card" }, el("h3", { text: "2023 place profile" }), el("div", { class: "tbl-wrap" }, summary)),
        el("article", { class: "card" }, el("h3", { text: meta.name }), history,
          el("div", { class: "tbl-wrap" }, el("table", {}, el("thead", {}, el("tr", {},
            el("th", { text: "Year" }), el("th", { class: "num", text: series?.unit || "Value" }))),
          el("tbody", {}, census.map(([date, value]) => el("tr", {},
            el("td", { text: date.slice(0, 4) }), el("td", { class: "num", text: valueText(value, meta) })))))))));
    for (const marks of [mapMarks, rankMarks]) {
      for (const [key, node] of marks) node.setAttribute("aria-pressed", key === code);
    }
  };
  const setYears = () => {
    const available = [...new Set([...byIndicator.get(indicator.select.value).values()]
      .flatMap(s => s.points.map(p => p[0].slice(0, 4))))].sort().reverse();
    const previous = year.select.value;
    year.select.replaceChildren(...available.map(y => el("option", { value: y, text: y })));
    year.select.value = available.includes(previous) ? previous : available[0];
  };
  const render = () => {
    const id = indicator.select.value, meta = D.indicators[id], selectedYear = year.select.value;
    const data = byIndicator.get(id);
    const values = new Map(areas.map(({ code }) => [code, data.get(code)?.points.find(p => p[0].startsWith(selectedYear))?.[1] ?? null]));
    const available = [...values.values()].filter(v => v != null);
    const min = Math.min(...available), max = Math.max(...available);
    const colour = v => v == null ? "var(--grid)" :
      PLACE_COLOURS[Math.min(4, Math.floor(5 * (v - min) / (max - min || 1)))];
    const unit = data.values().next().value?.unit;
    definition.replaceChildren(`${selectedYear} ${meta.period_label || "Census"}${unit ? ` · ${unit}` : ""} · ${meta.caveat} `,
      el("a", { href: meta.url, text: "Stats NZ source" }));
    legend.replaceChildren(...(available.length ? [
      el("span", { text: valueText(min, meta) }),
      el("span", { class: "places-key", "aria-hidden": "true" }, PLACE_COLOURS.map(c => el("i", { style: `background:${c}` }))),
      el("span", { text: valueText(max, meta) }),
    ] : []), el("span", { class: "places-key", "aria-hidden": "true" }, el("i", { class: "places-missing" })),
    el("span", { text: "Unavailable" }));
    rankMarks.clear();
    ranking.replaceChildren(...[...areas].sort((a, b) => (values.get(b.code) ?? -Infinity) - (values.get(a.code) ?? -Infinity) ||
      a.name.localeCompare(b.name, "en-NZ")).map(({ code, name }) => {
      const value = values.get(code);
      const button = el("button", { type: "button", class: "places-bar", onclick: () => pickArea(code) },
        el("span", { text: name }), el("b", { text: valueText(value, meta) }),
        value != null ? el("i", { style: `width:${100 * value / (max || 1)}%;background:${colour(value)}`, "aria-hidden": "true" }) : null);
      rankMarks.set(code, button);
      return button;
    }));
    if (boundaries) {
      const ns = "http://www.w3.org/2000/svg";
      const svg = document.createElementNS(ns, "svg");
      svg.setAttribute("viewBox", "0 0 440 460");
      svg.setAttribute("class", "places-map");
      svg.setAttribute("aria-label", `${selectedYear} ${meta.name} by statistical area`);
      mapMarks.clear();
      for (const [i, feature] of boundaries.features.entries()) {
        const { code, name } = feature.properties;
        const path = document.createElementNS(ns, "path");
        const label = `${name}, ${valueText(values.get(code), meta)}`;
        path.setAttribute("d", boundaries.paths[i]);
        path.setAttribute("fill", colour(values.get(code)));
        path.setAttribute("fill-rule", "evenodd");
        path.setAttribute("role", "button");
        path.setAttribute("tabindex", "0");
        path.setAttribute("aria-label", label);
        const title = document.createElementNS(ns, "title");
        title.textContent = label;
        path.append(title);
        path.addEventListener("click", () => pickArea(code));
        path.addEventListener("keydown", event => {
          if (event.key === "Enter" || event.key === " ") { event.preventDefault(); pickArea(code); }
        });
        mapMarks.set(code, path);
        svg.append(path);
      }
      mapHost.replaceChildren(svg);
    }
    showProfile();
  };
  indicator.select.addEventListener("change", () => { setYears(); render(); });
  year.select.addEventListener("change", render);
  area.select.addEventListener("change", showProfile);
  setYears();
  render();
  placeMap ||= fetch("data/sa2-boundaries.geojson").then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  });
  placeMap.then(collection => {
    const codes = new Set(collection.features.map(feature => feature.properties.code));
    if (codes.size !== areas.length || areas.some(({ code }) => !codes.has(code))) throw new Error("SA2 codes do not match");
    boundaries = { features: collection.features, paths: placePaths(collection.features) };
    render();
  }).catch(() => {
    placeMap = undefined;
    mapHost.replaceChildren(el("p", { class: "note", text: "The map could not load. Select an area from the comparison chart or area picker." }));
  });

  return el("div", {},
    el("h2", { text: "Gisborne District place profiles" }),
    el("p", { class: "intro", text: `Compare ${areas.length} populated statistical areas (SA2s) on consistent 2023 boundaries.` }),
    el("div", { class: "filters places-controls" }, indicator.field, year.field, area.field),
    definition,
    el("div", { class: "places-grid" },
      el("article", { class: "card" }, el("h3", { text: "Map by area" }), mapHost, legend,
        el("div", { class: "src" }, "Stats NZ boundaries · CC BY 4.0", el("a", { href: PLACE_BOUNDARIES, text: "Boundary source" }))),
      el("article", { class: "card" }, el("h3", { text: "Compare areas" }), ranking)),
    profile,
    el("p", { class: "note" }, "Stats NZ randomly rounds Census counts and suppresses some small figures. Percentages use the published rounded counts.",
      " ", el("a", { href: "data/observations.csv", download: "observations.csv", text: "Download observations (CSV)" })));
}
