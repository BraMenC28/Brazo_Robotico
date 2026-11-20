from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from stl import mesh
import numpy as np
import tkinter as tk
import sys
import os


# ============================================================
# 1. UBICAR LA CARPETA CON LOS STL
# ============================================================

# Nombre de la carpeta que contiene los archivos .STL
# (debe estar en la misma carpeta que este archivo .py)
CARPETA = "Bazo para Python"

# Ruta completa de la carpeta: carpeta de este script + nombre de la carpeta
RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), CARPETA)


def buscar_archivo(nombre):
    # Recorre todos los archivos de la carpeta
    for archivo in os.listdir(RUTA):
        # Si el archivo termina con el nombre de la pieza, ese es
        # (sirve aunque el archivo tenga un prefijo como "Ensamblaje - ")
        if archivo.lower().endswith(nombre.lower() + ".stl"):
            return os.path.join(RUTA, archivo)

    # Si llega aqui es porque no encontro la pieza
    print("No encontre la pieza:", nombre)
    print("Archivos que hay en la carpeta:", os.listdir(RUTA))
    sys.exit()


# ============================================================
# 2. IMPORTAR LAS PIEZAS STL
# ============================================================
# IMPORTANTE: aqui NO se centran las piezas una por una (como en
# codigo1.1). Todas vienen del mismo ensamblaje de SolidWorks, asi que
# ya traen su posicion correcta. Si se centran, el robot se desarma.

modelo1 = mesh.Mesh.from_file(buscar_archivo("Pieza 1-1"))     # base (fija)
modelo2 = mesh.Mesh.from_file(buscar_archivo("Pieza 2-1"))     # gira con J1
modelo3 = mesh.Mesh.from_file(buscar_archivo("Pieza 3-1"))     # gira con J2
modelo4 = mesh.Mesh.from_file(buscar_archivo("Pieza 4-1"))     # gira con J3
modelo5 = mesh.Mesh.from_file(buscar_archivo("Pieza 5-2"))     # gira con J4
modelo6 = mesh.Mesh.from_file(buscar_archivo("Pieza 6-2"))     # gira con J5
modelo7 = mesh.Mesh.from_file(buscar_archivo("Pieza 7-2"))     # gira con J6
modelo8 = mesh.Mesh.from_file(buscar_archivo("Pasador-3"))     # gira con J6
modelo9 = mesh.Mesh.from_file(buscar_archivo("Pasador-4"))     # gira con J6
modelo10 = mesh.Mesh.from_file(buscar_archivo("Pieza 8-4"))    # dedo 1 (J7)
modelo11 = mesh.Mesh.from_file(buscar_archivo("Pieza 8-3"))    # dedo 2 (J8)

modelos = [
    modelo1, modelo2, modelo3, modelo4, modelo5, modelo6,
    modelo7, modelo8, modelo9, modelo10, modelo11
]


# ============================================================
# 3. CALCULAR EL CENTRO Y LA ESCALA DEL ROBOT COMPLETO
# ============================================================
# Se busca la caja que encierra TODAS las piezas juntas.
# Con ella se centra y se escala el robot como un solo objeto.

# Se empieza con los valores de la primera pieza
minimo = modelo1.vectors.min(axis=(0, 1))
maximo = modelo1.vectors.max(axis=(0, 1))

# Se compara con todas las piezas y se guarda el menor y el mayor
for modelo in modelos:
    minimo_pieza = modelo.vectors.min(axis=(0, 1))
    maximo_pieza = modelo.vectors.max(axis=(0, 1))
    minimo = np.minimum(minimo, minimo_pieza)    # menor de cada eje (x, y, z)
    maximo = np.maximum(maximo, maximo_pieza)    # mayor de cada eje (x, y, z)

# Centro del robot (punto medio de la caja)
centro = (minimo + maximo) / 2

# Tamano de la dimension mas grande del robot (en mm)
tamano = np.max(maximo - minimo)

# Escala para que el robot mida aproximadamente 2 unidades en OpenGL
escala = 2.0 / tamano


# ============================================================
# 4. DATOS DE LAS ARTICULACIONES
# ============================================================
# Cada articulacion tiene:
#   - pivote: punto (x, y, z) alrededor del cual gira (medido en SolidWorks, en mm)
#   - eje: direccion (x, y, z) del giro
#   - minimo y maximo: limites del angulo en grados
# El numero de la articulacion es la posicion en la lista:
#   0 = J1, 1 = J2, 2 = J3, 3 = J4, 4 = J5, 5 = J6, 6 = J7, 7 = J8

nombres = [
    "J1 Giro de base",
    "J2 Hombro",
    "J3 Codo",
    "J4 Giro antebrazo",
    "J5 Muneca",
    "J6 Giro herramienta",
    "J7 Dedo 1",
    "J8 Dedo 2"
]

pivotes = [
    [716.3, 1031.0, 1483.5],
    [779.6, 1193.5, 1347.2],
    [734.3, 1508.9, 1476.5],
    [764.2, 1427.0, 1247.3],
    [799.2, 1361.9, 1139.0],
    [813.7, 1341.0, 1055.0],
    [782.8, 1314.9, 1024.3],
    [853.8, 1353.4, 1027.2]
]

ejes = [
    [0, 1, 0],
    [0.951, 0.001, 0.310],
    [0.951, -0.002, 0.310],
    [0.267, -0.514, -0.815],
    [0.926, 0.370, 0.074],
    [-0.166, 0.236, 0.957],
    [-0.446, 0.848, -0.286],
    [-0.446, 0.848, -0.286]
]

limites_min = [-180, -90, -120, -180, -90, -180, -35, -35]
limites_max = [180, 90, 120, 180, 90, 180, 35, 35]

# Angulo actual de cada articulacion (en grados). Empiezan en 0 (HOME)
angulos = [0, 0, 0, 0, 0, 0, 0, 0]


# ============================================================
# 5. VARIABLES DE LA CAMARA
# ============================================================

posicion = [0, 0, 0]     # desplazamiento de la escena en X, Y, Z (mm)
rotacion = [0, 0, 0]     # rotacion de la escena en X, Y, Z (grados)
zoom = 1.0               # 1.0 = normal, mayor = mas cerca


# ============================================================
# 6. FUNCIONES DE DIBUJO
# ============================================================

def crear_lista(modelo, color):
    # Una "display list" graba los triangulos de la pieza UNA sola vez.
    # Despues se puede dibujar de golpe con glCallList (mucho mas rapido
    # que recorrer todos los triangulos en cada cuadro).
    lista = glGenLists(1)
    glNewList(lista, GL_COMPILE)

    glColor3f(color[0], color[1], color[2])

    glBegin(GL_TRIANGLES)
    for i, cara in enumerate(modelo.vectors):
        glNormal3fv(modelo.normals[i])
        for vertice in cara:
            glVertex3fv(vertice)
    glEnd()

    glEndList()
    return lista


def girar_articulacion(j):
    # Gira alrededor del pivote de la articulacion j.
    # Para girar alrededor de un punto que NO es el origen se hace:
    #   1) mover el pivote al origen
    #   2) girar
    #   3) devolver el pivote a su lugar
    # OpenGL aplica las transformaciones en orden INVERSO a como se escriben,
    # por eso aqui aparecen al reves: primero +pivote, luego giro, luego -pivote.
    px = pivotes[j][0]
    py = pivotes[j][1]
    pz = pivotes[j][2]

    glTranslatef(px, py, pz)                                   # 3) devolver
    glRotatef(angulos[j], ejes[j][0], ejes[j][1], ejes[j][2])  # 2) girar
    glTranslatef(-px, -py, -pz)                                # 1) pivote al origen


def dibujar_robot():
    # La base nunca se mueve
    glCallList(lista1)

    # Guardamos la matriz para poder volver a ella al final
    glPushMatrix()

    # Cada giro se SUMA al anterior: si gira J1, todo lo que viene despues
    # (hombro, codo, muneca...) tambien gira con el.

    girar_articulacion(0)        # J1
    glCallList(lista2)

    girar_articulacion(1)        # J2 (ya incluye J1)
    glCallList(lista3)

    girar_articulacion(2)        # J3 (ya incluye J1 y J2)
    glCallList(lista4)

    girar_articulacion(3)        # J4
    glCallList(lista5)

    girar_articulacion(4)        # J5
    glCallList(lista6)

    girar_articulacion(5)        # J6
    glCallList(lista7)
    glCallList(lista8)           # los pasadores giran con J6
    glCallList(lista9)

    # Los dedos dependen de J6 pero NO uno del otro.
    # Por eso cada uno va entre su propio Push y Pop:
    # el Pop deshace el giro del dedo 1 antes de dibujar el dedo 2.

    glPushMatrix()
    girar_articulacion(6)        # J7
    glCallList(lista10)
    glPopMatrix()

    glPushMatrix()
    girar_articulacion(7)        # J8
    glCallList(lista11)
    glPopMatrix()

    glPopMatrix()


def display():
    glClearColor(0.13, 0.14, 0.17, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # Luz (direccional, no depende de la camara)
    glLightfv(GL_LIGHT0, GL_POSITION, (0.5, 1.0, 1.0, 0.0))

    # --- Camara y escena completa ---

    # Alejar la escena (mientras mas zoom, menos se aleja)
    glTranslatef(0, 0, -3.0 / zoom)

    # Desplazar toda la escena (mm pasados a unidades de OpenGL)
    glTranslatef(posicion[0] * escala, posicion[1] * escala, posicion[2] * escala)

    # Rotar toda la escena
    glRotatef(rotacion[0], 1, 0, 0)
    glRotatef(rotacion[1], 0, 1, 0)
    glRotatef(rotacion[2], 0, 0, 1)

    # El CAD trae el robot mirando hacia otro lado; este giro lo pone de frente
    glRotatef(-90, 0, 1, 0)

    # Pasar de milimetros a unidades de OpenGL
    glScalef(escala, escala, escala)

    # Mover el centro del robot al origen
    glTranslatef(-float(centro[0]), -float(centro[1]), -float(centro[2]))

    # Dibujar el robot con sus articulaciones
    dibujar_robot()

    glutSwapBuffers()


def reshape(w, h):
    # Se ejecuta cuando se cambia el tamano de la ventana
    if h == 0:
        h = 1
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(40, w / h, 0.1, 50)
    glMatrixMode(GL_MODELVIEW)


# ============================================================
# 7. INTERFAZ TKINTER (ventana de controles)
# ============================================================

ventana = tk.Tk()
ventana.title("Controles del brazo")


def crear_slider(marco, texto, minimo, maximo, paso):
    # Crea un slider, lo coloca en el marco y lo devuelve
    slider = tk.Scale(marco, label=texto, from_=minimo, to=maximo,
                      resolution=paso, orient="horizontal", length=250)
    slider.pack(fill="x")
    return slider


# --- Marco izquierdo: articulaciones ---

marco_art = tk.LabelFrame(ventana, text="Articulaciones (grados)")
marco_art.pack(side="left", fill="y", padx=4, pady=4)

slider_j1 = crear_slider(marco_art, nombres[0], limites_min[0], limites_max[0], 1)
slider_j2 = crear_slider(marco_art, nombres[1], limites_min[1], limites_max[1], 1)
slider_j3 = crear_slider(marco_art, nombres[2], limites_min[2], limites_max[2], 1)
slider_j4 = crear_slider(marco_art, nombres[3], limites_min[3], limites_max[3], 1)
slider_j5 = crear_slider(marco_art, nombres[4], limites_min[4], limites_max[4], 1)
slider_j6 = crear_slider(marco_art, nombres[5], limites_min[5], limites_max[5], 1)
slider_j7 = crear_slider(marco_art, nombres[6], limites_min[6], limites_max[6], 1)
slider_j8 = crear_slider(marco_art, nombres[7], limites_min[7], limites_max[7], 1)

sliders_art = [slider_j1, slider_j2, slider_j3, slider_j4,
               slider_j5, slider_j6, slider_j7, slider_j8]


def home_articulaciones():
    # Devuelve todos los sliders (y por tanto los angulos) a cero
    for slider in sliders_art:
        slider.set(0)


boton_home_art = tk.Button(marco_art, text="HOME articulaciones", command=home_articulaciones)
boton_home_art.pack(fill="x", pady=4)


# --- Marco derecho: camara ---

marco_cam = tk.LabelFrame(ventana, text="Camara")
marco_cam.pack(side="left", fill="y", padx=4, pady=4)

slider_pos_x = crear_slider(marco_cam, "Desplazar X (mm)", -600, 600, 5)
slider_pos_y = crear_slider(marco_cam, "Desplazar Y (mm)", -600, 600, 5)
slider_pos_z = crear_slider(marco_cam, "Desplazar Z (mm)", -600, 600, 5)

slider_rot_x = crear_slider(marco_cam, "Rotar X (grados)", -180, 180, 1)
slider_rot_y = crear_slider(marco_cam, "Rotar Y (grados)", -180, 180, 1)
slider_rot_z = crear_slider(marco_cam, "Rotar Z (grados)", -180, 180, 1)

slider_zoom = crear_slider(marco_cam, "Zoom", 0.4, 2.5, 0.05)
slider_zoom.set(1.0)


def vista_superior():
    slider_rot_x.set(90)
    slider_rot_y.set(0)
    slider_rot_z.set(0)


def vista_isometrica():
    slider_rot_x.set(25)
    slider_rot_y.set(-45)
    slider_rot_z.set(0)


def vista_lateral():
    slider_rot_x.set(0)
    slider_rot_y.set(0)
    slider_rot_z.set(0)


def home_camara():
    slider_pos_x.set(0)
    slider_pos_y.set(0)
    slider_pos_z.set(0)
    slider_rot_x.set(0)
    slider_rot_y.set(0)
    slider_rot_z.set(0)
    slider_zoom.set(1.0)


boton_superior = tk.Button(marco_cam, text="Vista superior", command=vista_superior)
boton_superior.pack(fill="x")

boton_isometrica = tk.Button(marco_cam, text="Vista isometrica", command=vista_isometrica)
boton_isometrica.pack(fill="x")

boton_lateral = tk.Button(marco_cam, text="Vista lateral", command=vista_lateral)
boton_lateral.pack(fill="x")

boton_home_cam = tk.Button(marco_cam, text="HOME CAMARA", command=home_camara)
boton_home_cam.pack(fill="x", pady=4)


def salir():
    ventana.destroy()
    sys.exit()


# Si se cierra la ventana de controles, se cierra todo el programa
ventana.protocol("WM_DELETE_WINDOW", salir)


# ============================================================
# 8. LEER LOS SLIDERS Y UNIR TKINTER CON GLUT
# ============================================================

def leer_controles():
    # Copia el valor actual de cada slider a las variables que usa OpenGL
    global zoom

    for j in range(8):
        angulos[j] = sliders_art[j].get()

    posicion[0] = slider_pos_x.get()
    posicion[1] = slider_pos_y.get()
    posicion[2] = slider_pos_z.get()

    rotacion[0] = slider_rot_x.get()
    rotacion[1] = slider_rot_y.get()
    rotacion[2] = slider_rot_z.get()

    zoom = slider_zoom.get()


def actualizar(valor):
    # GLUT y tkinter tienen cada uno su propio ciclo principal y no pueden
    # correr al mismo tiempo. Solucion: GLUT manda, y cada 16 ms (unas 60
    # veces por segundo) esta funcion le da un "turno" a tkinter.
    try:
        ventana.update()         # tkinter atiende los sliders y botones
    except tk.TclError:
        sys.exit()               # se cerro la ventana de controles

    leer_controles()             # pasar los valores de los sliders a las variables
    glutPostRedisplay()          # pedir a OpenGL que dibuje de nuevo
    glutTimerFunc(16, actualizar, 0)   # programar la siguiente vez


# ============================================================
# 9. INICIALIZAR GLUT Y OPENGL
# ============================================================

glutInit()
glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
glutInitWindowSize(800, 600)
glutInitWindowPosition(50, 50)
glutCreateWindow(b"Simulador de brazo robotico")

glEnable(GL_DEPTH_TEST)          # que lo que esta adelante tape lo de atras
glEnable(GL_LIGHTING)            # activar iluminacion
glEnable(GL_LIGHT0)              # activar la luz 0
glEnable(GL_NORMALIZE)           # mantener bien las normales al escalar
glEnable(GL_COLOR_MATERIAL)      # que glColor defina el color con iluminacion
glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)    # iluminar ambos lados de cada triangulo
glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.35, 0.35, 0.38, 1.0))
glShadeModel(GL_SMOOTH)

reshape(800, 600)


# ============================================================
# 10. CREAR LAS DISPLAY LISTS (cada pieza con su color)
# ============================================================
# Esto se hace DESPUES de crear la ventana, porque OpenGL necesita
# que exista la ventana para poder grabar las listas.

lista1 = crear_lista(modelo1, (0.8, 0.8, 0.8))
lista2 = crear_lista(modelo2, (1.0, 0.0, 0.0))
lista3 = crear_lista(modelo3, (0.0, 1.0, 0.0))
lista4 = crear_lista(modelo4, (0.0, 0.0, 1.0))
lista5 = crear_lista(modelo5, (1.0, 1.0, 0.0))
lista6 = crear_lista(modelo6, (1.0, 0.0, 1.0))
lista7 = crear_lista(modelo7, (0.0, 1.0, 1.0))
lista8 = crear_lista(modelo8, (1.0, 0.5, 0.0))
lista9 = crear_lista(modelo9, (0.6, 0.3, 0.9))
lista10 = crear_lista(modelo10, (0.3, 0.8, 0.4))
lista11 = crear_lista(modelo11, (0.9, 0.6, 0.6))


# ============================================================
# 11. REGISTRAR FUNCIONES E INICIAR
# ============================================================

glutDisplayFunc(display)
glutReshapeFunc(reshape)
glutTimerFunc(0, actualizar, 0)
glutMainLoop()