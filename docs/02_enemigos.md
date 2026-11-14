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
- Patrulla a 60 px/s y persigue a 90 px/s si el jugador está a menos de 220 px.
- Ataca al contacto con 1 s de recarga entre golpes.
- Cómo vencerlo: un tajo, o saltarlo. Es el enemigo básico para enseñar el combate.

### Zombi corredor
- Patrulla a 80 px/s. Si el jugador está a menos de 320 px, acelera a 900 px/s² hasta 260 px/s.
- Embiste en línea recta. Si falla, frena por fricción y queda aturdido 0,8 s, una ventana para atacarlo.
- Cómo vencerlo: dash para atravesar la embestida, o un tajo bien cronometrado.

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
| Máquina de estados y detección | Pendiente |
| Zombi caminante | Pendiente |
| Zombi corredor | Pendiente |
| Zombi arquero y proyectiles | Pendiente |
| Zombi hinchado | Pendiente |
| Sierras y plataformas móviles | Pendiente |
| Samurái Caído | Pendiente |
| Oni | Pendiente |
