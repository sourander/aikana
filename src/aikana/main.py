import os

import uvicorn
from fasthtml.common import FastHTML

from aikana.semester import routes as semester_routes
from aikana.shared import layout

app = FastHTML(title="Aikana", hdrs=layout.extra_headers())
semester_routes.register_routes(app)


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    main()
