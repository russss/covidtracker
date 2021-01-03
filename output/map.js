const colour_ramp = [
  [500, 500, "#0c2c84", true],
  [250, 250, "#225ea8", true],
  [100, 100, "#1d91c0", true],
  [75, 75, "#41b6c4", true],
  [50, 50, "#7fcdbb", true],
  [25, 25, "#c7e9b4", false],
  [10, 10, "#edf8b1", false],
  [0.01, 0.01, "#ffffd9", false],
  [0, 0, "#ececec", false]
];

const change_colour_ramp = [
  ["> 50", 50, "#c51b7d", true],
  ["> 25", 25, "#de77ae", false],
  ["> 10", 10, "#f1b6da", false],
  ["> 2", 2, "#fde0ef", false],
  ["0", -2, "#EDEDED", false],
  ["< -2", -10, "#e6f5d0", false],
  ["< -10", -20, "#b8e186", false],
  ["< -25", -50, "#7fbc41", false],
  ["< -50", -60, "#4d9221", true]
];

const positivity_colour_ramp = [
  ["> 20%", 20, "#810f7c", true],
  ["> 10%", 10, "#8856a7", true],
  ["> 6%", 6, "#8c96c6", true],
  ["> 3%", 3, "#9ebcda", false],
  ["> 1%", 1, "#bfd3e6", false],
  ["< 1%", 0, "#edf8fb", false]
];

function makeGraph(width, height, data, provisional_days, type, num_suffix="") {
  const gap = 1;
  var draw = SVG().size(width, height);

  const left_margin = 23,
    top_margin = 5,
    bottom_margin = 5,
    right_margin = 2;
  const graph_height = height - top_margin - bottom_margin;
  const graph_width = width - left_margin - right_margin;
  const max_value = Math.ceil(Math.max(...data, 5));
  const bar_width = graph_width / data.length - gap;

  if (type == "bar") {
    for (let i = 0; i < data.length; i++) {
      const bar_height = (data[i] / max_value) * graph_height;

      bar = draw
        .rect(bar_width, bar_height)
        .move(
          i * (bar_width + gap) + left_margin,
          graph_height - bar_height + top_margin - 1
        );

      if (i >= data.length - provisional_days) {
        bar.fill("#E6C8C8");
      } else {
        bar.fill("#d44");
      }
    }
  } else if (type == "line") {
    let path = "M";
    for (let i = 0; i < data.length; i++) {
      let x = i * (bar_width + gap) + bar_width / 2 + left_margin;
      let y =
        graph_height - (data[i] / max_value) * graph_height + top_margin - 1;
      path += `${x} ${y} `;
      if (i == 0) {
        path += "L";
      }
      if (i == data.length - 1) {
        const marker_diameter = 3;
        draw
          .circle(marker_diameter)
          .move(x, y - marker_diameter / 2)
          .fill("#384EF5")
          .stroke("none");
      }
    }
    draw
      .path(path)
      .stroke("#384EF5")
      .fill("none");
  }

  draw
    .text(max_value.toString() + num_suffix)
    .attr({ x: left_margin - 4, y: top_margin + 2 })
    .font({ fill: "#666", family: "Noto Sans", size: 9, anchor: "end" });

  draw
    .text("0" + num_suffix)
    .attr({ x: left_margin - 4, y: graph_height + top_margin + 2 })
    .font({ fill: "#666", family: "Noto Sans", size: 9, anchor: "end" });

  draw
    .line(left_margin - 2, top_margin, left_margin + 1, top_margin)
    .stroke({ width: 1, color: "#aaa" });

  draw
    .line(
      left_margin - 2,
      height - bottom_margin - 1,
      width - right_margin,
      height - bottom_margin - 1
    )
    .stroke({ width: 0.5, color: "#aaa" });
  return draw;
}

function getColour(ramp, value) {
  for (const element of ramp) {
    if (value >= element[1]) {
      return element[2];
    }
  }
  return ramp[ramp.length - 1][2];
}

function styleExpression(data, propname) {
  var expression = ["match", ["get", propname]];

  for (const gss_id in data) {
    const prevalence = (data[gss_id]["prevalence"] * 100000).toFixed(2);
    const colour = getColour(colour_ramp, prevalence);

    expression.push(gss_id, colour);
    if (gss_id == "E09000012") {
      expression.push("E09000001", colour);
    } else if (gss_id == "E06000052") {
      expression.push("E06000053", colour);
    }
  }

  expression.push("#ffffff");
  return expression;
}

function diffStyleExpression(data, propname) {
  var expression = ["match", ["get", propname]];

  for (const gss_id in data) {
    const change = (data[gss_id].change * 100000).toFixed(2);
    var colour = getColour(change_colour_ramp, change);

    expression.push(gss_id, colour);
    if (gss_id == "E09000012") {
      expression.push("E09000001", colour);
    } else if (gss_id == "E06000052") {
      expression.push("E06000053", colour);
    }
  }
  expression.push("#ffffff");
  return expression;
}

function positivityStyleExpression(data, propname) {
  var expression = ["match", ["get", propname]];

  for (const gss_id in data) {
    const positivity = data[gss_id].positivity;
    if (!positivity) {
      continue;
    }
    var colour = getColour(positivity_colour_ramp, positivity);

    expression.push(gss_id, colour);
    if (gss_id == "E09000012") {
      expression.push("E09000001", colour);
    } else if (gss_id == "E06000052") {
      expression.push("E06000053", colour);
    }
  }
  expression.push("#ffffff");
  return expression;
}

function popupRenderer(map, data, name_field, gss_field) {
  return function(e) {
    var props = e.features[0].properties;
    let gss = props[gss_field];
    let name = props[name_field];
    let sub_name = null;
    if (gss == "E09000001" || gss == "E09000012") {
      // City of London
      gss = "E09000012"; // Hackney
      name = "Hackney";
      sub_name = "(including City of London)";
    } else if (gss == "E06000053" || gss == "E06000052") {
      // Isles of Scilly
      gss = "E06000052"; // Cornwall
      name = "Cornwall";
      sub_name = "(including Isles of Scilly)";
    }
    let item = data[gss];

    let html = "<h3>" + name + "</h3>";
    if (sub_name) {
      html += "<p>" + sub_name + "</p>";
    }

    html += "<table>";

    if (item["cases"]) {
      html += "<tr><th>Weekly cases</th><td>" + item["cases"] + "</td></tr>";
    }

    html +=
      "<tr><th>Prevalence</th><td>" +
      (item["prevalence"] * 100000).toFixed(2) +
      " per 100,000</td></tr>";

    let change_prefix = '';
    if (item.change > 0) {
      change_prefix = '+';
    }
    html +=
      "<tr><th>Weekly change</th><td>" +
      change_prefix + (item["change"] * 100000).toFixed(2) +
      " per 100,000</td></tr>";
    if (item["positivity"]) {
      html +=
        "<tr><th>Test positivity</th><td>" +
        item["positivity"].toFixed(1) +
        "%</td></tr>";
    }
    html += "</table>";

    let div = window.document.createElement("div");
    div.innerHTML = html;

    if (item["history"]) {
      let header = document.createElement("h4");
      header.innerText = "Cases";
      div.appendChild(header);
      let graph = makeGraph(
        210,
        45,
        item["history"],
        item["provisional_days"],
        "bar"
      );
      div.appendChild(graph.node);
    }

    if (item["positivity_history"]) {
      let header = document.createElement("h4");
      header.innerText = "Test Positivity";
      div.appendChild(header);
      let graph = makeGraph(210, 45, item.positivity_history, 0, "line", "%");
      div.appendChild(graph.node);
    }

    // Prevent body from scrolling due to interactions on popup
    div.ontouchend = e => {
      e.preventDefault();
    };
    div.onwheel = e => {
      e.preventDefault();
    };

    new mapboxgl.Popup()
      .setLngLat(e.lngLat)
      .setDOMContent(div)
      .addTo(map);
  };
}

class LegendControl {
  onAdd(map) {
    this._map = map;
    this._container = document.createElement("div");
    this._container.className = "mapboxgl-ctrl-group mapboxgl-ctrl colour-key";
    this._ramp_container = null;
    return this._container;
  }

  setColours(ramp) {
    let container = document.createElement("div");

    for (const element of ramp) {
      let div = document.createElement("div");
      div.className = "colour-key-cell";
      div.innerHTML = element[0];
      div.style.backgroundColor = element[2];
      if (element[3]) {
        div.style.color = "#f0f0f0";
      }
      container.appendChild(div);
    }

    if (this._ramp_container) {
      this._container.replaceChild(container, this._ramp_container);
    } else {
      this._container.appendChild(container);
    }
    this._ramp_container = container;
  }
}

class SwitchControl {
  constructor(legend) {
    this._legend = legend;
  }

  onAdd(map) {
    this._map = map;
    this._container = document.createElement("div");
    this._container.className =
      "mapboxgl-ctrl-group mapboxgl-ctrl switcher-container";

    this._rate_button = document.createElement("button");
    this._rate_button.innerHTML = "Rate";
    this._rate_button.onclick = e => {
      history.pushState("rate", "", "#");
      this.setState("rate");
    };
    this._container.appendChild(this._rate_button);

    this._change_button = document.createElement("button");
    this._change_button.innerHTML = "Change";
    this._change_button.onclick = e => {
      history.pushState("change", "", "#change");
      this.setState("change");
    };
    this._container.appendChild(this._change_button);

    this._positivity_button = document.createElement("button");
    this._positivity_button.innerHTML = "Positivity";
    this._positivity_button.onclick = e => {
      history.pushState("positivity", "", "#positivity");
      this.setState("positivity");
    };
    this._container.appendChild(this._positivity_button);

    window.onpopstate = event => {
      if (event.state == null) {
        this.setState("rate");
      } else {
        this.setState(event.state);
      }
    };
    return this._container;
  }

  setState(state) {
    this._map.setLayoutProperty("cases_rel", "visibility", "none");
    this._map.setLayoutProperty("cases_abs", "visibility", "none");
    this._map.setLayoutProperty("positivity", "visibility", "none");
    this._rate_button.disabled = false;
    this._change_button.disabled = false;
    this._positivity_button.disabled = false;
    if (state == "rate") {
      this._rate_button.disabled = true;
      this._map.setLayoutProperty("cases_abs", "visibility", "visible");
      this._legend.setColours(colour_ramp);
    } else if (state == "change") {
      this._change_button.disabled = true;
      this._map.setLayoutProperty("cases_rel", "visibility", "visible");
      this._legend.setColours(change_colour_ramp);
    } else {
      this._positivity_button.disabled = true;
      this._map.setLayoutProperty("positivity", "visibility", "visible");
      this._legend.setColours(positivity_colour_ramp);
    }
    this._state = state;
  }
}

function initMap(data) {
  if (!mapboxgl.supported()) {
    const map = document.getElementById("body");
    map.innerHTML =
      "Your browser does not support this map.<br/>" +
      '<a href="http://webglreport.com">WebGL</a> with hardware acceleration is required';
    return;
  }

  var map = new mapboxgl.Map({
    container: "map",
    style: "style.json",
    center: [-3.1, 55.5],
    zoom: 5,
    customAttribution:
      '<a href="https://geoportal.statistics.gov.uk/datasets/local-authority-districts-december-2019-boundaries-uk-bfc">Contains OS data © Crown copyright and database right 2019</a>',
    maxBounds: [[-17.1, 49.4], [11.2, 61.4]]
  });
  window.map = map;

  map.touchZoomRotate.disableRotation();
  map.addControl(new mapboxgl.NavigationControl({ showCompass: false }));

  const legend = new LegendControl();
  const switchControl = new SwitchControl(legend);
  map.addControl(switchControl, "top-right");
  map.addControl(legend, "bottom-right");

  map.on("load", () => {
    const opacity_func = [
      "interpolate",
      ["exponential", 1.4],
      ["zoom"],
      5,
      0.85,
      12,
      0.5
    ];

    map.addLayer(
      {
        id: "cases_abs",
        type: "fill",
        source: "areas",
        "source-layer": "local_authorities",
        paint: {
          "fill-color": styleExpression(data, "lad19cd"),
          "fill-opacity": opacity_func
        }
      },
      "la_boundary"
    );

    map.addLayer(
      {
        id: "cases_rel",
        type: "fill",
        source: "areas",
        "source-layer": "local_authorities",
        paint: {
          "fill-color": diffStyleExpression(data, "lad19cd"),
          "fill-opacity": opacity_func
        },
        layout: {
          visibility: "none"
        }
      },
      "la_boundary"
    );

    map.addLayer(
      {
        id: "positivity",
        type: "fill",
        source: "areas",
        "source-layer": "local_authorities",
        paint: {
          "fill-color": positivityStyleExpression(data, "lad19cd"),
          "fill-opacity": opacity_func
        },
        layout: {
          visibility: "none"
        }
      },
      "la_boundary"
    );

    for (const layer of ["cases_abs", "cases_rel", "positivity"]) {
      map.on("click", layer, popupRenderer(map, data, "lad19nm", "lad19cd"));

      map.on("mouseenter", layer, function() {
        map.getCanvas().style.cursor = "pointer";
      });

      map.on("mouseleave", layer, function() {
        map.getCanvas().style.cursor = "";
      });
    }

    let state = window.location.hash.split("#")[1];
    if (state) {
      switchControl.setState(state);
    } else {
      switchControl.setState("rate");
    }
  });
}
