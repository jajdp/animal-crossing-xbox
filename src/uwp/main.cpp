// Punto de entrada WinRT de Animal Crossing para Xbox Series X.
//
// El juego es un programa SDL2 + OpenGL normal: su main() vive en pc_main.c y se
// compila renombrado a acgc_game_main (-Dmain=acgc_game_main), porque en UWP el
// main de verdad lo pone SDL con SDL_WinRTRunApp.
//
// Como en los ports de Diddy Kong Racing y Banjo-Kazooie, la plantilla C++/CX de
// SDL no se usa: lo que hay que hacer cabe en C++ normal, y ademas clang no
// compila C++/CX.
//
// TRES COSAS QUE NO SON OPCIONALES:
//
// 1. EL DIRECTORIO DE TRABAJO. El juego abre todo con rutas relativas ("rom",
//    "save/card_a", "shaders/default.frag", "settings.ini") dando por hecho que
//    puede escribir donde esta. En UWP la carpeta de instalacion es de SOLO
//    LECTURA. Se resuelve de una vez apuntando el directorio de trabajo a
//    LocalState —SetCurrentDirectory SI esta permitido dentro de un
//    AppContainer, esta en WindowsApp.lib— y copiando alli los shaders, que son
//    lo unico que viaja en el paquete y el juego necesita leer. Asi no hay que
//    tocar ni una linea del codigo del juego.
//
// 2. ACTIVAR LA CoreWindow. Una aplicacion WinRT que no llama a Activate() al
//    arrancar se da por colgada y el sistema la cierra a los pocos segundos, sin
//    dejar volcado. Aqui la ventana la crea SDL, que normalmente activa sola,
//    pero se hace explicito porque en Banjo-Kazooie eso costo horas de
//    diagnostico y no cuesta nada dejarlo puesto.
//
// 3. LA BITACORA DE ARRANQUE. En una consola no hay stderr. Si algo lanza dentro
//    del juego, la excepcion sube al bucle de WinRT, que la convierte en un
//    fail-fast (0xC0000409) y el volcado solo ensena el fail-fast, no la causa.
//    Escribir cuatro lineas en LocalState\arranque.txt es la diferencia entre
//    diagnosticar y adivinar.
#include <windows.h>

#include <cstdio>
#include <cstring>
#include <exception>

#include <winrt/Windows.UI.Core.h>

#include "SDL2/SDL.h"

extern "C" int acgc_game_main(int argc, char* argv[]);

static char s_local[1024];
static char s_instalacion[1024];

static void Apunta(const char* texto) {
    if (s_local[0] == '\0') {
        return;
    }
    char ruta[1200];
    snprintf(ruta, sizeof(ruta), "%sarranque.txt", s_local);
    FILE* f = fopen(ruta, "a");
    if (f != NULL) {
        fputs(texto, f);
        fputc('\n', f);
        fclose(f);
    }
}

// Copia un archivo de la carpeta de instalacion a LocalState si aun no esta.
static void CopiaSiFalta(const char* relativo) {
    char origen[1200];
    char destino[1200];
    snprintf(origen, sizeof(origen), "%s%s", s_instalacion, relativo);
    snprintf(destino, sizeof(destino), "%s%s", s_local, relativo);
    for (char* p = destino; *p; p++) {
        if (*p == '/') {
            *p = '\\';
        }
    }
    if (GetFileAttributesA(destino) != INVALID_FILE_ATTRIBUTES) {
        return;
    }
    // Crear las carpetas intermedias
    char carpeta[1200];
    snprintf(carpeta, sizeof(carpeta), "%s", destino);
    char* ultima = strrchr(carpeta, '\\');
    if (ultima != NULL) {
        *ultima = '\0';
        CreateDirectoryA(carpeta, NULL);
    }
    CopyFileA(origen, destino, TRUE);
}

static void PreparaEntorno() {
    char* base = SDL_GetBasePath();
    if (base != NULL) {
        snprintf(s_instalacion, sizeof(s_instalacion), "%s", base);
        SDL_free(base);
    }
    // Con organizacion y aplicacion vacias, SDL2 devuelve la raiz de LocalState.
    char* pref = SDL_GetPrefPath("", "");
    if (pref != NULL) {
        snprintf(s_local, sizeof(s_local), "%s", pref);
        SDL_free(pref);
    }

    Apunta("");
    Apunta("=== arranque ===");
    char linea[2600];
    snprintf(linea, sizeof(linea), "[uwp] instalacion: %s", s_instalacion);
    Apunta(linea);
    snprintf(linea, sizeof(linea), "[uwp] LocalState : %s", s_local);
    Apunta(linea);

    // Los shaders viven en el paquete (solo lectura) y el juego los abre con
    // ruta relativa: se copian a LocalState la primera vez.
    CopiaSiFalta("shaders\\default.vert");
    CopiaSiFalta("shaders\\default.frag");

    // Variables de entorno para Mesa, desde un archivo de LocalState.
    //
    // Mesa se configura por variables de entorno (GALLIUM_DRIVER, MESA_DEBUG…), y en
    // UWP no hay forma de ponerlas desde fuera: `getenv` devuelve NULL para todo lo
    // que no haya puesto el propio proceso. Ponerlas aqui con _putenv_s SI funciona,
    // porque Mesa las lee del mismo CRT.
    //
    // Leerlas de un archivo en vez de compilarlas permite **cambiar de driver sin
    // reconstruir ni reinstalar nada**: basta subir `mesa-env.txt` a LocalState con
    // lineas `CLAVE=valor`. Con `GALLIUM_DRIVER=llvmpipe` se pasa a render por
    // software, que es como se distingue un fallo de GPU de uno del juego.
    {
        char ruta[1200];
        snprintf(ruta, sizeof(ruta), "%smesa-env.txt", s_local);
        FILE* f = fopen(ruta, "r");
        if (f != NULL) {
            char linea[512];
            while (fgets(linea, sizeof(linea), f) != NULL) {
                char* fin = linea + strlen(linea);
                while (fin > linea && (fin[-1] == '\n' || fin[-1] == '\r' || fin[-1] == ' ')) {
                    *--fin = '\0';
                }
                char* igual = strchr(linea, '=');
                if (igual == NULL || linea[0] == '#') {
                    continue;
                }
                *igual = '\0';
                _putenv_s(linea, igual + 1);
                char aviso[600];
                snprintf(aviso, sizeof(aviso), "[uwp] entorno: %s=%s", linea, igual + 1);
                Apunta(aviso);
            }
            fclose(f);
        }
    }

    if (s_local[0] != '\0') {
        if (SetCurrentDirectoryA(s_local)) {
            Apunta("[uwp] directorio de trabajo = LocalState");
        } else {
            snprintf(linea, sizeof(linea), "[uwp] SetCurrentDirectory FALLO: %lu", GetLastError());
            Apunta(linea);
        }
    }
}

// El port escribe un diagnostico muy completo por la salida estandar —que disco
// cargo, cuantos archivos indexo de la FST, que assets faltan— y en una consola
// no hay consola donde verlo. Redirigirla a un archivo de LocalState convierte
// ese diagnostico en la unica herramienta seria que hay aqui: sin esto, un
// arranque fallido es una pantalla negra y nada mas.
static void RedirigeSalida() {
    if (s_local[0] == '\0') {
        return;
    }
    char ruta[1200];
    snprintf(ruta, sizeof(ruta), "%ssalida.txt", s_local);
    FILE* f = nullptr;
    if (freopen_s(&f, ruta, "w", stdout) == 0 && f != nullptr) {
        setvbuf(stdout, nullptr, _IONBF, 0);  // sin buffer: si muere, lo escrito ya esta
    }
    snprintf(ruta, sizeof(ruta), "%serrores.txt", s_local);
    if (freopen_s(&f, ruta, "w", stderr) == 0 && f != nullptr) {
        setvbuf(stderr, nullptr, _IONBF, 0);
    }
}

// Una violacion de acceso NO es una excepcion de C++: el try/catch de abajo no la
// ve, el proceso se va en seco y en la consola no queda ni rastro. Un manejador
// vectorizado se entera ANTES que nadie y deja escrito el codigo y la direccion,
// que es la diferencia entre saber donde mirar y volver a empezar.
//
// Las dos funciones se declaran a mano porque con WINAPI_FAMILY_APP las cabeceras
// de Windows las esconden (estan en la particion de escritorio), aunque el
// sistema si las exporta y WindowsApp.lib las resuelve.
extern "C" {
__declspec(dllimport) PVOID WINAPI AddVectoredExceptionHandler(ULONG, PVECTORED_EXCEPTION_HANDLER);
extern char __ImageBase;
}

static LONG CALLBACK CazaExcepciones(EXCEPTION_POINTERS* info) {
    const EXCEPTION_RECORD* r = info->ExceptionRecord;

    // 0xE06D7363 es «se ha lanzado una excepcion de C++». El juego lanza muchas y
    // las recoge; anotarlas solo llena el archivo de ruido y tapa lo que importa.
    if (r->ExceptionCode == 0xE06D7363) {
        return EXCEPTION_CONTINUE_SEARCH;
    }

    char linea[700];
    // De que DLL es la direccion: sin esto, un fallo dentro de Mesa, de SDL o del
    // CRT son indistinguibles, y son tres diagnosticos muy distintos.
    char modulo[320] = "(desconocido)";
    HMODULE h = NULL;
    if (GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                               GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           (LPCWSTR)r->ExceptionAddress, &h) && h != NULL) {
        wchar_t ancho[260] = L"";
        if (GetModuleFileNameW(h, ancho, 260) > 0) {
            WideCharToMultiByte(CP_UTF8, 0, ancho, -1, modulo, (int)sizeof(modulo), NULL, NULL);
        }
    }

    snprintf(linea, sizeof(linea),
             "[uwp] EXCEPCION DEL SISTEMA 0x%08lX en %p\n[uwp]   modulo: %s (+0x%llX)",
             r->ExceptionCode, r->ExceptionAddress, modulo,
             (unsigned long long)((uintptr_t)r->ExceptionAddress - (uintptr_t)h));
    Apunta(linea);
    if (r->ExceptionCode == EXCEPTION_ACCESS_VIOLATION && r->NumberParameters >= 2) {
        snprintf(linea, sizeof(linea), "[uwp]   %s la direccion %p",
                 r->ExceptionInformation[0] ? "escribiendo en" : "leyendo de",
                 (void*)r->ExceptionInformation[1]);
        Apunta(linea);
    }
    return EXCEPTION_CONTINUE_SEARCH;  // solo mirar, no tocar
}

// LATIDO. El juego se para siempre en el mismo punto y sin dejar excepcion, y hay
// dos explicaciones muy distintas con el mismo aspecto: (a) el proceso muere de
// golpe, o (b) se queda colgado dentro de un fotograma y el shell de WinRT lo cierra
// por no responder. Un hilo que escribe la hora cada medio segundo las separa: si
// los latidos siguen despues de la ultima linea del juego, estaba COLGADO, no muerto.
static DWORD WINAPI Latido(LPVOID) {
    ULONGLONG t0 = GetTickCount64();
    for (int i = 0; i < 240; i++) {  // dos minutos como mucho
        Sleep(500);
        char linea[128];
        snprintf(linea, sizeof(linea), "[uwp] latido t=%.1f s",
                 (double)(GetTickCount64() - t0) / 1000.0);
        Apunta(linea);
    }
    return 0;
}

static int bootstrap(int argc, char** argv) {
    PreparaEntorno();
    RedirigeSalida();
    AddVectoredExceptionHandler(1, CazaExcepciones);
    CloseHandle(CreateThread(NULL, 0, Latido, NULL, 0, NULL));

    try {
        auto ventana = winrt::Windows::UI::Core::CoreWindow::GetForCurrentThread();
        ventana.Activate();
        // El tamano de la CoreWindow es el de la superficie que acaba creando SDL, y
        // en una consola que saca 4K son 3840x2160: solo la cadena de intercambio y
        // su bufer de profundidad se comen ~100 MB. Conviene tenerlo por escrito.
        auto r = ventana.Bounds();
        char linea[160];
        snprintf(linea, sizeof(linea), "[uwp] CoreWindow activada, %.0fx%.0f",
                 r.Width, r.Height);
        Apunta(linea);
    } catch (...) {
        Apunta("[uwp] NO se pudo activar la CoreWindow");
    }

    // --verbose SIEMPRE en la consola, y no es un descuido.
    //
    // El port esconde casi todo su diagnostico detras de esa bandera: la version y
    // el renderizador de OpenGL, la imagen de disco que abrio, el listado de la FST,
    // cuantos assets cargo y los mensajes de arranque del propio juego. Sin ella el
    // registro se queda en ocho lineas inutiles. En una PC se omite porque escribir
    // en la terminal hunde los fotogramas; aqui la salida va a un archivo y el coste
    // es despreciable al lado de quedarse a ciegas.
    char arg0[] = "AnimalCrossing";
    char arg1[] = "--verbose";
    char* argv_uwp[] = {arg0, arg1, nullptr};

    Apunta("[uwp] entrando al juego (con --verbose)");
    try {
        int r = acgc_game_main(2, argv_uwp);
        char linea[128];
        snprintf(linea, sizeof(linea), "[uwp] el juego devolvio %d", r);
        Apunta(linea);
        return r;
    } catch (const std::exception& e) {
        char linea[1024];
        snprintf(linea, sizeof(linea), "[uwp] EXCEPCION: %s", e.what());
        Apunta(linea);
        return 1;
    } catch (...) {
        Apunta("[uwp] EXCEPCION desconocida");
        return 1;
    }
}

int CALLBACK WinMain(HINSTANCE, HINSTANCE, LPSTR, int) {
    return SDL_WinRTRunApp(bootstrap, NULL);
}
