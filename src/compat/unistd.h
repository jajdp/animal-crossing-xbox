/* <unistd.h> minimo para el ABI de MSVC (UWP).
 *
 * El port lo incluye por costumbre POSIX pero apenas usa nada: getcwd en
 * pc_m_card.c (solo para un mensaje de diagnostico) y algun access.
 *
 * OJO con getcwd en UWP: una aplicacion de AppContainer no tiene directorio de
 * trabajo en el sentido habitual, y la version del CRT «store» puede no estar.
 * Aqui se devuelve "." , que es lo unico honesto: el llamador solo lo imprime.
 */
#ifndef ACGC_COMPAT_UNISTD_H
#define ACGC_COMPAT_UNISTD_H

#include <io.h>
#include <direct.h>
#include <string.h>

#ifndef F_OK
#define F_OK 0
#define X_OK 1
#define W_OK 2
#define R_OK 4
#endif

#ifndef access
#define access _access
#endif

#ifndef unlink
#define unlink _unlink
#endif

#ifndef rmdir
#define rmdir _rmdir
#endif

static char* acgc__getcwd(char* buf, size_t tam) {
    if (buf == NULL || tam < 2) {
        return NULL;
    }
    buf[0] = '.';
    buf[1] = '\0';
    return buf;
}

#ifndef getcwd
#define getcwd acgc__getcwd
#endif

#endif /* ACGC_COMPAT_UNISTD_H */
