from jinja2 import Environment, FileSystemLoader, select_autoescape
import json
from datetime import datetime
from bokeh.embed import json_item
from bokeh.themes import Theme

env = Environment(
    loader=FileSystemLoader("templates"), autoescape=select_autoescape(["html", "xml"])
)

theme = Theme("./theme.yaml")


def render_template(name, graphs={}, **kwargs):
    print(f"Rendering {name}...")

    graphs_data = json.dumps(
        [json_item(graph, name, theme=theme) for name, graph in graphs.items()]
    )

    generated = datetime.now()

    template = env.get_template(name)
    with open(f"output/{name}", "w") as f:
        f.write(template.render(graphs=graphs_data, generated=generated, **kwargs))
