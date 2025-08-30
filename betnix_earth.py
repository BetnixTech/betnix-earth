# betnix_earth_ultimate.py
import math, os, json, requests
from io import BytesIO
from PIL import Image
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

DATA_FILE = "betnix_data.json"
TILE_SIZE = 256

# ------------------- DATA -------------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            d = json.load(f)
            return {
                "markers": d.get("markers", []),
                "routes": d.get("routes", []),
                "trees": d.get("trees", []),
                "grass": d.get("grass", []),
                "buildings": d.get("buildings", [])
            }
    return {"markers": [], "routes": [], "trees": [], "grass": [], "buildings": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ------------------- GEO -------------------
def latlon_to_xyz(lat, lon, radius=2.0):
    x = radius * math.cos(math.radians(lat)) * math.cos(math.radians(lon))
    y = radius * math.sin(math.radians(lat))
    z = radius * math.cos(math.radians(lat)) * math.sin(math.radians(lon))
    return x, y, z

def latlon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n)
    return xtile, ytile

# ------------------- ENTITIES -------------------
class Marker:
    def __init__(self, lat, lon, color=(1,0,0)):
        self.lat, self.lon = lat, lon
        self.color = color
    def draw(self, radius=2.02):
        glColor3f(*self.color)
        x, y, z = latlon_to_xyz(self.lat, self.lon, radius)
        glPushMatrix()
        glTranslatef(x, y, z)
        quad = gluNewQuadric()
        gluSphere(quad, 0.03, 10, 10)
        glPopMatrix()

class Route:
    def __init__(self, markers, color=(0,1,0)):
        self.markers = markers
        self.color = color
    def draw(self, radius=2.01):
        glColor3f(*self.color)
        glBegin(GL_LINE_STRIP)
        for m in self.markers:
            x, y, z = latlon_to_xyz(m.lat, m.lon, radius)
            glVertex3f(x, y, z)
        glEnd()

# ------------------- TREES, GRASS, BUILDINGS -------------------
def draw_realistic_tree(lat, lon, radius=2.0, lod=1):
    x, y, z = latlon_to_xyz(lat, lon, radius)
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(-90, 1, 0, 0)
    glColor3f(0,0.6,0)
    quad = gluNewQuadric()
    if lod==0:
        gluCylinder(quad, 0.0, 0.03, 0.1, 6, 6)
    else:
        gluCylinder(quad, 0.0, 0.05, 0.3, 12, 12)
        glTranslatef(0,0,0.3)
        gluCylinder(quad, 0.05, 0.0, 0.15, 12, 12) # top cone for leaves
    glPopMatrix()

def draw_grass(lat, lon, radius=2.0):
    x, y, z = latlon_to_xyz(lat, lon, radius)
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(0.2,0.8,0.2)
    glBegin(GL_QUADS)
    glVertex3f(-0.02,0,-0.02)
    glVertex3f(0.02,0,-0.02)
    glVertex3f(0.02,0,0.02)
    glVertex3f(-0.02,0,0.02)
    glEnd()
    glPopMatrix()

def draw_realistic_building(lat, lon, height=0.3, radius=2.0, lod=1):
    x, y, z = latlon_to_xyz(lat, lon, radius)
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(0.6,0.6,0.6)
    if lod==0: glutSolidCube(height*0.5)
    else:
        # multi-floor approximation
        for i in range(int(height/0.1)):
            glTranslatef(0,0,0.1)
            glutSolidCube(0.09)
    glPopMatrix()

# ------------------- TILE SYSTEM -------------------
tile_cache = {}
def fetch_tile(x, y, z):
    key = (x, y, z)
    if key in tile_cache: return tile_cache[key]
    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    r = requests.get(url)
    if r.status_code != 200: return None
    img = Image.open(BytesIO(r.content)).convert("RGB")
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGB,img.width,img.height,0,GL_RGB,GL_UNSIGNED_BYTE,img.tobytes())
    tile_cache[key] = tex_id
    return tex_id

def visible_tiles(zoom):
    n = 2 ** zoom
    tiles = []
    for x in range(n):
        for y in range(n):
            tiles.append((x, y, zoom))
    return tiles

def draw_globe_tiles(zoom, radius=2.0):
    glEnable(GL_TEXTURE_2D)
    for x, y, z in visible_tiles(zoom):
        tex_id = fetch_tile(x, y, z)
        if tex_id:
            lat0 = math.degrees(math.atan(math.sinh(math.pi*(1-2*y/2**zoom))))
            lat1 = math.degrees(math.atan(math.sinh(math.pi*(1-2*(y+1)/2**zoom))))
            lon0 = x/2**zoom*360 - 180
            lon1 = (x+1)/2**zoom*360 - 180
            glBindTexture(GL_TEXTURE_2D, tex_id)
            glBegin(GL_QUADS)
            for lat, lon in [(lat0, lon0), (lat0, lon1), (lat1, lon1), (lat1, lon0)]:
                vx, vy, vz = latlon_to_xyz(lat, lon, radius)
                glTexCoord2f(0 if lon==lon0 else 1, 0 if lat==lat0 else 1)
                glVertex3f(vx, vy, vz)
            glEnd()

# ------------------- OSM DYNAMIC -------------------
osm_cache = {}
def fetch_osm_data(min_lat, min_lon, max_lat, max_lon):
    key = (min_lat, min_lon, max_lat, max_lon)
    if key in osm_cache: return osm_cache[key]
    query = f"""
    [out:json];
    (
      node["natural"="tree"]({min_lat},{min_lon},{max_lat},{max_lon});
      way["building"]({min_lat},{min_lon},{max_lat},{max_lon});
    );
    out body;
    >;
    out skel qt;
    """
    r = requests.post("https://overpass-api.de/api/interpreter", data=query)
    if r.status_code != 200: return {"trees":[],"buildings":[]}
    data = r.json()
    trees, buildings, nodes = [], {}, {}
    for el in data.get("elements", []):
        if el["type"]=="node":
            nodes[el["id"]] = (el["lat"], el["lon"])
            if "tags" in el and el["tags"].get("natural")=="tree": trees.append((el["lat"], el["lon"]))
        elif el["type"]=="way" and "tags" in el and "building" in el["tags"]:
            poly = [nodes[nid] for nid in el.get("nodes", []) if nid in nodes]
            buildings[el["id"]] = poly
    osm_cache[key] = {"trees":trees,"buildings":buildings}
    return osm_cache[key]

# ------------------- GRID -------------------
def draw_grid(radius=2.03, step=30):
    glColor3f(0.5,0.5,0.5)
    for lat in range(-90, 91, step):
        glBegin(GL_LINE_STRIP)
        for lon in range(-180, 181, 2):
            x, y, z = latlon_to_xyz(lat, lon, radius)
            glVertex3f(x, y, z)
        glEnd()
    for lon in range(-180, 181, step):
        glBegin(GL_LINE_STRIP)
        for lat in range(-90, 91, 2):
            x, y, z = latlon_to_xyz(lat, lon, radius)
            glVertex3f(x, y, z)
        glEnd()

# ------------------- MAIN -------------------
def main():
    pygame.init()
    display = (1200, 800)
    screen = pygame.display.set_mode(display, DOUBLEBUF|OPENGL)
    pygame.display.set_caption("Betnix Earth Ultimate")
    gluPerspective(45, display[0]/display[1], 0.1, 100.0)
    glTranslatef(0, 0, -6)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_TEXTURE_2D)
    glutInit()

    data = load_data()
    markers = [Marker(**m) for m in data["markers"]]
    routes = [Route([Marker(**pt) for pt in r]) for r in data["routes"]]
    trees = [(t["lat"], t["lon"]) for t in data["trees"]]
    grass = [(g["lat"], g["lon"]) for g in data["grass"]]
    buildings = [(b["lat"], b["lon"], b.get("height",0.3)) for b in data["buildings"]]

    rot_x, rot_y, zoom = 0, 0, -6
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20)
    input_active, input_text, current_route = False, "", []

    running = True
    while running:
        for event in pygame.event.get():
            if event.type==pygame.QUIT: running=False
            elif event.type==pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
                dx, dy = event.rel
                rot_x += dy; rot_y += dx
            elif event.type==pygame.MOUSEBUTTONDOWN:
                if event.button==4: zoom += 0.3
                elif event.button==5: zoom -= 0.3
            elif event.type==pygame.KEYDOWN:
                if input_active:
                    if event.key==pygame.K_RETURN:
                        try:
                            lat, lon = map(float, input_text.split(","))
                            m=Marker(lat,lon); markers.append(m); current_route.append(m)
                        except: pass
                        input_text=""; input_active=False
                    elif event.key==pygame.K_BACKSPACE: input_text=input_text[:-1]
                    else: input_text+=event.unicode
                elif event.key==pygame.K_s:
                    save_data({
                        "markers":[{"lat":m.lat,"lon":m.lon} for m in markers],
                        "routes":[[{"lat":pt.lat,"lon":pt.lon} for pt in r.markers] for r in routes],
                        "trees":[{"lat":t[0],"lon":t[1]} for t in trees],
                        "grass":[{"lat":g[0],"lon":g[1]} for g in grass],
                        "buildings":[{"lat":b[0],"lon":b[1],"height":b[2]} for b in buildings]
                    })
                elif event.key==pygame.K_f: input_active=True
                elif event.key==pygame.K_r:
                    if len(current_route)>1: routes.append(Route(current_route.copy())); current_route=[]
                elif event.key==pygame.K_t:
                    if current_route: trees.append((current_route[-1].lat,current_route[-1].lon))
                elif event.key==pygame.K_g:
                    if current_route: grass.append((current_route[-1].lat,current_route[-1].lon))
                elif event.key==pygame.K_b:
                    if current_route: buildings.append((current_route[-1].lat,current_route[-1].lon,0.3))

        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0,0,zoom)
        glRotatef(rot_x,1,0,0)
        glRotatef(rot_y,0,1,0)

        lod = 0 if zoom<-5 else 1

        draw_globe_tiles(zoom=3)
        draw_grid()
        for m in markers: m.draw()
        for r in routes: r.draw()
        if len(current_route)>1: Route(current_route,(1,1,0)).draw()
        for lat,lon in trees: draw_tree(lat,lon,lod=lod)
        for lat,lon in grass: draw_grass(lat,lon)
        for lat,lon,h in buildings: draw_building(lat,lon,h,lod=lod)

        osm = fetch_osm_data(-85,-180,85,180)
        for lat,lon in osm["trees"]: draw_tree(lat,lon,lod=lod)
        for poly in osm["buildings"].values():
            for lat,lon in poly: draw_building(lat,lon,0.2,lod=lod)

        if input_active:
            txt_surf = font.render("Enter lat,lon: "+input_text,True,(255,255,255))
            screen.blit(txt_surf,(10,10))

        pygame.display.flip()
        clock.tick(60)

    save_data({
        "markers":[{"lat":m.lat,"lon":m.lon} for m in markers],
        "routes":[[{"lat":pt.lat,"lon":pt.lon} for pt in r.markers] for r in routes],
        "trees":[{"lat":t[0],"lon":t[1]} for t in trees],
        "grass":[{"lat":g[0],"lon":g[1]} for g in grass],
        "buildings":[{"lat":b[0],"lon":b[1],"height":b[2]} for b in buildings]
    })

# --- Frustum Culling Utility ---
def is_tile_visible(lat_min, lat_max, lon_min, lon_max, camera_matrix):
    """
    Returns True if any corner of the tile is inside the camera view.
    """
    for lat, lon in [(lat_min, lon_min),(lat_min, lon_max),(lat_max, lon_min),(lat_max, lon_max)]:
        x, y, z = latlon_to_xyz(lat, lon)
        # Transform to camera space
        vx = camera_matrix[0]*x + camera_matrix[4]*y + camera_matrix[8]*z + camera_matrix[12]
        vy = camera_matrix[1]*x + camera_matrix[5]*y + camera_matrix[9]*z + camera_matrix[13]
        vz = camera_matrix[2]*x + camera_matrix[6]*y + camera_matrix[10]*z + camera_matrix[14]
        if -10 < vz < 10:  # Simple near/far clipping
            return True
    return False

if __name__=="__main__":
    main()
