from starlette.requests import Request


def flash(request: Request, message: str, category: str = "info") -> None:
    if "_flashes" not in request.session:
        request.session["_flashes"] = []
    request.session["_flashes"].append({"message": message, "category": category})


def get_flashed_messages(request: Request) -> list[dict]:
    messages = request.session.pop("_flashes", [])
    return messages
