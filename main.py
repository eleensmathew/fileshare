from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import qrcode
import qrcode.image.svg
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

static_dir = os.path.join(os.path.dirname(__file__), "static/images")
app.mount("/images", StaticFiles(directory=static_dir), name="images")

templates = Jinja2Templates(directory="templates")

@app.get("/")
async def root(request: Request):
    eleena = "Eleena"
    img = qrcode.make('http://www.google.com/', image_factory=qrcode.image.svg.SvgImage)

    filename = os.path.join(static_dir, "qr.svg")
    actualfilepath = "/images/qr.svg"
    with open(filename, 'wb') as qr:
        img.save(qr)
    
    return templates.TemplateResponse("fileupload.html", {"request": request, "eleena": eleena, "filename":actualfilepath})

@app.post("/")
async def root(request: Request):
    form = await request.form()
    for form_data in form:
        print("PP", form_data)
    file = form["filename"]
    
    return templates.TemplateResponse("fileupload.html", {"request": request, "filename": "lop"})#file.filename, "contents": contents}