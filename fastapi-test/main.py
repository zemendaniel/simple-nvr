from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.staticfiles import StaticFiles
from parse_config import conf
from media import MediaCapture


@asynccontextmanager
async def lifespan(app):
    yield
    await capture.shutdown()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
capture = MediaCapture(conf['camera']['url'], conf['camera']['fps'], conf['camera']['width'], conf['camera']['height'])


@app.get('/')
async def root():
    return RedirectResponse(url='/static/index.html')


@app.post("/offer")
async def offer(request: Request):
    params = await request.json()
    sdp, type_ = await capture.handle_offer(params)

    return JSONResponse({
        "sdp": sdp,
        "type": type_
    })


