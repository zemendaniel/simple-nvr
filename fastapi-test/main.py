from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status
from starlette.staticfiles import StaticFiles
from parse_config import conf
from media import MediaCapture
from auth import authenticate_user, create_access_token, get_current_user


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


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token({"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/offer")
async def offer(request: Request):
    params = await request.json()
    sdp, type_ = await capture.handle_offer(params)

    return JSONResponse({
        "sdp": sdp,
        "type": type_
    })


