from fastapi import FastAPI, Request, Response, WebSocket, File, UploadFile, HTTPException
from fastapi.templating import Jinja2Templates
import qrcode
import qrcode.image.svg
from fastapi.staticfiles import StaticFiles
import os
from pydantic import ConfigDict, BaseModel, Field, EmailStr

from typing import Optional, List
from pydantic.functional_validators import BeforeValidator

from starlette.websockets import WebSocketDisconnect
from typing_extensions import Annotated
from supabase_file import create_supabase_client

import concurrent.futures
import gzip
from datetime import datetime, timedelta

from fastapi_sessions.frontends.implementations import SessionCookie, CookieParameters
from fastapi_sessions.backends import InMemoryBackend
from fastapi_sessions.session_verifier import SessionVerifier
from uuid import UUID, uuid4

supabase = create_supabase_client()
app = FastAPI()

static_dir = os.path.join(os.path.dirname(__file__), "static/images")
app.mount("/images", StaticFiles(directory=static_dir), name="images")

templates = Jinja2Templates(directory="templates")

class SessionData(BaseModel):
    session_id: str
    timestamp: str

cookie_params = CookieParameters(max_age = 24*60*60)

cookie = SessionCookie(
    cookie_name="session",
    cookie_params=cookie_params,
    identifier="session_id",
    auto_error=True,
    secret_key="secret"
)
backend = InMemoryBackend[UUID, SessionData]()

class BasicVerifier(SessionVerifier[UUID, SessionData]):
    def __init__(
        self,
        *,
        identifier: str,
        auto_error: bool,
        backend: InMemoryBackend[UUID, SessionData],
        auth_http_exception: HTTPException,
    ):
        self._identifier = identifier
        self._auto_error = auto_error
        self._backend = backend
        self._auth_http_exception = auth_http_exception

    @property
    def identifier(self):
        return self._identifier

    @property
    def backend(self):
        return self._backend

    @property
    def auto_error(self):
        return self._auto_error

    @property
    def auth_http_exception(self):
        return self._auth_http_exception

    def verify_session(self, model: SessionData) -> bool:
        session_age = datetime.now(datetime.timezone.utc) - model.created_at  # Calculate session age
        if session_age > timedelta(hours=24):  # Check if session is older than 24 hours
            return False  # Session has expired
        return True


verifier = BasicVerifier(
    identifier="general_verifier",
    auto_error=True,
    backend=backend,
    auth_http_exception=HTTPException(status_code=403, detail="invalid session"),
)

# from bson import ObjectId
# import motor.motor_asyncio
# from db.supabase import create_supabase_client

# client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"])
# db = client.get_database("college")
# student_collection = db.get_collection("students")
# PyObjectId = Annotated[str, BeforeValidator(str)]


# class StudentModel(BaseModel):
#     """
#     Container for a single student record.
#     """

#     # The primary key for the StudentModel, stored as a `str` on the instance.
#     # This will be aliased to `_id` when sent to MongoDB,
#     # but provided as `id` in the API requests and responses.
#     id: Optional[PyObjectId] = Field(alias="_id", default=None)
#     text: Optional[str] = None
#     session_id = str
#     timestamp: str
    
#     model_config = ConfigDict(
#         populate_by_name=True,
#         arbitrary_types_allowed=True,
#         json_schema_extra={
#             "example": {
#                 "name": "Jane Doe",
#                 "email": "jdoe@example.com",
#                 "course": "Experiments, Science, and Fashion in Nanophotonics",
#                 "gpa": 3.0,
#             }
#         },
#     )

# class StudentCollection(BaseModel):
#     """
#     A container holding a list of `StudentModel` instances.

#     This exists because providing a top-level array in a JSON response can be a [vulnerability](https://haacked.com/archive/2009/06/25/json-hijacking.aspx/)
#     """

#     students: List[StudentModel]

@app.get("/")
async def root(request: Request):
    eleena = "Eleena"
    img = qrcode.make('http://www.google.com/', image_factory=qrcode.image.svg.SvgImage)

    filename = os.path.join(static_dir, "qr.svg")
    actualfilepath = "/images/qr.svg"
    with open(filename, 'wb') as qr:
        img.save(qr)
    
    return templates.TemplateResponse("fileupload.html", {"request": request, "eleena": eleena, "filename":actualfilepath})

@app.post("/create_session/{name}")
async def create_session(response: Response, name: Optional[str] = None):
    session = uuid4()
    data = SessionData(username=name if name else "anonymous", created_at=datetime.now(datetime.timezone.utc))
    await backend.create(session, data)
    cookie.attach_to_response(response, session)
    return f"created session for {name}"

@app.get("/whoami", dependencies=[Depends(cookie)])
async def whoami(session_data: SessionData = Depends(verifier)):
    return session_data

@app.post("/delete_session")
async def del_session(response: Response, session_id: UUID = Depends(cookie)):
    await backend.delete(session_id)
    cookie.delete_from_response(response)
    return "deleted session"

def compress_and_upload(part, part_filename, content_type):
    compressed_part = gzip.compress(part)
    supabase.storage.from_("file_storage").upload(file=compressed_part, path=f"public/{part_filename}", file_options={"content-type": content_type})

@app.post("/")
async def upload_file(request: Request, file: UploadFile = File(...)):
    file_content = await file.read()
    print(len(file_content)) 
    max_parts = 8
    part_size = len(file_content) // max_parts

    if len(file_content) > part_size:
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            num_parts = min(max_parts, (len(file_content) + part_size - 1) // part_size)
            for i in range(num_parts):
                part = file_content[i*part_size:(i+1)*part_size]
                part_filename = f"{file.filename}_{i}.gz"
                print(f"{datetime.now()} - Submitting part {i+1}/{num_parts}: {part_filename}")
                content_type = file.content_type
                futures.append(executor.submit(compress_and_upload, part, part_filename, content_type))
            
            concurrent.futures.wait(futures)
    else:
        supabase.storage.from_("file_storage").upload(file=file_content, path=f"public/{file.filename}", file_options={"content-type": file.content_type})

    return templates.TemplateResponse("fileupload.html", {"request": request, "filename": file.filename})#file.filename, "contents": contents}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try: 
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        print("Client disconnected")