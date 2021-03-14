import sys
from bokeh.io import show
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, CustomJS
from bokeh.models import Select
from bokeh.models.tools import HoverTool
from bokeh.plotting import figure
import pandas as pd

def visualize(filename):
    df = pd.read_csv(filename)
    ds = ColumnDataSource(df)
    p = figure(toolbar_location="above", x_axis_type="linear")
    # p.add_tools(HoverTool(tooltips=[("x")]))

    line_renderer = p.line('x', 'ground_truth', source=ds)
    handler = CustomJS(args=dict(line_renderer=line_renderer),
                       code="""
        line_renderer.glyph.y = {field: cb_obj.value};
    """)

    select = Select(title="Model Type:", options=list(df.columns))
    select.js_on_change('value', handler)

    show(column(select, p))


if __name__ == "__main__":
    filename = sys.argv[1]
    visualize(filename)
