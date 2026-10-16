# -*- coding: utf-8 -*-
"""Genera los mosaicos provisionales del paquete UWP.

Son un MARCADOR DE POSICION, no arte: un fondo verde con las siglas del juego.
La identidad visual de verdad la elige el usuario y entra por
`dependencias-usuario\\Display Images\\` con `herramientas\\identidad-visual.py`
del proyecto padre (ver su tecnico, 5.4). Mientras esa carpeta este vacia, el
paquete necesita SI O SI unos PNG del tamano correcto o el empaquetado falla.

Tamanos: los que pide el manifiesto, mas las variantes de escala que la consola
usa para el mosaico grande.
"""
import os
import sys

from PIL import Image, ImageDraw

DESTINO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "fuentes", "uwp", "Assets")

# Verde del cesped del juego, que al menos lo hace reconocible de un vistazo
FONDO = (74, 145, 61)
TEXTO = (245, 240, 205)

PIEZAS = [
    ("StoreLogo.png", 50, 50),
    ("Square44x44Logo.png", 44, 44),
    ("Square44x44Logo.scale-200.png", 88, 88),
    ("Square44x44Logo.targetsize-24_altform-unplated.png", 24, 24),
    ("Square150x150Logo.png", 150, 150),
    ("Square150x150Logo.scale-200.png", 300, 300),
    ("SplashScreen.png", 620, 300),
    ("SplashScreen.scale-200.png", 1240, 600),
]


def pieza(ruta, ancho, alto):
    img = Image.new("RGBA", (ancho, alto), FONDO + (255,))
    d = ImageDraw.Draw(img)
    # «AC» centrado, escalado al tamano de la pieza
    lado = min(ancho, alto)
    if lado >= 40:
        texto = "AC"
        # fuente por defecto de PIL, ampliada dibujando en pequeno y escalando
        tmp = Image.new("RGBA", (24, 12), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((2, 0), texto, fill=TEXTO + (255,))
        escala = max(1, int(lado * 0.5) // 12)
        tmp = tmp.resize((24 * escala, 12 * escala), Image.NEAREST)
        img.alpha_composite(tmp, ((ancho - tmp.width) // 2, (alto - tmp.height) // 2))
    else:
        d.rectangle([lado * 0.25, lado * 0.25, lado * 0.75, lado * 0.75], fill=TEXTO + (255,))
    img.save(ruta)


def main():
    os.makedirs(DESTINO, exist_ok=True)
    for nombre, w, h in PIEZAS:
        pieza(os.path.join(DESTINO, nombre), w, h)
        print("  %-52s %dx%d" % (nombre, w, h))
    print("%d mosaicos provisionales en %s" % (len(PIEZAS), DESTINO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
