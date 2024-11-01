import axios from "axios";
import { createSignal, For, Index } from "solid-js";

export default function Home() {
    const [routeList, setRouteList] = createSignal([]);
    const [pointName, setPointName] = createSignal("");

    const add = () => {
        setRouteList(
            routeList().concat([
                { name: pointName(), weather: null, found: null },
            ]),
        );
        setPointName("");
    };

    const check = async () => {
        let points = [...routeList()];
        for (let i = 0; i < points.length; i++) {
            try {
                let response = await axios.get(
                    "http://127.0.0.1:5000/accu/currentconditions",
                    {
                        params: {
                            location: points[i].name,
                        },
                    },
                );
                points[i].weather = response.data;
                points[i].found = true;
                if (response.data.status === "error") {
                    points[i].found = false;
                }
            } catch (error) {
                points[i].found = false;
            }
        }
        setRouteList([]);
        setRouteList(points);
    };

    const pointStatus = (point) => {
        console.log(point);
        if (point.found === null || point.weather === null) {
            return { color: "#f3f3f3", status: "" };
        }
        if (point.found === false) {
            return { color: "#FF6161", status: "- Не удалось получить данные" };
        }
        if (point.weather.favorable) {
            return {
                color: "#EA8181",
                status: `- ${point.weather.description}`,
            };
        }
        return {
            color: "#8AFF75",
            status: `- ${point.weather.description}`,
        };
    };

    return (
        <main>
            <div class="content">
                <div class="header">
                    <h1>Forecasty</h1>
                </div>
                <div class="content">
                    <div class="router-form">
                        <input
                            class="enter-point"
                            name="enter-point"
                            type="text"
                            placeholder="Введите название города"
                            value={pointName()}
                            onInput={(event) =>
                                setPointName(event.target.value)
                            }
                        />
                        <button class="add-btn" onClick={add}>
                            +
                        </button>
                    </div>
                    <div class="route-list">
                        <For each={routeList()}>
                            {(item) => (
                                <button
                                    class="route-box"
                                    style={{
                                        "background-color":
                                            pointStatus(item).color,
                                    }}
                                >
                                    {item.name} {pointStatus(item).status}
                                </button>
                            )}
                        </For>
                    </div>
                    <button
                        class="check-btn"
                        onClick={async () => await check()}
                    >
                        Проверить
                    </button>
                    <p>
                        <span>
                            Зеленым выделены города с благоприятными погодными
                            условиями.
                        </span>
                        <span>Светло-красным - с неблагоприятными.</span>
                        <span>
                            Контрастным красным выделены города, данные по
                            которым получить не удалось.
                        </span>
                    </p>
                </div>
            </div>
        </main>
    );
}
