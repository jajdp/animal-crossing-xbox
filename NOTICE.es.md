# Aviso

*(English: [NOTICE.md](NOTICE.md))*

## Sin afiliación

Esto es un proyecto de aficionado, no oficial y sin ánimo de lucro. **No está afiliado a Nintendo ni
a Microsoft**, ni cuenta con su respaldo o aprobación, ni lo está con
[ACreTeam](https://github.com/ACreTeam/ac-decomp) ni con los autores del port de PC o de su
[fork de 64 bits](https://github.com/birabittoh/ACGC-PC-Port). *Animal Crossing*, *Xbox* y todos los
nombres y marcas relacionados son de sus respectivos propietarios, y aquí se usan solo para decir con
qué funciona esto.

Aquí no se vende nada, y nada de esto está monetizado.

## Qué no distribuye este repositorio

Ni imagen del disco. Ni datos ni recursos del juego. Ni ejecutable compilado. Ni `.msix`. Ni
partidas. Ni mosaicos del paquete (`package/Assets/` está vacía, y
[`docs/ASSETS.es.md`](docs/ASSETS.es.md) te pide los tuyos).

**Ni ninguna de las bibliotecas de UWP**: Mesa, SDL2 y `libuwp` son binarios de otros. La guía dice
de dónde salen.

## Qué contiene de trabajo de otros

**Parches contra el fork de 64 bits.** Los trece parches citan las líneas del código del fork que
cada uno comprueba antes de escribir, para fallar en seguro en vez de estropear un árbol que no
reconoce. Ese fork tiene **licencia doble**: la decompilación que lleva, de ACreTeam, es
**CC0 1.0** (dominio público), y la capa de port es **MIT**, © 2026 FlyingMeta. Las dos lo permiten,
y este repositorio se publica bajo [la MIT](LICENSE), llevando con él el aviso del fork.

**`src/uwp/main.cpp` y `src/compat/`** son propios: el punto de entrada WinRT y tres cabeceras
pequeñas que hacen de las que MSVC no trae (`dirent.h`, `strings.h`, `unistd.h`).

**Aquí no hay capturas de pantalla.** Una captura de esto funcionando sería casi toda arte de
Nintendo.

## Retirada y contacto

Si tienes derechos sobre este material y quieres que algo de aquí se quite o se cambie, escribe a
**jajdpmail@gmail.com** diciendo a qué te opones y en calidad de qué escribes.

Las peticiones de quien tiene los derechos se atienden: se quita la parte en disputa, o se retira el
repositorio, sin discutir, y recibirás una respuesta confirmándolo.
