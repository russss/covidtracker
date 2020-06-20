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

function initMap(data) {
  var map = new mapboxgl.Map({
    container: 'map',
    style: 'style.json',
    center: [-1.82, 53],
    zoom: 6,
    customAttribution:
      '<a href="https://geoportal.statistics.gov.uk/datasets/local-authority-districts-december-2019-boundaries-uk-bfc">Contains OS data © Crown copyright and database right 2019</a>',
    maxBounds: [[-17.1, 49.4], [11.2, 61.4]],
  });

  map.touchZoomRotate.disableRotation();
  map.addControl(new mapboxgl.NavigationControl({showCompass: false}));

  map.on('load', () => {
    const max_prevalence = Math.max(
      ...Object.entries(data).map(v => v[1]['prevalence']),
    );

    const colours = ['#fef0d9', '#fdcc8a', '#fc8d59', '#d7301f'];
    const zero_colour = '#ececec';

    var expression = ['match', ['get', 'lad19cd']];

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

    map.addLayer(
      {
        id: 'la_cases',
        type: 'fill',
        // Filter to restrict to English LAs only at the moment
        filter: ['==', ['slice', ['get', 'lad19cd'], 0, 1], 'E'],
        source: 'local_authorities',
        'source-layer': 'local_authorities',
        paint: {
          'fill-color': expression,
          'fill-opacity': 0.7,
        },
      },
      'la_boundary',
    );

    map.on('click', 'la_cases', function(e) {
      var props = e.features[0].properties;
      let html = '<h3>' + props.lad19nm + '</h3>';

      html += '<table>';
      html +=
        '<tr><th>Weekly cases</th><td>' +
        data[props.lad19cd]['cases'] +
        '</td></tr>';
      html +=
        '<tr><th>Prevalence</th><td>' +
        (data[props.lad19cd]['prevalence'] * 100000).toFixed(2) +
        ' per 100,000</td></tr>';
      html += '</table>';

      let div = window.document.createElement('div');
      div.innerHTML = html;

      let graph = makeGraph(200, 30, data[props.lad19cd]['history']);
      div.appendChild(graph.node);

      new mapboxgl.Popup()
        .setLngLat(e.lngLat)
        .setDOMContent(div)
        .addTo(map);
    });

    map.on('mouseenter', 'la_cases', function() {
      map.getCanvas().style.cursor = 'pointer';
    });

    map.on('mouseleave', 'la_cases', function() {
      map.getCanvas().style.cursor = '';
    });
  });
}
