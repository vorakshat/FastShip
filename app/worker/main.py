from datetime import datetime

from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference

from app.worker.tasks import background_task, send_mail

app = FastAPI()


@app.get("/test")
def test():
    send_mail.delay(
        recipients=["akshatnvora05@gmail.com"],
        subject="Test mail",
        body="...",
    )
    now = datetime.now()  # noqa: DTZ005
    background_task.delay(
        name=f"Background Task {now.second}",
        data={"min": now.minute, "sec": now.second},
    )
    return {"status": "success", "message": "Tasks scheduled"}


@app.get("/scalar", include_in_schema=False)
def get_scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url or "/openapi.json",
        title="Scalar API",
    )