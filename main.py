import os
import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"msg": "Hello from Railway!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # <- Yahan se Railway ka port pick hoga
    uvicorn.run("main:app", host="0.0.0.0", port=port)
