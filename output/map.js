function makeGraph(width, height, data) {
  const gap = 1;
  var draw = SVG().size(width, height);

  const graph_height = height - 3;
  const graph_width = width - 3;
  const max_value = Math.max(...data);
  const bar_width = graph_width / data.length - gap;
  for (let i = 0; i < data.length; i++) {
    const bar_height = (data[i] / max_value) * graph_height;
    draw
      .rect(bar_width, bar_height)
      .move(i * (bar_width + gap) + 2, graph_height - bar_height)
      .fill('#d44');
  }
  draw
    .line(1, height - 3, width, height - 3)
    .stroke({width: 0.5, color: '#bbb'});
  return draw;
}

function styleExpression(data, propname, colours, zero_colour) {
  const max_prevalence = Math.max(
    ...Object.entries(data).map(v => v[1]['prevalence']),
    15/100000 // Maximum won't go below 15 per 100,000
  );

  var expression = ['match', ['get', propname]];

  for (const gss_id in data) {
    var colour = null;
    if (data[gss_id]['cases'] == 0) {
      colour = zero_colour;
    } else {
      const idx = Math.round(
        (data[gss_id]['prevalence'] / max_prevalence) * (colours.length - 1),
      );
      colour = colours[idx];
    }
    expression.push(gss_id, colour);
  }

  expression.push('#ffffff');
  return expression;
}

function popupRenderer(map, data, name_field, gss_field) {
  return function(e) {
    var props = e.features[0].properties;
    let html = '<h3>' + props[name_field] + '</h3>';

    let item = data[props[gss_field]];
    html += '<table>';

    if (item['cases']) {
      html += '<tr><th>Weekly cases</th><td>' + item['cases'] + '</td></tr>';
    }

    html +=
      '<tr><th>Prevalence</th><td>' +
      (item['prevalence'] * 100000).toFixed(2) +
      ' per 100,000</td></tr>';
    html += '</table>';

    let div = window.document.createElement('div');
    div.innerHTML = html;

    if (item['history']) {

      let graph = makeGraph(200, 30, item['history']);
      div.appendChild(graph.node);
    }

    new mapboxgl.Popup()
      .setLngLat(e.lngLat)
      .setDOMContent(div)
      .addTo(map);
  };
}

function initMap(data) {
  var map = new mapboxgl.Map({
    container: 'map',
    style: 'style.json',
    center: [-3.1, 55.5],
    zoom: 5,
    customAttribution:
      '<a href="https://geoportal.statistics.gov.uk/datasets/local-authority-districts-december-2019-boundaries-uk-bfc">Contains OS data © Crown copyright and database right 2019</a>',
    maxBounds: [[-17.1, 49.4], [11.2, 61.4]],
  });
  window.map = map;

  map.touchZoomRotate.disableRotation();
  map.addControl(new mapboxgl.NavigationControl({showCompass: false}));

  map.on('load', () => {

    const opacity_func = ["interpolate", ["exponential", 1.4], ["zoom"],
      5, 0.85,
      12, 0.5
    ];

    map.addLayer(
      {
        id: 'england_cases',
        type: 'fill',
        // Filter to restrict to English LAs only
        filter: ['==', ['slice', ['get', 'ctyua19cd'], 0, 1], 'E'],
        source: 'areas',
        'source-layer': 'utla',
        paint: {
          'fill-color': styleExpression(
            data.england,
            'ctyua19cd',
            ['#fef0d9','#fdd49e','#fdbb84','#fc8d59','#e34a33','#b30000'],
            '#ececec',
          ),
          'fill-opacity': opacity_func,
        },
      },
      'la_boundary',
    );

    map.addLayer(
      {
        id: 'wales_cases',
        type: 'fill',
        // Filter to restrict to Welsh LAs only
        filter: ['==', ['slice', ['get', 'lad19cd'], 0, 1], 'W'],
        source: 'areas',
        'source-layer': 'local_authorities',
        paint: {
          'fill-color': styleExpression(
            data.wales,
            'lad19cd',
            ['#edf8fb','#bfd3e6','#9ebcda','#8c96c6','#8856a7','#810f7c'],
            '#ececec',
          ),
          'fill-opacity': 0.7,
        },
      },
      'la_boundary',
    )

    map.addLayer(
      {
        id: 'scot_cases',
        type: 'fill',
        source: 'areas',
        'source-layer': 'scottish_health_boards',
        paint: {
          'fill-color': styleExpression(
            data.scotland,
            'HBCode',
            ['#edf8fb','#b2e2e2','#66c2a4','#238b45'],
            '#ececec',
          ),
          'fill-opacity': 0.7,
        },
      },
      'la_boundary',
    );

    map.on(
      'click',
      'england_cases',
      popupRenderer(map, data.england, 'ctyua19nm', 'ctyua19cd'),
    );
    map.on(
      'click',
      'wales_cases',
      popupRenderer(map, data.wales, 'lad19nm', 'lad19cd'),
    );
    map.on(
      'click',
      'scot_cases',
      popupRenderer(map, data.scotland, 'HBName', 'HBCode'),
    );

    for (const layer of ['la_cases', 'scot_cases', 'wales_cases']) {
      map.on('mouseenter', layer, function() {
        map.getCanvas().style.cursor = 'pointer';
      });

      map.on('mouseleave', layer, function() {
        map.getCanvas().style.cursor = '';
      });
    }
  });
}
