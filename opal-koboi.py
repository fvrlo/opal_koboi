'''
Welcome to opal-koboi! A quick and dirty (Fast)API for Tautulli, Plex, and IMDB.

    These services are funny, because their APIs all suck. Tautulli uses JSON, but it's all query instead of path,
    Plex returns XML for who knows what reason, and IMDB is owned by Amazon so it sucks and I don't want to pay for it.
    Solution? Write a wrapper using existing Python interpreters of them to standardize and utilize them in a way that
    doesn't make me loathe humanity.

Start API server:       hypercorn opal-koboi:app --reload
Dynamic Swagger docs:   http://127.0.0.1:8000/docs
Dynamic Redoc docs:     http://127.0.0.1:8000/redoc

Potential Modules
 - MakeMKV Automator    | python-makemkv    | https://python-makemkv.readthedocs.io/en/latest/usage/
 - Process Images       | Pillow            | https://pillow.readthedocs.io/en/stable/
 - Glitch Images        | glitch-this       | https://github.com/TotallyNotChase/glitch-this/wiki/Documentation:-The-glitch-this-library

N8N Node Creation:      https://docs.n8n.io/integrations/creating-nodes/

Ability List Planner:
 - Convert between Markdown, JSON, XML, and YAML
 - Webhooks for Plex, Tautulli, and New Files
 - Retrieve the "{blank} Of The Day": Songs, Lyrics, Florence, Movie, Shot, Photo
 - Color
     - Retrieve and store brand colors, palettes, and colorschemes
     - Conversions between HSV, RGB, Hexcode, Colorspaces, Vp-p, and 255-color
'''

def specFinder(spec):
    if importlib.util.find_spec(spec) == None: raise SystemExit(f"Missing non-import module: {spec}")

# <--- Built-in Module Imports --->
#   --> These come standard with Python, so there's no risk of a missing installation. I assume. Hopefully.
import os               # https://docs.python.org/3/library/os.html
import re               # https://docs.python.org/3/library/re.html
import io               # https://docs.python.org/3/library/io.html
import sys              # https://docs.python.org/3/library/sys.html
import time             # https://docs.python.org/3/library/time.html
import json             # https://docs.python.org/3/library/json.html
import typing           # https://docs.python.org/3/library/typing.html
import datetime         # https://docs.python.org/3/library/datetime.html
import configparser     # https://docs.python.org/3/library/configparser.html

# <--- Required Non-Imports --->
#   --> These need to be on the system, but are only for other packages or external use.
specFinder("hypercorn") # https://hypercorn.readthedocs.io/en/latest/
specFinder("networkx")  # https://networkx.org/
specFinder("numpy")     # http://www.numpy.org/

# <--- Processing Module Imports --->
#   --> There is a possibility that these modules are not installed, so we check for import and exit if it fails to do so.
try:
    import requests     # https://requests.readthedocs.io/en/latest/
    import pydantic     # https://docs.pydantic.dev/
    import pandas       # https://pandas.pydata.org/docs/
    import fastapi      # https://fastapi.tiangolo.com/
    import colormath    # https://python-colormath.readthedocs.io/en/latest/index.html
    import path         # https://github.com/jaraco/path
    # Wrappers for Plex, Tautulli, and IMDB:
    import plexapi      # https://python-plexapi.readthedocs.io/en/latest/
    import tautulli     # https://pytulli.readthedocs.io/en/latest/
    import imdb         # https://cinemagoer.readthedocs.io/en/latest/
except ImportError as importException:
    raise SystemExit(f"Missing processing module: {importException}")

# <--- Shortcuts --->
#   --> If you're a faithful standardization follower, skip this part.
canBe = typing.Union




#   --> Get Directory stuff (files, extensions, etc.)
def getDir(dirName):
    listOfFile = os.listdir(dirName)
    allFiles, extensions = list(), list()
    for entry in listOfFile:
        fullPath = os.path.join(dirName, entry)
        if os.path.isdir(fullPath): allFiles = allFiles + getFileList(fullPath)
        else: allFiles.append(fullPath)
    
    for x in allFiles:
        ext = os.path.splitext(x)[-1].lower()
        if ext not in extensions: extensions.append(ext)

def ms2length(ms):
    xmin, xsec = divmod(int(ms/1000), 60)
    xhou, xmin = divmod(xmin, 60)
    return f"{xhou}h{xmin}m{xsec}s"

def mkvinfo(file = "/file.mkv"):
    sprun = sp.run(['ffprobe','-of','json','-show_entries', 'format:stream', file], stdout=sp.PIPE, stderr=sp.PIPE, universal_newlines=True)
    results = json.loads(sprun.stdout)
    return [sprun.stdout, results['format']['tags'], [res['tags'] for res in results['streams']]]
    # 1. Metadata JSON, 2. Title & Description, 3. Per-stream metadata

def bool_or_str(varia):
	if type(varia) == bool:
		if varia: return "True"; else: return "False"
	else:
		if varia in ["True","true","1",1,"yes","Yes","y"]: return True; else: return False

def dict_compare(d1, d2):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    shared = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o : (d1[o], d2[o]) for o in shared if d1[o] != d2[o]}
    same = set(o for o in shared if d1[o] == d2[o])
    return added, removed, modified, same, shared








class CColor(BaseModel): # Common Color
    r_255 = pydantic.conint(ge=0,le=255)
    g_255 = pydantic.conint(ge=0,le=255)
    b_255 = pydantic.conint(ge=0,le=255)
    r_one = pydantic.confloat(ge=0,le=1,allow_inf_nan=False)
    g_one = pydantic.confloat(ge=0,le=1,allow_inf_nan=False)
    b_one = pydantic.confloat(ge=0,le=1,allow_inf_nan=False)
    hex_6 = str
    hex_7 = str
    def __init__(self, rgb):
        if type(rgb) is tuple: # Takes a tuple in the form (R, G, B)
            if type(r) == float:
                r_one, g_one, b_one = rgb
                r_255 = int(r * float(255))
                g_255 = int(g * float(255))
                b_255 = int(b * float(255))
            elif type(r) == int:
                r_255, g_255, b_255 = rgb
                r_one = float(r / float(255))
                g_one = float(g / float(255))
                b_one = float(b / float(255))
            self.value_hex = '%02x%02x%02x' % (r_255, g_255, b_255)
        else: # Takes a hexcode with or without hash
            if len(rgb) == 6: self.hex_6, self.hex_7 = rgb, str("#",str(rgb))
            elif len(rgb) == 7: self.hex_6, self.hex_7 = rgb.lstrip('#'), str(rgb)
            self.r_255, self.g_255, self.b_255 = tuple(int(self.hex_6[i:i + 6 // 3], 16) for i in range(0, 6, 6 // 3))

class ColorObject:
    def __init__(self,r,g,b):
        if type(r)
        self.rgbmode = 
        self.r = r
        self.g = g
        self.b = b
    def __str__(self):
        return f"{self.r},{self.g},{self.b}"
    def bw_unweight(rgb):
        return (rgb.r / 3) + (rgb.g / 3) + (rgb.b / 3)
    def bw_weighted(rgb):
        return colorsys.rgb_to_yiq(a,b,c)[0]


'''
https://stackoverflow.com/questions/65681367/declaring-a-variable-as-hex-in-python
https://docs.pydantic.dev/usage/types/#constrained-types
https://python-colormath.readthedocs.io/en/latest/color_objects.html
'''




# <--- Class Definitions --->
#   --> Helps to keep items in a static shape, ensures data is as it should be.
class Item(pydantic.BaseModel):
    name: str
    price: float
    is_offer: canBe[bool, None] = None   # Can be a boolean or None


# <--- API Authentication --->
#   --> Defines a security schema, based on this -> https://testdriven.io/tips/6840e037-4b8f-4354-a9af-6863fb1c69eb/
def api_key_auth(api_key: str = fastapi.Depends(fastapi.security.OAuth2PasswordBearer(tokenUrl="token"))):
    if api_key not in ["123456789123456789"]: 
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED,detail="Forbidden")


# <--- API Definition --->
app = fastapi.FastAPI()



Tautulli = tautulli.api.object_api.ObjectAPI(TautulliBaseURL,TautulliAPIKey) # https://pytulli.readthedocs.io/en/latest/documentation.html#the-objectapi-class

@app.get("/tautulli")
async def activity(session_key=None, session_id=None):
    return {Tautulli.activity(session_key,session_id)}







@app.get("/protected", dependencies=[Depends(api_key_auth)])
def add_post() -> dict:
    return { "data": "You used a valid API key." }

@app.get("/")
async def read_root():
    return {"text": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: canBe[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    return {"item_name": item.name, "item_id": item_id}







# share_unshare_libraries.py by  @JonnyWong16
def library_sharing(share_toggle):
    from xml.dom import minidom
    
    PLEX_TOKEN = "ENTER_YOUR_PLEX_TOKEN_HERE"
    SERVER_ID = "ENTER_YOUR_SERVER_ID_HERE"  # Example: https://i.imgur.com/EjaMTUk.png
    
    # Get the User IDs and Library IDs from https://plex.tv/api/servers/SERVER_ID/shared_servers ( Example: https://i.imgur.com/yt26Uni.png )
    # Enter the User IDs and Library IDs in this format: {UserID1: [LibraryID1, LibraryID2], UserID2: [LibraryID1, LibraryID2]}
    
    USER_LIBRARIES = {1234567: [1234567, 1234567]}
    
    if share_toggle == None: print('You must provide "share" or "unshare" as an argument')
    elif share_toggle == True:
        headers = {"X-Plex-Token": PLEX_TOKEN, "Accept": "application/json"}
        url = "https://plex.tv/api/servers/" + SERVER_ID + "/shared_servers"
        for user_id, library_ids in USER_LIBRARIES.iteritems():
            payload = {"server_id": SERVER_ID, "shared_server": {"library_section_ids": library_ids, "invited_id": user_id} }
            r = requests.post(url, headers=headers, json=payload)
            if r.status_code == 401: print("Invalid Plex token")
            elif r.status_code == 400: print(r.content)
            elif r.status_code == 200: print("Shared libraries with user %s" % str(user_id))
    elif share_toggle == False:
        headers = {"X-Plex-Token": PLEX_TOKEN, "Accept": "application/json"}
        url = "https://plex.tv/api/servers/" + SERVER_ID + "/shared_servers"
        r = requests.get(url, headers=headers)
        if r.status_code == 401: print("Invalid Plex token")
        elif r.status_code == 400: print(r.content)
        elif r.status_code == 200:
            response_xml = minidom.parseString(r.content)
            MediaContainer = response_xml.getElementsByTagName("MediaContainer")[0]
            SharedServer = MediaContainer.getElementsByTagName("SharedServer")
            shared_servers = {int(s.getAttribute("userID")): int(s.getAttribute("id")) for s in SharedServer}
            for user_id, library_ids in USER_LIBRARIES.iteritems():
                server_id = shared_servers.get(user_id)
                if server_id:
                    url = "https://plex.tv/api/servers/" + SERVER_ID + "/shared_servers/" + str(server_id)
                    r = requests.delete(url, headers=headers)
                    if r.status_code == 200: print("Unshared libraries with user %s" % str(user_id))
                else: print("No libraries shared with user %s" % str(user_id))