import os

import uvicorn
from fasthtml import FastHTML

app = FastHTML()


@app.get("/")
def index():
    return "<p>Aikana</p>"


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    main()
