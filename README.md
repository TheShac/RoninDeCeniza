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
- Protagonista animado (reposo, carrera, salto y caída) generado con un esqueleto de ángulos
- Modo debug para visualizar la física en tiempo real

## Niveles

| Nivel                    | Ambientación        | Elementos                                                          | Jefe            |
| ------------------------ | -------------------- | ------------------------------------------------------------------ | --------------- |
| 1. Aldea en llamas       | Noche, humo y niebla | Zombis caminantes, corredores y arqueros                           | Samurái Caído |
| 2. Templo de la montaña | Nieve y hielo        | Suelo helado, plataformas en movimiento, sierras, zombis hinchados | Oni             |

## Controles

| Entrada                            | Acción                            |
| ---------------------------------- | ---------------------------------- |
| `A` / `D` o flechas            | Mover                              |
| `W`, `Espacio` o flecha arriba | Saltar (mantener para más altura) |
| `S`                              | Agacharse                          |
| Mouse                              | Apuntar                            |
| Clic izquierdo                     | Tajo                               |
| Clic derecho                       | Desvío                            |
| `E` (mantener y soltar)          | Lanzar shuriken                    |
| `Shift`                          | Dash                               |
| `Esc` / `P`                    | Pausa                              |
| `R`                              | Reiniciar nivel                    |
| `F1`                             | Modo debug                         |

## Conceptos de física y matemáticas aplicados

| Concepto              | Aplicación en el juego                                                                   | Estado       |
| --------------------- | ----------------------------------------------------------------------------------------- | ------------ |
| Leyes de movimiento   | Gravedad, salto, aceleración, fricción e inercia (`player.py`, `physics.py`)        | Implementado |
| Colisiones            | Cajas AABB resueltas por eje con subpasos (`physics.py`)                                | Implementado |
| Álgebra de vectores  | `Vector2` para posición y velocidad; normalización, reflexión del desvío, knockback | En curso     |
| Movimiento rotacional | Arco del tajo, shuriken giratorio, sierras                                                | Pendiente    |
| Tiro parabólico      | Shuriken y rocas del Oni                                                                  | Pendiente    |
| Perspectiva           | Parallax de fondo en varias capas                                                         | Pendiente    |

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

### Pruebas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas verifican gravedad, altura del salto, frenado, hielo, colisiones a alta velocidad y
tiempo de gracia del salto (coyote time).

## Estructura del repositorio

```
RoninDeCeniza/
  src/          código fuente (main, game, player, animation, level, camera, physics, settings)
  tests/        pruebas de la física y de las animaciones
  tools/        herramientas (generador de sprites del Ronin)
  levels/       mapas de los niveles (.txt)
  assets/
    images/     sprites y fondos
    sounds/     efectos y música
  docs/         documentación de diseño (protagonista y enemigos)
  requirements.txt
```

## Documentación

| Documento                                                                   | Contenido                                              |
| --------------------------------------------------------------------------- | ------------------------------------------------------ |
| [docs/01_protagonista.md](docs/01_protagonista.md)                           | El Ronin: atributos, movimiento, habilidades y estados |
| [docs/02_enemigos.md](docs/02_enemigos.md)                                   | Enemigos, peligros del escenario y jefes               |

## Estado del desarrollo

- [X] Estructura del proyecto, bucle principal con delta time y modo debug
- [X] Jugador: movimiento, gravedad, salto variable y colisiones
- [X] Carga de niveles desde archivos de texto y cámara con seguimiento
- [X] Diseño del Ronin y animaciones de reposo, carrera, salto y caída
- [ ] Tajo, zombi caminante, vida y knockback
- [ ] Proyectiles, arquero, desvío y shuriken
- [ ] Nivel 1 completo con parallax y primer jefe
- [ ] Dash, menús y estados del juego, sonido
- [ ] Nivel 2 y segundo jefe
- [ ] Pruebas finales, manual de usuario y presentación

## Créditos y licencias

- Autor: _completar nombre_
- Asignatura: E.F.P. Fundamentos Teóricos de Videojuegos. Profesor: Raúl Herrera A.
- Los recursos gráficos y sonoros de terceros, si se usan, se listarán aquí con su licencia.
