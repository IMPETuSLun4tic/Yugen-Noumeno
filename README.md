# Yugen-Noumeno

Juego espacial local en Python con vista isométrica simulada, exploración, combate
contra enemigos y progreso guardado. La referencia de estilo es la navegación y
selección de objetivos de un
juego espacial como DarkOrbit; las reglas y la implementación de este proyecto se
definen aquí. No se incorporaron recursos de ese juego.

## Cómo empezar

1. Ejecuta el programa y elige **Nueva partida** o **Cargar partida**.
2. Comienzas en una base segura situada en el centro de un mapa de 6000 × 6000 píxeles.
3. Haz clic en el espacio para viajar y en un enemigo para seleccionarlo.
4. Selecciona un arma con `1`, `2` o `3`; repite la tecla para iniciar el disparo automático.
5. Consigue créditos por bajas y regresa a la base para comprar mejoras con `E`.
6. Usa `Esc` para pausar y guardar; al cerrar normalmente se guarda la sesión.

La cámara mantiene siempre la nave en el centro de la ventana. El movimiento se
limita a los bordes del mundo; ya no se reaparece por el extremo contrario.

## Controles

| Entrada | Acción |
| --- | --- |
| Clic izquierdo en espacio vacío | Fijar un destino; la nave se detiene al alcanzarlo. |
| Clic izquierdo en un enemigo | Seleccionar ese objetivo sin cambiar el destino de viaje. |
| `1` | Seleccionar láser; repetir para iniciar o detener su disparo automático. |
| `2` | Seleccionar misiles; repetir para iniciar o detener su disparo automático. |
| `3` | Seleccionar haz; repetir para iniciar o detener su disparo automático. |
| `E` dentro de la base | Abrir la tienda y detener el viaje. |
| `Esc` | Pausar; desde pausa o tienda, volver al juego. |
| Cerrar ventana / Guardar y salir | Autoguardar y cerrar. |

Al cambiar de arma se detiene la anterior. Las armas necesitan un enemigo vivo
seleccionado y dentro de alcance. Si queda fuera de alcance, el disparo espera;
si el objetivo muere o se desactiva por distancia, hay que seleccionar otro y
reactivar el disparo. No se dispara hacia el cursor ni se controla con WASD.
El minimapa es informativo: pulsarlo no fija destinos.

## Combate, vida y escudo

La nave empieza con **100 de vida y 100 de escudo**. Los enemigos tienen **100 de
vida, sin escudo**, y disparan proyectiles de **20 de daño**, como máximo uno por
segundo por enemigo. El contacto entre naves no causa una muerte instantánea.

Cada impacto reparte el daño así:

```text
danio_absorbido = min(escudo_disponible, danio * 0.80)
danio_a_vida = danio - danio_absorbido
```

Un impacto de 20 consume 16 de escudo y 4 de vida. Con solo 5 de escudo, consume
esos 5 y causa 15 de daño a la vida. Sin escudo, todo el daño pasa a la vida.
Las cantidades se limitan a los puntos que realmente quedan.

Una burbuja azul rodea la nave mientras conserva escudo. Los proyectiles enemigos
impactan en su borde antes de alcanzar el casco; la burbuja destella al absorber
daño. Es un efecto de absorción, sin devolución de daño al atacante. Los números
flotantes azules muestran pérdida de escudo, los rojos pérdida de vida y los
amarillos daño infligido a enemigos.

Después de **5 segundos sin disparar, infligir ni recibir daño**, se regeneran **5 de vida y
10 de escudo por segundo**, hasta sus máximos. La pausa y la tienda detienen el
reloj de simulación. Un disparo fallido por falta de objetivo o alcance no reinicia
la espera; recibir daño o efectuar un disparo sí la reinicia.

### Armas disponibles

| Slot | Arma | Daño inicial | Cadencia o duración | Alcance |
| --- | --- | --- | --- | --- |
| `1` | Láser | 80 por impacto | Un disparo cada 0,28 s | 650 píxeles |
| `2` | Misil | 120 por enemigo afectado | Un lanzamiento cada 0,5 s | 750 píxeles |
| `3` | Haz | 260 por segundo | Hasta 3 s activo; 3 s de enfriamiento | 820 píxeles |

Láseres y misiles apuntan a la posición del objetivo al disparar y viajan en línea
recta; los misiles no son teledirigidos. Su explosión afecta a los enemigos cuyos
centros están a 80 píxeles o menos del impacto. No hay consumo de munición.

El haz sigue al objetivo seleccionado, causa daño proporcional al tiempo y se
interrumpe al cambiar de arma, detener el disparo, perder el objetivo, salir de
alcance o entrar en la base. Interrumpir un haz activo inicia su enfriamiento.
Con el disparo automático activo y un objetivo válido, vuelve a activarse después
de la recarga. La muerte del objetivo detiene el disparo automático.

### Derrota

La nave se destruye al llegar a cero de vida y la simulación de combate se detiene.
Los restos, destellos y números flotantes terminan su animación detrás del menú.
El menú permite comenzar otra partida, cargar la guardada o salir. Guardar una nave
muerta conserva la derrota; cargarla no la revive. Salir normalmente también
autoguarda ese estado y reemplaza el guardado anterior.

## Mundo, enemigos y minimapa

El mapa se divide en sectores de 750 × 750 píxeles. Se generan candidatos a
enemigos al visitar sectores cercanos, con una semilla propia de la partida.
Solo se actualizan hasta 25 enemigos vivos a 1100 píxeles o menos de la nave.

Los enemigos detectan al jugador a 520 píxeles, se acercan y disparan a 400 píxeles
o menos. Cuando el jugador queda lejos o entra en la base, vuelven hacia su origen.
Los que quedan fuera de activación conservan su posición, vida y temporizador.
Al regresar no recuperan vida ni reaparecen los que ya murieron.

Cada sector genera como máximo dos enemigos y actualmente no hay reaparición por
tiempo; por tanto, la población de una partida es finita. Los candidatos cercanos
a la base se omiten. La generación antigua por intervalos y el aumento de velocidad
por baja se sustituyeron por este sistema de exploración y activación por proximidad.

El minimapa muestra la base, el jugador, la región visible y los enemigos activos.
Los enemigos de zonas lejanas no se muestran ni se simulan. En los límites, la
cámara sigue centrada en la nave y puede mostrar espacio fuera del mapa; las líneas
del borde indican el área navegable.

## Vista isométrica y efectos de impacto

El mundo conserva sus coordenadas, distancias y colisiones en 2D. La presentación
rota los ejes 45 grados y comprime su profundidad vertical al 50 %, formando una
cuadrícula diagonal con proporción 2:1. La cámara mantiene centrada la nave y la
transformación inversa traduce los clics al mismo mundo lógico.

La base se dibuja como una plataforma con espesor, luces y anillos elípticos. Las
naves reutilizan los sprites existentes con la orientación proyectada, espesor
aparente y sombras; se dibujan según su profundidad para resolver superposiciones.
El minimapa conserva la orientación lógica del mapa y delimita con un polígono
la región que muestra la cámara inclinada. Los textos y barras permanecen planos
para facilitar su lectura; los números de daño ascienden verticalmente en pantalla.

Los efectos se generan en los puntos donde se resuelven los impactos:

| Impacto | Efecto visual |
| --- | --- |
| Escudo | Arco luminoso localizado en el lado golpeado, ondulación y partículas azules; el arco sigue a la nave mientras se desvanece. |
| Casco | Destello blanco y naranja y chispas que se dispersan desde el contacto. |
| Misil | Explosión con núcleo luminoso, anillos expansivos y fragmentos con altura aparente. |
| Haz | Núcleo de contacto brillante y emisiones espaciadas de partículas. |
| Destrucción | Explosión más amplia y restos que se frenan, caen y desaparecen. |

El sistema admite hasta 256 partículas y 64 pulsos simultáneos. La emisión visual
del haz se limita a una cada 0,06 segundos; el daño continuo mantiene su frecuencia
original. Los efectos utilizan su propio generador aleatorio y no cambian la
generación del mundo. Se congelan al pausar o abrir la tienda, y no se guardan.

Esta perspectiva se calcula con superficies de Pygame. No introduce un eje de
altura en el combate ni cambia el daño, alcance, velocidad o formato de partida.
La dirección iluminada de la burbuja representa un impacto visual, sin modificar
la distribución uniforme de energía del escudo.

## Base y tienda

La base está en `(3000, 3000)` y su zona segura tiene un radio de 320 píxeles.
Los enemigos se mantienen fuera de ella y sus proyectiles no pueden cruzarla.
Dentro se bloquean las armas y se retiran los proyectiles de la escena para que
entrar en la base no permita seguir atacando desde la zona segura.

Pulsa `E` dentro para abrir la tienda. Cada baja otorga **25 créditos**. Las tres
armas están disponibles desde el principio; la tienda mejora estas capacidades:

| Mejora | Incremento por nivel | Máximo |
| --- | --- | --- |
| Láser | +10 de daño | 5 niveles |
| Vida | +20 de vida máxima | 5 niveles |
| Escudo | +20 de escudo máximo | 5 niveles |

El siguiente nivel cuesta `75 × (nivel_actual + 1)` créditos: 75, 150, 225, 300 y
375. Comprar vida o escudo aumenta la capacidad máxima; la regeneración recupera
los puntos adicionales. No rellena inmediatamente la defensa ni permite comprar
fuera de la base, sin créditos suficientes o por encima del nivel máximo.

## Guardado de sesión

Se utiliza una sola partida en `partidas/partida.json`, relativa a la raíz del
proyecto e independiente del directorio desde el que se ejecute el programa.
La carpeta y el archivo se crean al guardar; no forman parte de una partida de
ejemplo incluida en el repositorio.

Se conservan:

- Posición, destino, orientación, vida y escudo de la nave.
- Arma seleccionada, tiempos de recarga y espera de regeneración.
- Créditos, bajas y niveles de mejoras.
- Semilla del mundo, sectores visitados y estado de cada enemigo generado, incluidos los muertos.

El objetivo seleccionado, el disparo automático, los proyectiles en vuelo y los
efectos visuales son transitorios y no se restauran. Guardar un haz activo lo
convierte en un enfriamiento al cargar para evitar reanudar daño automáticamente.
El destino guardado sí se conserva y el viaje puede continuar al cargar.

**Nueva partida** pide confirmación cuando ya existe una sesión o un guardado.
Empezar de nuevo no borra inmediatamente el archivo anterior: lo sustituirá el
siguiente guardado manual o al salir.

El formato JSON tiene versión y validación de tipos, rangos, coordenadas,
identificadores y duplicados. Un archivo corrupto o incompatible se rechaza con
un mensaje y no reemplaza la sesión actual. La escritura utiliza un archivo
temporal, lo sincroniza y después reemplaza el archivo principal. Si falla el
autoguardado, el juego permite reintentar, volver o salir sin guardar.

El autoguardado corresponde al cierre normal; no cubre terminar el proceso por
la fuerza ni un cierre del sistema antes de guardar. No hay varias ranuras ni
migración entre futuras versiones del formato.

## Requisitos y ejecución

El manifiesto [pyproject.toml](pyproject.toml) requiere Python **3.14 o superior** y
declara `numpy>=2.5.1` y `psutil>=7.2.2`. El juego también necesita el módulo
`pygame`, proporcionado en el entorno local por **pygame-ce 2.5.7**. Esa dependencia
continúa sin estar declarada en el manifiesto ni en `uv.lock`; no basta con instalar
solo las dependencias declaradas.

Desde la raíz del proyecto en PowerShell, para preparar un entorno nuevo:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install "numpy>=2.5.1" "psutil>=7.2.2" "pygame-ce==2.5.7"
```

Si el entorno ya existe, utiliza su intérprete sin recrearlo. Para ejecutar:

```powershell
.\.venv\Scripts\python.exe Python_Game\main.py
```

Los recursos se resuelven desde la ubicación de `resources.py`, por lo que también
funciona ejecutar `main.py` desde `Python_Game` o desde un IDE con otro directorio
de trabajo. La ventana mide 1366 × 768 y el bucle limita el objetivo a 100 FPS.
El paso de simulación se limita a 0,05 s para evitar saltos grandes después de un
bloqueo; el juego no recupera tiempo de simulación perdido durante ese bloqueo.

## Estructura del proyecto

```text
Yugen-Noumeno/
|-- README.md
|-- LICENSE
|-- pyproject.toml
|-- uv.lock
|-- partidas/                 Se crea al guardar una sesión
|   `-- partida.json
|-- tests/
|   |-- test_mecanicas.py     Pruebas de reglas, persistencia e integración
|   `-- test_efectos.py       Proyección, impactos y ciclo de vida visual
`-- Python_Game/
    |-- main.py              Aplicación y transiciones de menús
    |-- config.py            Parámetros del juego
    |-- partida.py           Estado y actualización de la sesión
    |-- mundo.py             Cámara, sectores y activación de enemigos
    |-- entities.py          Nave, enemigos, proyectiles y elementos de fondo
    |-- combate.py           Armas, impactos, daño y recompensas
    |-- efectos.py           Partículas, pulsos y destellos transitorios
    |-- logic.py             Traducción de eventos a acciones de juego
    |-- interfaz.py          HUD, minimapa, tienda y menús
    |-- render.py            Representación del mundo y sus entidades
    |-- guardado.py          Formato JSON, validación y escritura de partidas
    |-- tienda.py            Niveles, precios y aplicación de mejoras
    |-- resources.py         Imágenes, audio y creación del fondo
    |-- utils.py             Utilidades existentes de geometría, audio y bloom
    |-- performance.py       Monitor de rendimiento existente
    |-- Readme.txt           Nota original
    |-- jugador.png
    |-- enemigos.png
    |-- nebulosa.png
    |-- laser.wav
    |-- missile.wav
    |-- explosion.wav
    `-- beam.wav
```

## Arquitectura y funcionamiento

| Componente | Responsabilidad |
| --- | --- |
| [Aplicacion](Python_Game/main.py) | Gestionar ventana, recursos y estados `inicio`, `jugando`, `pausa`, `tienda`, `derrota`, `confirmar_nueva` y `error_salida`. Coordinar eventos, guardado, actualización y presentación. |
| [Partida](Python_Game/partida.py) | Mantener la nave, el mundo, las mejoras, los créditos, el objetivo y los efectos transitorios de una sesión. |
| [Mundo y Camara](Python_Game/mundo.py) | Convertir coordenadas, generar sectores y actualizar exclusivamente enemigos próximos, excluyendo la zona segura. |
| [Entidades](Python_Game/entities.py) | Conservar estado y comportamiento individual. El daño a la nave devuelve un resultado con las pérdidas de vida y escudo. |
| [Combate](Python_Game/combate.py) | Comprobar alcance y recarga, generar proyectiles, resolver colisiones, aplicar el haz y entregar recompensas una sola vez por baja. |
| [Interfaz](Python_Game/interfaz.py) | Dibujar defensas, slots, objetivo, minimapa y botones; separar los controles de pantalla de las coordenadas del mundo. |
| [Renderizado](Python_Game/render.py) | Dibujar entidades con la transformación de cámara, la base, la burbuja y los indicadores de destino y selección. |
| [SistemaEfectos](Python_Game/efectos.py) | Emitir, actualizar y dibujar partículas y pulsos con vida y cantidad limitadas; mantenerlos separados de las reglas de daño y de los datos persistentes. |
| [AlmacenPartida](Python_Game/guardado.py) | Transformar estado persistente a JSON y reconstruir una partida validada sin reutilizar el estado parcial de una carga fallida. |
| [Tienda](Python_Game/tienda.py) | Comprobar acceso, saldo y límites antes de cobrar y aplicar una mejora. |

### Orden de actualización

1. Procesar eventos de ventana, menús o controles de juego.
2. Si se está jugando, mover y orientar la nave y reducir sus temporizadores.
3. Generar sectores próximos, seleccionar enemigos activos y actualizar su movimiento.
4. Validar el objetivo y bloquear el combate si la nave entra en la base.
5. Procesar disparo del jugador, disparo enemigo e impactos de proyectiles.
6. Regenerar defensas si no hubo combate y ha transcurrido la espera.
7. Centrar la cámara y actualizar los marcadores, partículas y pulsos de impacto.
8. Actualizar el fondo con parallax y reproducir los eventos de audio.
9. Dibujar el mundo, aplicar bloom y añadir la interfaz y los menús.

Las colisiones de proyectiles comprueban el segmento recorrido durante el paso,
no solo su posición final, para reducir impactos perdidos por velocidad. Un
proyectil láser se consume en el primer enemigo alcanzado. La base intercepta
los disparos que cruzan su perímetro antes de alcanzar un objetivo al otro lado.

El estado de combate y el guardado no dependen de superficies o canales de audio.
El fondo conserva las clases visuales existentes. Si faltan imágenes se utilizan
figuras; si falta audio se intenta sintetizar tonos, y si no hay dispositivo de
audio se permite continuar sin sonido. El monitor existente sigue actualizándose;
el HUD presenta los FPS, sin panel de CPU y memoria.

## Configuración y próximos cambios

Los tamaños del mundo, radios, daños, regeneración, alcances, cadencias, precios y
límites están en [config.py](Python_Game/config.py). Las distancias se expresan en
píxeles, velocidades en píxeles por segundo y temporizadores en segundos.

`COMPRESION_ISOMETRICA = 0.5` define la inclinación visual; debe mantenerse mayor
que cero y como máximo en uno. `ESCALA_SPRITE_ISOMETRICO` afecta solo al tamaño
dibujado de las naves. `MAX_PARTICULAS_IMPACTO`, `MAX_PULSOS_IMPACTO` e
`INTERVALO_EFECTO_HAZ_SEGUNDOS` controlan la carga de efectos visuales.

El escudo tiene un único depósito de energía. La concentración frontal, lateral
o posterior está prevista como una decisión futura, todavía sin implementar.
El reparto de daño y el resultado de absorción están separados de su dibujo para
que esa evolución pueda diseñarse sin mezclarla con los efectos de pantalla.

La activación actual conserva en memoria los enemigos de los sectores generados;
optimiza su actualización, sin descargar sus datos a disco durante la partida.
El tamaño de sector, los límites de identificadores y el formato persistente
están relacionados: cambiar la estructura del mapa requerirá revisar la versión
y la validación del guardado.

## Pruebas y verificación

Desde la raíz:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Las pruebas usan los controladores `dummy` de SDL y directorios temporales propios
dentro de `tests`, que se eliminan al terminar. No leen ni reemplazan tu partida
real. Cubren daño y escudo, regeneración, movimiento y cámara, slots y alcance,
impactos rápidos, misiles y haz, base segura, activación de enemigos, compras,
guardados válidos e inválidos y transiciones y renderizado de la aplicación.
También verifican proyección e inversa, orientación de sprites y selección en
distintas direcciones, contactos precisos, límites y caducidad de los efectos,
pausa de animaciones, restos tras la derrota y conservación del formato JSON.

La verificación automática no sustituye una partida manual para evaluar equilibrio,
comodidad de los controles, sonido real y rendimiento en pantalla. No hay un
formateador ni analizador estático configurado en el repositorio.

## Licencia

El proyecto mantiene la [licencia MIT](LICENSE), con copyright de 2025 a nombre de
Mariano.
