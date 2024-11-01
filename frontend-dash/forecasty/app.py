import json
import requests
import pandas as pd
import plotly.graph_objs as go

from collections import OrderedDict
from dash import Dash, State, Input, Output, html, ctx, dcc, callback

API_URL = "http://forecasty-backend:5000"

# Первый параметр: колонка, обозначающая погодное условие в api
# Второй параметр: кортеж, обозначающий отображение погодного условия в графике
GRAPH_PARAMS = OrderedDict(
    [
        ("temperature_c", ("Температура по городам", "Температура (°C)")),
        ("humidity_percent", ("Влажность по городам", "Влажность (%)")),
        (
            "precipitation_probability_percent",
            ("Вероятность осадков по городам", "Вероятность осадков (%)"),
        ),
        ("wind_speed_ms", ("Скорость ветра по городам", "Скорость ветра (м/с)")),
    ]
)

app = Dash(__name__)

app.layout = [
    html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [html.Div(html.H1("Forecasty"), className="header")],
                                className="content",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="enter-point",
                                                className="enter-point",
                                                name="enter-point",
                                                type="text",
                                                placeholder="Введите название города",
                                            ),
                                            html.Button(
                                                "+", id="add-btn", className="add-btn"
                                            ),
                                        ],
                                        className="router-form",
                                    ),
                                    html.Div(
                                        [], id="route-list", className="route-list"
                                    ),
                                    html.Div(
                                        [
                                            html.Button(
                                                "Погода сейчас",
                                                id="current-btn",
                                                className="check-btn",
                                            ),
                                            html.Button(
                                                "Прогноз на 5 дней",
                                                id="forecast-btn",
                                                className="check-btn",
                                                style={"marginLeft": "5px"},
                                            ),
                                        ]
                                    ),
                                ],
                                className="content",
                            ),
                        ],
                        className="content",
                    ),
                    html.Div(id="map", style={"display": "flex", "marginLeft": "40px"}),
                ],
                className="row-content",
            ),
            html.Div(id="graph-list", style={"display": "flex", "marginLeft": "40px"}),
        ],
        className="content",
    ),
    dcc.Store(id="route-store"),
    dcc.Store(id="forecast-store"),
]


@callback(
    Output("route-store", "data"),
    Input("route-store", "data"),
    State("enter-point", "value"),
    Input("add-btn", "n_clicks"),
    Input("current-btn", "n_clicks"),
)
def handle_routes(data, point_name, add_btn_clicks, current_btn_clicks):
    match ctx.triggered_id:
        case "add-btn":
            return json.dumps(
                (
                    json.loads(data)
                    + [
                        {
                            "name": point_name,
                            "weather": None,
                            "found": None,
                        }
                    ]
                )
                if add_btn_clicks != None
                else []
            )
        case "current-btn":
            if current_btn_clicks == None:
                return json.dumps([])

            baseurl = f"{API_URL}/accu/currentconditions"

            routes = json.loads(data)

            for route in routes:
                try:
                    response = requests.get(baseurl, params={"location": route["name"]})
                    if (
                        response.status_code == 200
                        and response.text.find("error") == -1
                    ):
                        route["weather"] = json.loads(response.text)
                        route["found"] = True
                    else:
                        route["found"] = False
                except requests.exceptions.RequestException as e:
                    route["found"] = False

            return json.dumps(routes)
    return json.dumps([])


@callback(Output("enter-point", "value"), Input("add-btn", "n_clicks"))
def clear_point_entry(_n_clicks):
    return ""


def get_point_status(point):
    if point["found"] is None and point["weather"] is None:
        return {"color": "#f3f3f3", "status": ""}
    if point["found"] is False:
        return {"color": "#FF6161", "status": "- Не удалось получить данные"}
    if point["weather"]["favorable"]:
        return {"color": "#EA8181", "status": f"- {point['weather']['description']}"}
    return {"color": "#8AFF75", "status": f"- {point['weather']['description']}"}


@callback(
    Output("route-list", "children"),
    Input("route-store", "data"),
)
def update_route_list(data):
    return [
        html.Button(
            f'{item["name"]} {get_point_status(item)["status"]}',
            className="route-box",
            style={"backgroundColor": get_point_status(item)["color"]},
        )
        for item in json.loads(data)
    ]


def create_map_data(routes):
    latitudes = []
    longitudes = []
    names = []
    hover_texts = []

    for route in routes:
        weather = route["weather"]

        name = weather["geo"]["name"]
        conditions = weather["conditions"]
        description = weather["description"]

        latitudes.append(route["weather"]["geo"]["latitude"])
        longitudes.append(route["weather"]["geo"]["longitude"])

        names.append(name)

        hover_texts.append(
            f"{name}<br>"
            f"<br>{description}<br><br>"
            f"Температура: {conditions['temperature_c']:.2f} °C<br>"
            f"Влажность: {conditions['humidity_percent']:.2f}%<br>"
            f"Осадки: {conditions['precipitation_probability_percent']:.2f}%<br>"
            f"Скорость ветра: {conditions['wind_speed_ms']:.2f} м/с<br>"
        )

    trace_points = go.Scattermapbox(
        lat=latitudes,
        lon=longitudes,
        mode="markers+lines",
        marker=dict(size=10, color="blue"),
        text=hover_texts,
        hoverinfo="text",
        name="Города",
    )

    return [trace_points]


@callback(
    Output("map", "children"),
    Input("route-store", "data"),
)
def render_map(raw_routes):
    routes = [route for route in json.loads(raw_routes) if route["weather"]]

    if not routes:
        return []

    first_geo = routes[0]["weather"]["geo"]

    layout = go.Layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=first_geo["latitude"], lon=first_geo["longitude"]),
            zoom=3,
        ),
        title="Города с текущей погодой",
    )

    return dcc.Graph(
        id="map-graph",
        figure=go.Figure(data=create_map_data(routes), layout=layout),
        config={"displayModeBar": False},
        style={"height": "75vh"},
    )


@callback(
    Output("forecast-store", "data"),
    Input("forecast-btn", "n_clicks"),
    Input("route-store", "data"),
)
def fullfill_forecast(n_clicks, route_data):
    if n_clicks == None:
        return json.dumps({})

    baseurl = f"{API_URL}/accu/forecast/5days"
    routes = json.loads(route_data)

    dump = {}

    for route in routes:
        try:
            response = requests.get(baseurl, params={"location": route["name"]})
            if response.status_code == 200 and response.text.find("error") == -1:
                raw_data = json.loads(response.text)
                dump[route["name"]] = []
                for unit in raw_data["units"]:
                    city = {"date": unit["date"]}
                    for condition, value in unit["conditions"].items():
                        city[condition] = value
                    dump[route["name"]].append(city)
        except requests.exceptions.RequestException:
            pass

    return json.dumps(dump)


def make_flex_row(elems, row_length, group_style={}):
    return list(
        map(
            lambda group: html.Div(group, style=group_style),
            zip(*[iter(elems)] * row_length, strict=True),
        )
    )


@app.callback(
    Output("graph-list", "children"),
    Input("forecast-store", "data"),
)
def render_graphs(raw_data):
    colors = [
        "#FF5733",
        "#33FF57",
        "#3357FF",
        "#FF33A8",
        "#A833FF",
    ]

    traces = {column: [] for column in GRAPH_PARAMS.keys()}
    graphs = []

    data = json.loads(raw_data)

    if not data:
        return []

    for i, (city, city_data) in enumerate(data.items()):
        df = pd.DataFrame(city_data)

        for column in traces.keys():
            traces[column].append(
                go.Scatter(
                    x=df["date"],
                    y=df[column],
                    mode="lines+markers",
                    name=city,
                    line=dict(color=colors[i % len(colors)]),
                )
            )

    for column, trace_list in traces.items():
        graphs.append(
            dcc.Graph(
                figure=go.Figure(
                    data=trace_list,
                    layout=go.Layout(
                        title=GRAPH_PARAMS[column][0],
                        xaxis={"title": "Дата"},
                        yaxis={"title": GRAPH_PARAMS[column][1]},
                    ),
                ),
                config={"displayModeBar": False},
            )
        )

    return make_flex_row(
        graphs,
        2,
        group_style={
            "width": "40vw",
        },
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="3000", debug=True)
