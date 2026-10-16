/* <strings.h> minimo para el ABI de MSVC.
 *
 * MSVC no lo trae; sus equivalentes viven en <string.h> con guion bajo.
 * El port solo usa strcasecmp y strncasecmp.
 */
#ifndef ACGC_COMPAT_STRINGS_H
#define ACGC_COMPAT_STRINGS_H

#include <string.h>

#ifndef strcasecmp
#define strcasecmp _stricmp
#endif

#ifndef strncasecmp
#define strncasecmp _strnicmp
#endif

#endif /* ACGC_COMPAT_STRINGS_H */
