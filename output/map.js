const colour_ramp = [
  [100, "#b30000"],
  [75, "#e34a33"],
  [50, "#fc8d59"],
  [25, "#fdbb84"],
  [10, "#fdd49e"],
  [0.01, "#fef0d9"],
  [0, "#ececec"]
];

const change_colour_ramp = [
  [2.5, "#c51b7d"],
  [1, "#e9a3c9"],
  [0, "#fde0ef"],
  [-0.25, "#e6f5d0"],
  [-0.5, "#a1d76a"],
  [-1, "#4d9221"]
];

function makeGraph(width, height, data, provisional_days) {
  const gap = 1;
  var draw = SVG().size(width, height);

  const left_margin = 18;
  const top_margin = 5;
  const bottom_margin = 5;
  const graph_height = height - top_margin - bottom_margin;
  const graph_width = width - left_margin;
  const max_value = Math.max(...data, 5);
  const bar_width = graph_width / data.length - gap;
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

  draw
    .text(max_value.toString())
    .attr({ x: left_margin - 4, y: top_margin + 3 })
    .font({ fill: "#333", family: "Noto Sans", size: 9, anchor: "end" });

  draw
    .text("0")
    .attr({ x: left_margin - 4, y: graph_height + top_margin + 3 })
    .font({ fill: "#333", family: "Noto Sans", size: 9, anchor: "end" });

  draw
    .line(left_margin - 2, top_margin, left_margin + 1, top_margin)
    .stroke({ width: 1, color: "#aaa" });

  draw
    .line(
      left_margin - 2,
      height - bottom_margin - 1,
      width,
      height - bottom_margin - 1
    )
    .stroke({ width: 0.5, color: "#aaa" });
  return draw;
}

function getColour(ramp, value) {
  for (const element of ramp) {
    if (value >= element[0]) {
      return element[1];
    }
  }
  return null;
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
    const change = data[gss_id].change;
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
    html +=
      "<tr><th>Weekly increase</th><td>" +
      (item["change"] * 100).toFixed(0) +
      "%</td></tr>";
    html += "</table>";

    let div = window.document.createElement("div");
    div.innerHTML = html;

    if (item["history"]) {
      let graph = makeGraph(210, 45, item["history"], item["provisional_days"]);
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
    this.setColours(colour_ramp);
    return this._container;
  }

  setColours(ramp, percent) {
    let container = document.createElement("div");

    for (const element of ramp) {
      let div = document.createElement("div");
      div.className = "colour-key-cell";
      if (percent) {
        div.innerHTML = (element[0] * 100) + "%";
      } else {
        div.innerHTML = element[0];
      }
      div.style.backgroundColor = element[1];
      if (element[0] > 50 || (percent && Math.abs(element[0]) >= 1)) {
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
    this._container.className = "mapboxgl-ctrl-group mapboxgl-ctrl";

    this._button = document.createElement("button");
    this._state = 'rate';
    this._button.innerHTML = '%';
    this._button.onclick = (e) => {
      if (this._state == 'rate') {
        this.setState('change');
      } else {
        this.setState('rate');
      }
    }
    this._container.appendChild(this._button);
    return this._container;
  }

  setState(state) {
    if (state == 'rate') {
      this._button.innerHTML = '%';
      this._map.setLayoutProperty("cases_rel", "visibility", "none");
      this._map.setLayoutProperty("cases_abs", "visibility", "visible");
      this._legend.setColours(colour_ramp);
    } else {
      this._button.innerHTML = '↕';
      this._map.setLayoutProperty("cases_abs", "visibility", "none");
      this._map.setLayoutProperty("cases_rel", "visibility", "visible");
      this._legend.setColours(change_colour_ramp, true);
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
  map.addControl(new SwitchControl(legend), "top-right");
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
          visibility: 'none'
        }
      },
      "la_boundary"
    );

    for (const layer of ['cases_abs', 'cases_rel']) {
      map.on("click", layer, popupRenderer(map, data, "lad19nm", "lad19cd"));

      map.on("mouseenter", layer, function() {
        map.getCanvas().style.cursor = "pointer";
      });

      map.on("mouseleave", layer, function() {
        map.getCanvas().style.cursor = "";
      });
    }
  });
}
