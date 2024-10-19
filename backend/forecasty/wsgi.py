import gunicorn.app.base


class WSGIApplication(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


if __name__ == "__main__":
    import logging
    import forecasty
    import multiprocessing

    logging.basicConfig(level=logging.INFO)

    SERVER_PORT = 5000
    WORKERS = (multiprocessing.cpu_count() * 2) + 1

    WSGIApplication(
        forecasty.make_app(),
        {
            "bind": f"0.0.0.0:{SERVER_PORT}",
            "workers": WORKERS,
            "reload": True,
        },
    ).run()
