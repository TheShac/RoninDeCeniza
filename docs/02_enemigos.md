# Enemigos, peligros y jefes

Documento de diseño. Los valores numéricos son iniciales y se ajustarán al probar el juego.
Prioridad: **A** imprescindible, **B** muy deseable, **C** si sobra tiempo.

## Comportamiento común

Todos los enemigos están afectados por la gravedad y colisionan con el mapa igual que el jugador.
Su inteligencia es una máquina de estados sencilla:

```
PATRULLA --(jugador dentro del rango de visión)--> ALERTA / ATAQUE
ATAQUE   --(jugador fuera de rango o ataque terminado)--> PATRULLA
cualquier estado --(golpe recibido)--> AGOTADO (breve) o MUERTO
```

- **Detección:** distancia entre centros. Se compara el cuadrado de la distancia con el cuadrado del rango para evitar la raíz.
- **Patrulla:** avanzan en línea recta y dan la vuelta al llegar a un borde o a una pared.
- **Daño al jugador:** todos infligen 1 corazón y producen knockback. El knockback es un impulso en dirección `normalizar(jugador - enemigo)`.
- **Al recibir un golpe:** son empujados hacia atrás y quedan aturdidos un instante.

## Enemigos comunes

| Tipo | Vida | Movimiento (física) | Ataque | Nivel | Prioridad |
|---|---|---|---|---|---|
| Zombi caminante | 1 | Lento, velocidad constante (MRU) | Zarpazo al contacto | 1 y 2 | A |
| Zombi corredor | 1 | Acelera al ver al jugador (MRUA) y se desliza al frenar | Embestida | 1 y 2 | A |
| Zombi arquero | 2 | Casi estático en plataformas altas; retrocede si el jugador se acerca | Flechas rectas, desviables | 1 y 2 | A |
| Zombi hinchado | 3 | Muy lento y pesado | Explota al morir | 2 | B |

### Zombi caminante
- Patrulla a 60 px/s y persigue a 90 px/s si el jugador está a menos de 220 px y a una altura parecida (máx. 90 px de diferencia).
- Ataca con un zarpazo cuando queda a 30 px o menos, con 1 s de recarga entre golpes. El golpe hiere solo en una ventana del ataque (de 0,15 s a 0,30 s) y quita 1 corazón.
- Al patrullar da la vuelta si choca con una pared o si no hay suelo delante (no se cae por los pozos). Al perseguir se detiene en el borde.
- Tiene 1 de vida: un tajo o un shuriken lo matan. Al morir sale empujado, cae y su cuerpo desaparece a los 2 s.
- Cómo vencerlo: un tajo, un shuriken, o saltarlo. Es el enemigo básico para enseñar el combate.
- **Dos variantes de apariencia**, con el mismo comportamiento por ahora:
  - **Aldeano**: campesino japonés de la era samurái, con kimono índigo raído, obi, sandalias de paja y pelo enmarañado con una banda rota.
  - **Samurái**: guerrero caído con casco agrietado y un cuerno roto, pectoral de láminas con cordones desteñidos, hombreras, falda de placas y una katana rota en la mano.
- Animaciones (en `assets/images/zombi/caminante/<variante>_<animación>.png`): `walk` (6 cuadros), `attack` (4, dura 0,40 s), `hurt` (2) y `death` (5, dura 0,80 s).
- En el nivel de pruebas se colocan con las letras `Z` (aldeano) y `X` (samurái), o con las teclas `1` y `2`.

![Animaciones del zombi caminante](img/zombi_caminante.png)

### Zombi corredor
- Patrulla a 80 px/s. Si ve al Ronin a menos de 320 px y a una altura parecida, **embiste** hacia él: acelera a 900 px/s² hasta un tope de 260 px/s. Es un movimiento uniformemente acelerado (`v = v + a·dt`).
- La embestida termina al chocar con una pared, al llegar a 420 px de recorrido o al acercarse a un borde sin suelo (mira por delante la distancia de frenado `v² / 2a`, así no se cae por los pozos).
- Luego **frena por fricción** (1400 px/s²). Si golpeó al Ronin, vuelve a patrullar; si **falló**, queda **aturdido 0,8 s** sin moverse. Esa es la ventana para atacarlo. Tras cada embestida espera 1,2 s antes de repetirla.
- Si el Ronin lo toca durante la embestida le quita 1 corazón (una vez por embestida) y lo empuja.
- Tiene 1 de vida: un tajo o un shuriken lo matan, también cuando va a toda velocidad.
- Cómo vencerlo: **dash** para atravesar la embestida (el Ronin es invulnerable durante el dash, así que la embestida falla y el corredor queda aturdido), un tajo bien cronometrado, o un shuriken a distancia.
- **Dos variantes de apariencia**, con el mismo comportamiento:
  - **Campesino**: flaco, con el torso al aire (costillas y cicatrices), hakama rota y una banda en la frente.
  - **Ashigaru**: soldado raso de la era samurái, con *jingasa* (sombrero cónico de hierro abollado), coraza ligera de cuero con cordones rojos y falda de placas.
- Animaciones (en `assets/images/zombi/corredor/<variante>_<animación>.png`): `walk` (6 cuadros), `run` (6, el ciclo de carrera acelera con la velocidad real), `stun` (2) y `death` (5).
- En el nivel de pruebas se colocan con las letras `R` (campesino) y `A` (ashigaru), o con las teclas `3` y `4`.

![Animaciones del zombi corredor](img/zombi_corredor.png)

### Zombi arquero
- Se queda en su plataforma. Si el jugador se acerca a menos de 150 px, retrocede a 80 px/s.
- Si tiene al jugador en línea de visión a menos de 450 px, dispara una flecha cada 2 s a 420 px/s.
- Las flechas pueden desviarse con el desvío; la flecha reflejada hiere a cualquier enemigo que toque.
- Cómo vencerlo: desviar la flecha de vuelta, o subir a su plataforma y atacar.

### Zombi hinchado
- Camina a 40 px/s. Al morir explota: radio de 96 px, 1 de daño y un impulso radial.
- Impulso de la explosión: `J = k * normalizar(jugador - centro)` con `k = 600 px/s`, que disminuye con la distancia. También daña a otros zombis.
- Cómo vencerlo: shuriken desde lejos o un tajo seguido de alejarse rápidamente.

## Peligros del escenario

| Peligro | Comportamiento | Física | Nivel |
|---|---|---|---|
| Sierras giratorias | Giran en su sitio y dañan al contacto (colisión círculo contra caja) | Movimiento rotacional | 1 y 2 |
| Plataformas móviles | Se desplazan en línea recta o en círculo: `pos = centro + r (cos θ, sin θ)`, con `θ = ω t` | Movimiento circular uniforme | 2 |
| Suelo de hielo | `grip` bajo: cuesta arrancar y frenar | Fricción e inercia | 2 |

## Jefes

### Samurái Caído (nivel 1, vida 10)
El antiguo general del ronin, convertido en un muerto viviente.

- **Carga:** corre en línea recta hacia el jugador hasta 500 px/s y queda aturdido 1,5 s al terminar. Es la ventana para el tajo directo (1 de daño).
- **Onda de energía:** lanza un proyectil a 380 px/s cada 3 s. Solo el proyectil devuelto con el desvío le hace daño grande (3). Así el jefe enseña la mecánica central.
- **Fase 2 (menos de la mitad de vida):** carga más rápida y lanza dos ondas en abanico (±15°).

### Oni (nivel 2, vida 15)
Un demonio que custodia el templo y el faro.

- **Salto:** salta en parábola hacia donde está el jugador. La velocidad inicial se calcula con las ecuaciones del tiro parabólico para caer sobre el punto objetivo.
- **Onda de choque:** al caer, daña al jugador si está en el suelo a menos de 160 px (se evita saltando). Después queda aturdido 2 s.
- **Rocas:** lanza rocas en arco; un tajo las destruye.
- **Garrote:** telegrafía el ataque 0,5 s y luego barre un arco de 180° en 0,6 s (movimiento rotacional). Se esquiva con dash.

## Botín (propuesta)

Los enemigos pueden soltar corazones o shuriken (aprox. 20 %). Los jefes sueltan un checkpoint.

## Estado de implementación

| Elemento | Estado |
|---|---|
| Máquina de estados y detección | Hecho para el caminante y el corredor |
| Zombi caminante (aldeano y samurái) | Hecho |
| Zombi corredor (campesino y ashigaru) | Hecho |
| Zombi arquero y proyectiles | Pendiente |
| Zombi hinchado | Pendiente |
| Sierras y plataformas móviles | Pendiente |
| Samurái Caído (jefe) | Pendiente |
| Oni | Pendiente |
