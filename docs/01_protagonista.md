# El protagonista: el Ronin

Documento de diseño. Los valores numéricos son iniciales y se ajustarán en las pruebas de juego.
Las constantes marcadas con `settings.py` ya existen en el código.

## Resumen

Un samurái sin señor, ágil y de combate cercano. No usa armas de fuego: su fuerza está en el
tiempo de reacción (desvío), el posicionamiento (dash y saltos) y la puntería de sus lanzamientos.

| Atributo | Valor |
|---|---|
| Vida | 5 corazones |
| Munición de shuriken | 10 (se recogen más en los niveles) |
| Hitbox | 24 x 58 px (36 px de alto al agacharse) |
| Daño del tajo | 1 |

## Movimiento (implementado)

Todo el movimiento usa delta time (`dt`, en segundos), de modo que la velocidad no depende de los fps.

| Acción | Cómo funciona | Constante (`settings.py`) |
|---|---|---|
| Caminar y correr | La velocidad horizontal se acerca a la velocidad objetivo con aceleración | `RUN_SPEED` = 300 px/s, `GROUND_ACCEL` = 2600 px/s² |
| Frenado | Sin input, la fricción reduce la velocidad hasta cero | `GROUND_FRICTION` = 2200 px/s² |
| Control en el aire | Aceleración menor y frenado leve | `AIR_ACCEL`, `AIR_DRAG` |
| Gravedad | `v.y += g * dt`, con velocidad terminal | `GRAVITY` = 2200 px/s², `MAX_FALL_SPEED` |
| Salto | Velocidad inicial hacia arriba | `JUMP_SPEED` = 780 px/s |
| Salto variable | Soltar el botón en ascenso multiplica la velocidad vertical por 0,45 | `JUMP_CUT` |
| Coyote time | Se puede saltar hasta 0,10 s después de dejar un borde | `COYOTE_TIME` |
| Jump buffer | Un salto pedido hasta 0,12 s antes de aterrizar se ejecuta al tocar el suelo | `JUMP_BUFFER` |
| Hielo | `grip` del nivel multiplica aceleración y fricción del suelo (0,15 en hielo) | parámetro `;grip=` del nivel |

Cálculos de referencia:
- Altura máxima del salto: `h = v² / (2g) = 780² / (2 * 2200) ≈ 138 px` (unos 4,3 bloques).
- Tiempo hasta el punto más alto: `t = v / g ≈ 0,35 s`.
- Cada frame: `v += a * dt`, luego `pos += v * dt` (Euler semiimplícito), resolviendo las colisiones eje por eje.

## Habilidades

Estado: implementadas solo las de movimiento. El resto está en el plan de trabajo.

### Tajo (clic izquierdo)
- La katana barre un arco de 120° centrado en la dirección del mouse.
- Duración 0,2 s, es decir, una velocidad angular de 600°/s. Recarga de 0,35 s.
- Golpea a un enemigo si su centro está dentro del radio (80 px) y su ángulo respecto del jugador cae dentro del arco que ya recorrió la hoja.
- Física: movimiento rotacional y ángulos entre vectores (`atan2`).

### Desvío (clic derecho)
- Abre una ventana de 0,2 s en la que los proyectiles que tocan la hoja rebotan.
- La hoja apunta hacia el mouse con dirección unitaria `d`. La normal es `n = (-d.y, d.x)`, con el signo elegido para que `v · n < 0`.
- Velocidad reflejada: `v' = v - 2 (v · n) n`, aumentada un 25 %.
- Si el desvío no toca ningún proyectil, queda inutilizable 0,6 s.
- Los proyectiles devueltos dañan a los enemigos y son la única forma de herir seriamente al Samurái Caído.
- Física: álgebra de vectores (producto punto, normalización, reflexión).

### Shuriken (mantener E y soltar)
- Al mantener la tecla se dibuja la trayectoria punteada hacia el mouse; al soltar, se lanza.
- Velocidad de lanzamiento 700 px/s. Gira a 720°/s.
- Trayectoria: `x = x0 + vx t`, `y = y0 + vy t + ½ g t²`. La vista previa muestrea la misma fórmula.
- Daño 1. Consume 1 de munición.
- Física: tiro parabólico y descomposición de la velocidad en componentes.

### Dash (Shift)
- Impulso horizontal de 650 px/s durante 0,15 s, con invulnerabilidad en ese lapso.
- Recarga de 1 s. Al terminar el impulso, la inercia se disipa con la fricción del suelo (más larga en hielo).
- Física: momentum, inercia y fricción.

### Agacharse (S)
- Reduce la hitbox de 58 a 36 px de alto. Permite pasar bajo proyectiles altos y bajo obstáculos bajos.

### Daño y vida
- Cada golpe quita 1 corazón y empuja al jugador (knockback) en dirección opuesta al atacante.
- Tras recibir daño, 1 s de invulnerabilidad con parpadeo.
- Con 0 corazones, el nivel se reinicia desde el último checkpoint.

## Diseño visual y animaciones

**Concepto.** Silueta de samurái errante en estilo tinta sobre papel: kimono negro, sombrero cónico (kasa),
katana al cinto y una **bufanda roja** que es el único acento de color del personaje y ondea según el movimiento.
La paleta (negro tinta, rojo, tonos de gris) es la misma del resto del juego.

![Animaciones del Ronin](img/ronin_animaciones.png)

| Animación | Cuadros | Velocidad | Cuándo se usa |
|---|---|---|---|
| `idle` | 4 | 5 cuadros/s | Quieto en el suelo (respira y la bufanda se mueve) |
| `run` | 6 | 12 cuadros/s, escalada por la velocidad real | Se mueve en el suelo |
| `jump` | 1 | | En el aire subiendo (`vel.y < 0`) |
| `fall` | 1 | | En el aire bajando |
| Agacharse, tajo, desvío, dash, daño y muerte | | | Pendientes: se dibujan cuando se implemente cada habilidad |

**Cómo se hicieron.** El script `tools/generar_sprites_ronin.py` dibuja al personaje como un esqueleto de
segmentos. Cada extremidad se define con ángulos y la posición de cada articulación se calcula como
`punto_siguiente = punto + longitud * (sen(ángulo), cos(ángulo))` (cinemática directa). Cada cuadro de la
animación es una pose (un conjunto de ángulos), y el ciclo de carrera es una función seno de la fase.
Esto se puede explicar en el informe como aplicación de **trigonometría y movimiento rotacional**.

**Cómo se usan en el juego.**
- Cada animación es una tira horizontal de cuadros de 64 x 64 px en `assets/images/ronin/`.
- `Animator` (en `src/animation.py`) elige el cuadro con `índice = int(tiempo * fps)`; así la animación depende
  del tiempo y no de los fps de la pantalla.
- `Player.state` decide la animación según la física: en el suelo con velocidad alta es `run`, en el aire
  subiendo es `jump` y bajando es `fall`.
- Los sprites miran a la derecha y se voltean al mirar a la izquierda.
- Los pies del dibujo se alinean con el borde inferior de la hitbox. En el modo debug (F1) se ve la hitbox sobre el sprite.

**Cambiar el arte.** Para usar dibujos propios basta reemplazar los PNG por tiras con el mismo nombre y cuadros
de 64 x 64 px. Para regenerar los actuales: `pip install -r requirements-dev.txt` y
`python tools/generar_sprites_ronin.py --preview`. Pillow solo hace falta para regenerarlos, no para jugar.

## Controles

| Entrada | Acción |
|---|---|
| A / D o flechas | Mover |
| W, Espacio o flecha arriba | Saltar |
| S | Agacharse |
| Mouse | Apuntar tajo, desvío y shuriken |
| Clic izquierdo | Tajo |
| Clic derecho | Desvío |
| E (mantener y soltar) | Shuriken |
| Shift | Dash |
| Esc / P | Pausa |
| R | Reiniciar nivel |
| F1 | Modo debug |

## Estados del protagonista

Para el diagrama de estados del informe:

```
Quieto <-> Corriendo
   |           |
   +--> Saltando --> Cayendo --> (aterriza) Quieto / Corriendo
   +--> Agachado
   +--> Atacando (tajo)       --> vuelve al estado anterior
   +--> Desviando (parry)     --> vuelve al estado anterior (con recarga si falló)
   +--> Dash                  --> Corriendo / Cayendo
   +--> Herido (knockback)    --> Quieto / Cayendo
   +--> Muerto                --> reinicio desde checkpoint
```

## Estado de implementación

| Elemento | Estado |
|---|---|
| Caminar, frenar, gravedad, salto variable, coyote time, jump buffer | Hecho |
| Colisiones con el mapa y caída al vacío | Hecho |
| Diseño visual y animaciones idle, run, jump y fall | Hecho |
| Animaciones de agacharse, tajo, desvío, dash, daño y muerte | Pendiente |
| Agacharse | Pendiente |
| Tajo | Pendiente |
| Desvío | Pendiente |
| Shuriken | Pendiente |
| Dash | Pendiente |
| Vida, knockback e invulnerabilidad | Pendiente |
