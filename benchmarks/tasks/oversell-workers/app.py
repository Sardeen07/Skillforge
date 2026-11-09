"""WSGI entry point: POST /buy reserves one mug."""
import shop

DB_PATH = "shop.db"


def application(environ, start_response):
    ok = shop.buy(DB_PATH, "mug")
    start_response("200 OK" if ok else "409 Conflict", [("Content-Type", "text/plain")])
    return [b"reserved" if ok else b"sold out"]
