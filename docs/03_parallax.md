# Parallax y perspectiva

**Idea.** Al mover la vista, lo cercano cruza el campo visual rápido y lo lejano casi no se mueve. El fondo se divide en
capas y cada una se desplaza una fracción `k` del movimiento de la cámara:

```
desplazamiento de la capa = - x_cámara · k        (k = 0: fija, k = 1: se mueve con el mundo)
```

| Capa (nivel 1, `;fondo=aldea`) | k    | Contenido                     |
|--------------------------------|------|-------------------------------|
| cielo                          | 0,00 | degradado y sol rojo, fijo     |
| humo                           | 0,08 | nubes de humo                  |
| montañas lejos                 | 0,18 | cordillera clara con niebla    |
| montañas cerca                 | 0,34 | cordillera oscura              |
| aldea                          | 0,58 | casas, algunas en llamas       |
| árboles                        | 0,82 | árboles secos                  |
| suelo, enemigos y Ronin        | 1,00 | el mundo del juego             |

**Capas en bucle.** Una imagen de ancho `w` se dibuja en `x0 + n·w` con `x0 = (-x_cámara·k) mod w`, así el fondo no
se acaba aunque el nivel (7680 px en la zona de pruebas) sea más largo que la imagen. Las capas generadas son
periódicas: la cresta de las montañas se construye con senos de frecuencia entera, `f(x) = Σ aₖ sin(2π k x / W + φₖ)`,
y el borde derecho enlaza con el izquierdo.

**Uso.** `;fondo=aldea` en el archivo del nivel. `F4` activa o desactiva el parallax (útil para mostrar la diferencia
en la presentación). Las capas se regeneran con `python tools/generar_fondos.py [--preview]` (necesita Pillow);
`--preview` crea `docs/img/fondo_aldea.png`.

**Código.** `src/parallax.py` (funciones puras `layer_offset` y `tile_positions`, clases `Layer` y `Parallax`) y
`tests/test_parallax.py`.
