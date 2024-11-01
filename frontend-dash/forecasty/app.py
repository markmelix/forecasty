import json
import requests
import pandas as pd
import plotly.graph_objs as go

from dash import Dash, State, html, ctx, dcc, callback, Output, Input

app = Dash(__name__)

app.layout = [
    html.Div([html.Div(html.H1("Forecasty"), className="header")], className="content"),
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
                    html.Button("+", id="add-btn", className="add-btn"),
                ],
                className="router-form",
            ),
            html.Div([], id="route-list", className="route-list"),
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
            html.Div(
                [
                    # График температуры
                    dcc.Graph(id="temperature-graph", config={"displayModeBar": False}),
                    # График влажности
                    dcc.Graph(id="humidity-graph", config={"displayModeBar": False}),
                    # График вероятности осадков
                    dcc.Graph(
                        id="precipitation-graph", config={"displayModeBar": False}
                    ),
                    # График скорости ветра
                    dcc.Graph(id="wind-speed-graph", config={"displayModeBar": False}),
                ],
                id="graph-list",
            ),
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

            baseurl = "http://localhost:5000/accu/currentconditions"

            routes = json.loads(data)

            for route in routes:
                try:
                    response = requests.get(baseurl, params={"location": route["name"]})
                    if response.status_code == 200:
                        route["weather"] = json.loads(response.text)
                        route["found"] = True
                    else:
                        route["found"] = False
                except requests.exceptions.RequestException:
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


# Данные по нескольким городам (примерная структура)
# Предположим, что они были получены ранее от API и сохранены в переменной `all_city_data`
all_city_data = {
    "Москва": [
        {
            "date": "2024-11-01T07:00:00+03:00",
            "temperature_c": 5.6,
            "humidity_percent": 94,
            "precipitation_probability_percent": 94,
            "wind_speed_ms": 11.5,
        },
        {
            "date": "2024-11-02T07:00:00+03:00",
            "temperature_c": -1.1,
            "humidity_percent": 84,
            "precipitation_probability_percent": 1,
            "wind_speed_ms": 17.3,
        },
        # добавьте другие дни
    ],
    "Санкт-Петербург": [
        {
            "date": "2024-11-01T07:00:00+03:00",
            "temperature_c": 7.2,
            "humidity_percent": 89,
            "precipitation_probability_percent": 76,
            "wind_speed_ms": 10.2,
        },
        {
            "date": "2024-11-02T07:00:00+03:00",
            "temperature_c": 0.3,
            "humidity_percent": 82,
            "precipitation_probability_percent": 20,
            "wind_speed_ms": 15.0,
        },
        # добавьте другие дни
    ],
    # добавьте другие города
}


# Функция для обработки данных: конвертирует данные города в DataFrame
def process_city_data(city_data):
    return pd.DataFrame(city_data)


# Коллбэк для обновления графиков
@app.callback(
    [
        Output("temperature-graph", "figure"),
        Output("humidity-graph", "figure"),
        Output("precipitation-graph", "figure"),
        Output("wind-speed-graph", "figure"),
    ],
    Input(
        "temperature-graph", "id"
    ),  # Искусственный Input для триггера обновления графиков при загрузке страницы
)
def update_graphs(_):
    colors = [
        "#FF5733",
        "#33FF57",
        "#3357FF",
        "#FF33A8",
        "#A833FF",
    ]  # Цвета для каждого города

    # Создаем графики для каждого параметра
    temperature_traces = []
    humidity_traces = []
    precipitation_traces = []
    wind_speed_traces = []

    # Обрабатываем данные по каждому городу
    for i, (city, city_data) in enumerate(all_city_data.items()):
        df = process_city_data(city_data)

        # Линии для каждого параметра (температура, влажность, осадки, ветер)
        temperature_traces.append(
            go.Scatter(
                x=df["date"],
                y=df["temperature_c"],
                mode="lines+markers",
                name=city,
                line=dict(color=colors[i % len(colors)]),
            )
        )

        humidity_traces.append(
            go.Scatter(
                x=df["date"],
                y=df["humidity_percent"],
                mode="lines+markers",
                name=city,
                line=dict(color=colors[i % len(colors)]),
            )
        )

        precipitation_traces.append(
            go.Scatter(
                x=df["date"],
                y=df["precipitation_probability_percent"],
                mode="lines+markers",
                name=city,
                line=dict(color=colors[i % len(colors)]),
            )
        )

        wind_speed_traces.append(
            go.Scatter(
                x=df["date"],
                y=df["wind_speed_ms"],
                mode="lines+markers",
                name=city,
                line=dict(color=colors[i % len(colors)]),
            )
        )

    # Фигуры графиков
    temperature_fig = go.Figure(
        data=temperature_traces,
        layout=go.Layout(
            title="Температура по городам",
            xaxis={"title": "Дата"},
            yaxis={"title": "Температура (°C)"},
        ),
    )

    humidity_fig = go.Figure(
        data=humidity_traces,
        layout=go.Layout(
            title="Влажность по городам",
            xaxis={"title": "Дата"},
            yaxis={"title": "Влажность (%)"},
        ),
    )

    precipitation_fig = go.Figure(
        data=precipitation_traces,
        layout=go.Layout(
            title="Вероятность осадков по городам",
            xaxis={"title": "Дата"},
            yaxis={"title": "Вероятность осадков (%)"},
        ),
    )

    wind_speed_fig = go.Figure(
        data=wind_speed_traces,
        layout=go.Layout(
            title="Скорость ветра по городам",
            xaxis={"title": "Дата"},
            yaxis={"title": "Скорость ветра (м/с)"},
        ),
    )

    return temperature_fig, humidity_fig, precipitation_fig, wind_speed_fig


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="3000", debug=True)