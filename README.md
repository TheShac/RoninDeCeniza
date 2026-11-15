# Ronin de Ceniza

Videojuego de plataformas 2D con combate cuerpo a cuerpo, desarrollado en Python con pygame-ce.
Proyecto Semestral 2026 de la asignatura **E.F.P. Fundamentos Teóricos de Videojuegos**,
Ingeniería en Computación e Informática, Universidad de Tarapacá (Arica, Chile).

> Estado: en desarrollo. Entrega y presentación: 02/12/2026.

---

## Acerca del proyecto

*Ronin de Ceniza* es un plataformas de desplazamiento lateral con oleadas de enemigos y jefes finales.
El jugador controla a un ronin que atraviesa una región devastada por una plaga de muertos vivientes. No hay armas de fuego: se combate con la katana, con shuriken y con el **desvío**, una técnica que devuelve los proyectiles enemigos usando álgebra de vectores.

El juego nació de la idea de un run and gun clásico, pero se rediseñó para ser un concepto original:
cambia la mecánica central (combate de precisión y reflejos en lugar de disparos continuos), los enemigos, el objetivo de cada nivel y el estilo visual (tinta sobre papel).

**Enfoque educativo.** La física del juego es visible. El modo debug (`F1`) muestra hitboxes, vectores de velocidad y la trayectoria parabólica del shuriken, y el tutorial explica en pantalla qué ley física se está aplicando en cada acción.

## Historia

Hace una generación, el monasterio de Hai-no-Yama encendió en lo alto de la montaña un faro sagrado, cuya luz mantenía en reposo a los muertos del valle. Una noche el faro se apagó. Desde entonces los caídos caminan, y las aldeas arden una tras otra.

El ronin, un samurái sin señor que lleva años vagando por los caminos, regresa al valle y encuentra su antigua aldea en llamas. Entre los muertos reconoce al general bajo cuyo mando sirvió, ahora convertido en una sombra que no descansa. Para detener la plaga, el ronin debe abrirse paso por la aldea hasta el templo de la montaña y volver a encender el faro, enfrentando en el camino a los dos guardianes corrompidos que custodian el valle: el **Samurái Caído** y el **Oni**.

## Características

- Combate con katana: tajo en arco dirigido con el mouse
- Desvío de proyectiles: refleja flechas y ondas de energía contra los enemigos
- Shuriken con trayectoria parabólica y vista previa de la puntería
- Dash con impulso e invulnerabilidad breve
- Cuatro tipos de enemigos con comportamientos distintos, más dos jefes
- Dos niveles con mecánicas de terreno propias (suelo helado, plataformas en movimiento, sierras)
- Niveles definidos en archivos de texto: agregar uno nuevo no requiere modificar el código
- Protagonista con 12 animaciones (movimiento, agacharse, dash, tajo, desvío, lanzamiento, daño y muerte) generadas con un esqueleto de ángulos
- Modo debug para visualizar la física en tiempo real

## Niveles

| Nivel                    | Ambientación        | Elementos                                                          | Jefe            |
| ------------------------ | -------------------- | ------------------------------------------------------------------ | --------------- |
| 1. Aldea en llamas       | Noche, humo y niebla | Zombis caminantes, corredores y arqueros                           | Samurái Caído |
| 2. Templo de la montaña | Nieve y hielo        | Suelo helado, plataformas en movimiento, sierras, zombis hinchados | Oni             |

## Controles

| Entrada                            | Acción                                                                           |
| ---------------------------------- | --------------------------------------------------------------------------------- |
| `A` / `D` o flechas            | Mover                                                                             |
| `W`, `Espacio` o flecha arriba | Saltar (mantener para más altura)                                                |
| `S` (mantener)                   | Agacharse; si además se mueve, avanza agachado (más lento)                      |
| Clic izquierdo o `J`             | Tajo hacia donde mira el Ronin (hiere en un arco de 120°; el mouse no lo cambia) |
| Clic derecho o `K`               | Desvío. Clic derecho: la flecha sale hacia el cursor. `K`: hacia la dirección de WASD que mantengas (por defecto, hacia donde mira) |
| `E`                              | Lanzar shuriken                                                                   |
| `Shift`                          | Dash. Con `W` + `A`/`D` mantenidas sale en diagonal hacia arriba (llega más lejos) |
| `Esc`                            | Salir (la pausa vendrá con los menús)                                           |
| `R`                              | Reiniciar nivel                                                                   |
| `F1`                             | Modo debug (con él: `F2` golpe de prueba, `F3` muerte)                       |
| `F11`                            | Pantalla completa (alterna)                                                      |
| `1` a `7`                        | Solo en el nivel de pruebas: genera delante del Ronin un zombi (1-2 caminantes, 3-4 corredores, 5-6 arqueros, 7 hinchado) |

Notas sobre los controles:
- El Ronin siempre mira hacia donde se mueve (`A`/`D`). El mouse no lo gira: el tajo y el shuriken salen hacia donde mira. Solo el desvío tiene dirección propia.
- `J`, `E` y `K` se pueden usar caminando, saltando, cayendo o agachado. Mientras dura la acción se avanza al 50 % de la velocidad (`ACTION_SPEED_MULT` en `settings.py`).
- Con `F1` se muestran las teclas mantenidas y las acciones recibidas. Sirve para detectar si el teclado "pierde" alguna combinación de teclas pulsadas a la vez (*ghosting*, depende del hardware).
- Las teclas se pueden cambiar en el diccionario `KEYMAP` de `src/game.py`.

## Conceptos de física y matemáticas aplicados

| Concepto              | Aplicación en el juego                                                                                                | Estado                    |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| Leyes de movimiento   | Gravedad, salto, aceleración, fricción e inercia (`player.py`, `physics.py`); embestida del corredor con aceleración constante (`enemy.py`)                                     | Implementado              |
| Colisiones            | Cajas AABB resueltas por eje con subpasos (`physics.py`)                                                             | Implementado              |
| Álgebra de vectores  | `Vector2` para posición y velocidad; producto punto en el arco del tajo, knockback; reflexión de las flechas en el desvío (`v' = v − 2(v·n)n`) | Implementado              |
| Movimiento rotacional | Arco del tajo, shuriken giratorio, sierras                                                                             | En curso (shuriken hecho) |
| Tiro parabólico      | Shuriken y rocas del Oni                                                                                               | En curso (shuriken hecho) |
| Perspectiva           | Parallax de fondo en varias capas                                                                                      | Pendiente                 |

## Tecnologías

- Python 3.11 o superior
- [pygame-ce](https://pyga.me/) (versión comunitaria de pygame)
- Visual Studio Code
- Pillow (opcional, solo para regenerar los sprites con `tools/`)
- Niveles en texto plano (`levels/*.txt`)

## Instalación y ejecución

Requisitos: Python 3.11 o superior y Git. Instrucciones para Windows (PowerShell):

```powershell
git clone <URL-del-repositorio>
cd RoninDeCeniza
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

Si PowerShell bloquea la activación del entorno virtual, ejecutar una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. En VS Code, seleccionar el intérprete de `.venv`
con `Ctrl+Shift+P` > "Python: Select Interpreter".

La carpeta `.venv` no se versiona: cada equipo crea la suya a partir de `requirements.txt`.

### Tamaño de la ventana

Por defecto la ventana ocupa tu pantalla (descontando las barras de título y de tareas). Se cambia en `config.json`:

```json
{
  "ancho": "auto",
  "alto": "auto",
  "pantalla_completa": false
}
```

- `ancho` y `alto`: píxeles (por ejemplo `1280` y `720`) o `"auto"`. Se pueden fijar por separado. El mínimo es 480x270.
- `pantalla_completa`: `true` para abrir a pantalla completa. `F11` lo alterna dentro del juego.
- La ventana también se puede redimensionar con el mouse.
- El juego se dibuja siempre en un lienzo de 960x544 y se escala a la ventana **sin deformarse** (si la proporción no
  coincide quedan barras negras). Así la jugabilidad es idéntica en cualquier tamaño.
- Si `config.json` falta o está mal escrito, se usan los valores por defecto.

### Galería de animaciones

`python tools/ver_animaciones.py` (Ronin) o `python tools/ver_animaciones.py zombi` (una fila por variante) muestran
todas las animaciones en bucle. La ventana nunca supera el tamaño de tu pantalla: si no caben, se desplaza con la rueda
del mouse, las flechas arriba/abajo, `RePág`/`AvPág` o `Inicio`/`Fin`.

### Pruebas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas usan su propio nivel fijo (`tests/niveles/pruebas.txt`), así que se puede editar `levels/nivel1.txt` sin romperlas.
Las pruebas verifican gravedad, altura del salto, frenado, hielo, colisiones a alta velocidad y
tiempo de gracia del salto (coyote time).

## Estructura del repositorio

```
RoninDeCeniza/
  src/          código fuente (main, game, config, controls, player, enemy, hazard, combat, projectile, animation, level, camera, physics, settings)
  tests/        pruebas de la física, las animaciones, el combate y los enemigos
  tools/        generadores de sprites (Ronin y zombis) y galería de animaciones
  levels/       mapas de los niveles (.txt)
  assets/
    images/     sprites: ronin/ y zombi/<tipo>/ (caminante, corredor, arquero, hinchado), una hoja por animación
    sounds/     efectos y música
  docs/         documentación de diseño (protagonista y enemigos)
  requirements.txt
```

## Documentación

| Documento                                         | Contenido                                              |
| ------------------------------------------------- | ------------------------------------------------------ |
| [docs/01_protagonista.md](docs/01_protagonista.md) | El Ronin: atributos, movimiento, habilidades y estados |
| [docs/02_enemigos.md](docs/02_enemigos.md)         | Enemigos, peligros del escenario y jefes               |

## Estado del desarrollo

- [X] Estructura del proyecto, bucle principal con delta time y modo debug
- [X] Jugador: movimiento, gravedad, salto variable y colisiones
- [X] Carga de niveles desde archivos de texto y cámara con seguimiento
- [X] Diseño del Ronin y sus 12 animaciones
- [X] Agacharse, avanzar agachado y dash
- [X] Shuriken (trayectoria parabólica y rotación)
- [X] Tajo con arco de daño, zombi caminante (aldeano y samurái), vida en corazones y knockback
- [X] Zombi corredor (campesino y ashigaru) con embestida acelerada y aturdimiento
- [X] Flechas, zombi arquero (cazador y kyudoka), desvío con reflexión de vectores y shuriken
- [X] Zombi hinchado (luchador de sumo): se infla y explota con impulso radial y reacción en cadena
- [X] Sierras giratorias (fijas y con riel): movimiento rotacional y colisión círculo contra caja
- [ ] Nivel 1 completo con parallax y primer jefe
- [ ] Dash, menús y estados del juego, sonido
- [ ] Nivel 2 y segundo jefe
- [ ] Pruebas finales, manual de usuario y presentación

## Créditos y licencias

- Autor: _Leonardo Rodriguez_
- Asignatura: E.F.P. Fundamentos Teóricos de Videojuegos. Profesor: Raúl Herrera A.
- Los recursos gráficos y sonoros de terceros, si se usan, se listarán aquí con su licencia.
