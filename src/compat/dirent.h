/* dirent.h minimo para compilar el port con el ABI de MSVC (UWP).
 *
 * MSVC no trae <dirent.h>. El port solo usa cuatro cosas —opendir, readdir,
 * closedir y el campo d_name—, asi que esto no pretende ser POSIX: cubre
 * exactamente lo que usan pc_disc.c (buscar la imagen de disco) y famicom.cpp
 * (listar las ROM de NES).
 *
 * Se usa FindFirstFileExW y no FindFirstFileW porque la primera es la que esta
 * en el conjunto de API permitido dentro de un AppContainer.
 *
 * Los nombres se convierten de UTF-16 a UTF-8: el juego compara extensiones en
 * ASCII, asi que con eso basta y se evita depender de la pagina de codigos.
 */
#ifndef ACGC_COMPAT_DIRENT_H
#define ACGC_COMPAT_DIRENT_H

#include <windows.h>
#include <stdlib.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

struct dirent {
    char d_name[MAX_PATH * 3 + 1]; /* UTF-8: hasta 3 bytes por unidad UTF-16 */
};

typedef struct DIR {
    HANDLE handle;
    WIN32_FIND_DATAW datos;
    int primera;
    struct dirent entrada;
} DIR;

static void acgc__a_utf8(const wchar_t* ancho, char* destino, int tam) {
    int n = WideCharToMultiByte(CP_UTF8, 0, ancho, -1, destino, tam, NULL, NULL);
    if (n <= 0) {
        destino[0] = '\0';
    }
}

static DIR* opendir(const char* ruta) {
    wchar_t patron[MAX_PATH];
    int n;
    DIR* d;

    n = MultiByteToWideChar(CP_UTF8, 0, ruta, -1, patron, MAX_PATH - 3);
    if (n <= 0) {
        return NULL;
    }
    n--; /* sin el terminador */
    if (n > 0 && (patron[n - 1] == L'\\' || patron[n - 1] == L'/')) {
        n--;
    }
    patron[n] = L'\\';
    patron[n + 1] = L'*';
    patron[n + 2] = L'\0';

    d = (DIR*)calloc(1, sizeof(DIR));
    if (d == NULL) {
        return NULL;
    }
    d->handle = FindFirstFileExW(patron, FindExInfoBasic, &d->datos,
                                 FindExSearchNameMatch, NULL, 0);
    if (d->handle == INVALID_HANDLE_VALUE) {
        free(d);
        return NULL;
    }
    d->primera = 1;
    return d;
}

static struct dirent* readdir(DIR* d) {
    if (d == NULL || d->handle == INVALID_HANDLE_VALUE) {
        return NULL;
    }
    if (!d->primera) {
        if (!FindNextFileW(d->handle, &d->datos)) {
            return NULL;
        }
    }
    d->primera = 0;
    acgc__a_utf8(d->datos.cFileName, d->entrada.d_name, (int)sizeof(d->entrada.d_name));
    return &d->entrada;
}

static int closedir(DIR* d) {
    if (d == NULL) {
        return -1;
    }
    if (d->handle != INVALID_HANDLE_VALUE) {
        FindClose(d->handle);
    }
    free(d);
    return 0;
}

#ifdef __cplusplus
}
#endif

#endif /* ACGC_COMPAT_DIRENT_H */
