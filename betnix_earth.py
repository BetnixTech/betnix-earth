# Betnix Earth – Full Single File Python
# Requires: Python 3, PyOpenGL, Pygame, Pillow
# Betnix Earth Satilite Imagery

import os, json, math
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from PIL import Image

DATA_FILE = "betnix_data.json"

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

# ------------------- ENTITIES -------------------
class Marker:
    def __init__(self, lat, lon, color=(1, 0, 0)):
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
    def __init__(self, markers, color=(0, 1, 0)):
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
def draw_tree(lat, lon, height=0.2, radius=2.0):
    x, y, z = latlon_to_xyz(lat, lon, radius)
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(0, 0.5, 0)
    quad = gluNewQuadric()
    glRotatef(-90, 1, 0, 0)
    gluCylinder(quad, 0.0, 0.05, height, 8, 8)
    glPopMatrix()

def draw_grass(lat, lon, radius=2.0):
    x, y, z = latlon_to_xyz(lat, lon, radius)
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(0.2, 0.8, 0.2)
    glBegin(GL_QUADS)
    glVertex3f(-0.02, 0, -0.02)
    glVertex3f(0.02, 0, -0.02)
    glVertex3f(0.02, 0, 0.02)
    glVertex3f(-0.02, 0, 0.02)
    glEnd()
    glPopMatrix()

def draw_building(lat, lon, height=0.3, radius=2.0):
    x, y, z = latlon_to_xyz(lat, lon, radius)
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(0.6, 0.6, 0.6)
    glutSolidCube(height)
    glPopMatrix()

# ------------------- EARTH & GRID -------------------
def draw_earth_surface(radius=2.0, slices=40, stacks=40):
    for i in range(stacks):
        lat0 = -90 + 180 * i / stacks
        lat1 = -90 + 180 * (i + 1) / stacks
        glBegin(GL_QUAD_STRIP)
        for j in range(slices + 1):
            lon = -180 + 360 * j / slices
            glColor3f(0.2, 0.7, 0.2) if -60 <= lat0 <= 75 else glColor3f(0.1, 0.3, 0.8)
            x, y, z = latlon_to_xyz(lat0, lon, radius)
            glVertex3f(x, y, z)
            glColor3f(0.2, 0.7, 0.2) if -60 <= lat1 <= 75 else glColor3f(0.1, 0.3, 0.8)
            x, y, z = latlon_to_xyz(lat1, lon, radius)
            glVertex3f(x, y, z)
        glEnd()

def draw_grid(radius=2.03, step=30):
    glColor3f(0.5, 0.5, 0.5)
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
    screen = pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Betnix Earth")
    gluPerspective(45, display[0] / display[1], 0.1, 100.0)
    glTranslatef(0, 0, -6)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_COLOR_MATERIAL)
    glutInit()

    data = load_data()
    markers = [Marker(**m) for m in data["markers"]]
    routes = [Route([Marker(**pt) for pt in r]) for r in data["routes"]]
    trees = [(t["lat"], t["lon"]) for t in data["trees"]]
    grass = [(g["lat"], g["lon"]) for g in data["grass"]]
    buildings = [(b["lat"], b["lon"], b.get("height", 0.3)) for b in data["buildings"]]

    rot_x, rot_y, zoom = 0, 0, -6
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20)
    input_active, input_text, current_route = False, "", []

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
                dx, dy = event.rel
                rot_x += dy; rot_y += dx
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4: zoom += 0.3
                elif event.button == 5: zoom -= 0.3
            elif event.type == pygame.KEYDOWN:
                if input_active:
                    if event.key == pygame.K_RETURN:
                        try:
                            lat, lon = map(float, input_text.split(","))
                            m = Marker(lat, lon); markers.append(m); current_route.append(m)
                        except: pass
                        input_text = ""; input_active = False
                    elif event.key == pygame.K_BACKSPACE: input_text = input_text[:-1]
                    else: input_text += event.unicode
                elif event.key == pygame.K_s:
                    save_data({
                        "markers": [{"lat": m.lat, "lon": m.lon} for m in markers],
                        "routes": [[{"lat": pt.lat, "lon": pt.lon} for pt in r.markers] for r in routes],
                        "trees": [{"lat": t[0], "lon": t[1]} for t in trees],
                        "grass": [{"lat": g[0], "lon": g[1]} for g in grass],
                        "buildings": [{"lat": b[0], "lon": b[1], "height": b[2]} for b in buildings]
                    })
                elif event.key == pygame.K_f: input_active = True
                elif event.key == pygame.K_r:
                    if len(current_route) > 1: routes.append(Route(current_route.copy())); current_route = []
                elif event.key == pygame.K_t:
                    if current_route: trees.append((current_route[-1].lat, current_route[-1].lon))
                elif event.key == pygame.K_g:
                    if current_route: grass.append((current_route[-1].lat, current_route[-1].lon))
                elif event.key == pygame.K_b:
                    if current_route: buildings.append((current_route[-1].lat, current_route[-1].lon, 0.3))

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0, 0, zoom)
        glRotatef(rot_x, 1, 0, 0)
        glRotatef(rot_y, 0, 1, 0)

        draw_earth_surface()
        draw_grid()
        for m in markers: m.draw()
        for r in routes: r.draw()
        if len(current_route) > 1: Route(current_route, (1, 1, 0)).draw()
        for lat, lon in trees: draw_tree(lat, lon)
        for lat, lon in grass: draw_grass(lat, lon)
        for lat, lon, h in buildings: draw_building(lat, lon, h)

        if input_active:
            txt_surf = font.render("Enter lat,lon: " + input_text, True, (255, 255, 255))
            screen.blit(txt_surf, (10, 10))

        pygame.display.flip()
        clock.tick(60)

    save_data({
        "markers": [{"lat": m.lat, "lon": m.lon} for m in markers],
        "routes": [[{"lat": pt.lat, "lon": pt.lon} for pt in r.markers] for r in routes],
        "trees": [{"lat": t[0], "lon": t[1]} for t in trees],
        "grass": [{"lat": g[0], "lon": g[1]} for g in grass],
        "buildings": [{"lat": b[0], "lon": b[1], "height": b[2]} for b in buildings]
    })

if __name__ == "__main__": main()
