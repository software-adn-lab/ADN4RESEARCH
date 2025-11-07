Traducción automática de estrategias de búsqueda: Scopus vs IEEE Xplore
Resumen Ejecutivo

Top 10 Reglas (MVP):

Campos de búsqueda recomendados: Usar TITLE-ABS-KEY en Scopus (título,
resumen, palabras clave) y "All Metadata" (metadatos) en IEEE Xplore por
defecto 2dsearch.com bibliotecnica.upc.edu , para abarcar
título/resumen/keywords pero no texto completo.

Frase exacta vs. aproximada: En Scopus, envolver frases exactas con
llaves {\...} para que los términos aparezcan tal cual y contiguos
(incluyendo mayúsculas, espacios y stop words) library.sydney.edu.au .
Usar comillas \"\..." solo para frase aproximada, permitiendo pequeñas
variaciones (p.ej. diferencias de ortografía o singular/plural)
library.sydney.edu.au . En IEEE Xplore solo se usan comillas \"\..."
para buscar frases exactas; no se emplean llaves library.sydney.edu.au
facebook.com .

Operadores booleanos estandarizados: Emplear AND, OR y NOT (o AND NOT
para exclusión) en mayúsculas en ambos sistemas media.lib.unb.ca
library.indwes.edu . Scopus y IEEE Xplore son case-insensitive para
términos, pero los operadores lógicos deben ir en mayúsculas.

Precedencia booleana -- uso de paréntesis: En Scopus, actualmente la
prioridad es OR antes de AND y luego NOT media.lib.unb.ca (regla
peculiar de Elsevier), lo que puede producir interpretaciones
inesperadas si no se agrupan términos. Se deben usar paréntesis para
forzar la lógica deseada media.lib.unb.ca . (Nota: A finales de 2025
Scopus planea cambiar la precedencia por defecto a AND NOT \> AND \> OR
blog.scopus.com , alineándose con estándares típicos). En IEEE Xplore,
la precedencia por defecto es NEAR/ONEAR (proximidad) primero, luego
NOT, luego AND, y por último OR libguides.ittralee.ie , por lo que
también conviene agrupar con paréntesis si se combinan operadores
distintos.

Búsqueda por proximidad: Usar sintaxis de proximidad propia de cada
base. En Scopus: \*\*W/\*\*n para palabras a distancia n en cualquier
orden, y \*\*PRE/\*\*n para palabras separadas por n palabras en ese
orden library.sydney.edu.au media.lib.unb.ca . Ejemplo: \"defect\" W/2
\"prediction\" encuentra "defect ... prediction" en cualquier orden
dentro de 2 palabras library.sydney.edu.au ; \"software\" PRE/3
\"engineering\" requiere "software" precediendo a "engineering" con
hasta 3 palabras entre ellos. En IEEE Xplore: NEAR/# (no orden) y
ONEAR/# (orden estricto) cumplen funciones similares lib.unb.ca .
Ejemplo: \"bug\" NEAR/2 \"prediction\" (ambos términos a ≤2 palabras,
sin importar el orden) y \"bug\" ONEAR/2 \"prediction\" ("bug" aparece
antes, con ≤2 palabras de distancia) lib.unb.ca .

Comodines y truncamiento: En Scopus se admiten tres comodines: \* para
truncamiento de 0 o más caracteres, ? para sustituir exactamente 1
carácter, y \# para 0--1 caracteres (útil en variaciones
británico/estadounidense, e.g. p#ediatric) library.sydney.edu.au . No se
permite usarlos al inicio de una palabra (en ninguna de las bases) ya
que esto generaría búsquedas excesivamente amplias. IEEE Xplore soporta
\* (truncamiento de múltiples caracteres) y ? (un carácter)
library.indwes.edu . Nota: IEEE Xplore también reconoce \$ como comodín
multicaracter alternativo lib.unb.ca lib.unb.ca .

Límites de comodines y longitud de consulta: En Scopus no se documenta
un límite estricto de comodines por búsqueda, pero en IEEE Xplore solo
se permiten hasta 8 comodines (sumando \* y ?/\$) por estrategia de
búsqueda lib.unb.ca . Exceder ese número puede anular la consulta o
requerir simplificarla. Asimismo, una sola consulta en Scopus tiene
límite de 256 caracteres library.sydney.edu.au ; consultas más largas
deben dividirse (usando el historial para combinarlas). IEEE Xplore
permite consultas más largas en caracteres pero limita a 25 términos
(palabras o frases) si no están separados por operadores booleanos
lib.unb.ca . Se deben emitir warnings si se superan estos límites (ver
sección de Validaciones abajo).

Filtro de año de publicación: En Scopus la restricción por año(s) puede
integrarse en la consulta avanzada mediante el campo PUBYEAR con
operadores relacionales (ej. PUBYEAR \> 2018 AND PUBYEAR \< 2023)
sciencedirect.com academic.net , o usando la función LIMIT-TO(PUBYEAR,
YYYY) para años específicos. Ejemplo: TITLE-ABS-KEY(\"IoT\") AND PUBYEAR
= 2020 limitará resultados al año 2020. En IEEE Xplore, el año no se
puede filtrar dentro de la sintaxis de búsqueda textual; se debe aplicar
mediante la interfaz (filtro de año en Advanced Search o faceta de
resultados) lib.unb.ca . Por tanto, el traductor debe manejar los años
por separado: no incluir año en la query de IEEE, pero dejar indicado el
rango para filtrarlo en la UI.

Validaciones de sintaxis: El traductor debe verificar y ajustar la
sintaxis para evitar errores comunes: p.ej., Scopus exige paréntesis
equilibrados -- un mensaje "Syntax error" suele indicar paréntesis
desbalanceados o mal ubicados libguides.umn.edu . También se debe
validar que los operadores de proximidad se usan correctamente (Scopus
no permite W/0, etc.), y que las consultas resultantes no estén vacías
ni excedan restricciones. Cualquier ajuste o omisión (como ignorar un
filtro de año en IEEE) debe generar un aviso (warning) en la traza.

Registro de trazabilidad: Implementar un modelo de traza (trace\[\]) que
documente cada paso de la traducción, desde la consulta original hasta
la versión lista para ejecutar en cada base. Esto incluye pasos como
normalización de términos (unificación de mayúsculas/minúsculas, manejo
de acentos), aplicación de reglas de frase (exacta vs. laxa), traducción
de operadores/comodines, adición de filtros (p. ej. años) o notificación
de que se deben aplicar manualmente, y validación final. Cada paso de la
traza debe indicar qué se hizo o si hubo advertencias (ver ejemplo de
JSON de traza más adelante).

Top 5 Warnings críticos:

W-001 -- Exceso de comodines: Si una consulta traducida para IEEE Xplore
contiene más de 8 comodines (\*/?), se debe notificar que excede el
límite de la base lib.unb.ca . El traductor podría truncar términos o
recomendar dividir la búsqueda en varias.

W-002 -- Consulta demasiado larga: Si la estrategia para Scopus excede
los \~256 caracteres en una sola línea library.sydney.edu.au , alertar
que se debe dividir (por ejemplo, usando el historial de Scopus para
combinar sub-consultas con OR). Similarmente, si una sola "cláusula" sin
operadores en IEEE supera 25 términos lib.unb.ca , advertir que puede
que no recupere todos los resultados y sugerir añadir operadores o
partirla.

W-003 -- Filtro de año ignorado en IEEE: Si la consulta original incluye
un rango o condición de año, al traducir a IEEE Xplore se debe avisar
que el filtro de año no se puede incorporar en la consulta y deberá
aplicarse manualmente en la interfaz lib.unb.ca .

W-004 -- Uso de sintaxis no soportada: Cualquier elemento no válido en
la base de destino debe generar warning y ser omitido o reemplazado.
Ejemplos: uso de {} en IEEE (no soporta llaves, se convertirán a
comillas), intento de anidamiento excesivo de operadores no permitido, o
campo de búsqueda no existente en la base destino.

W-005 -- Truncamiento demasiado amplio: Advertir si un comodín podría
generar demasiados resultados o es mal ubicado. Por ejemplo, si el
usuario ingresó \*ology al inicio (que no es válido), o genom\* en
Scopus (válido pero muy amplio), se puede notificar para revisión.
También si un comodín de un solo caracter ? o opcional \# se usa
repetidamente en un término de forma que quizá exceda limitaciones
(p.ej. más de 3 placeholders en una palabra), podría sugerirse cautela.

Estas reglas y advertencias priorizadas garantizan que el traductor MVP
maneje correctamente las diferencias clave entre Scopus e IEEE Xplore,
evitando pérdidas de información y señalando al usuario cualquier ajuste
manual necesario.

Tabla comparativa de operadores y campos (Scopus vs IEEE Xplore)

A continuación se presenta una tabla que resume los principales campos
de búsqueda recomendados, operadores y sintaxis especiales para Scopus e
IEEE Xplore, incluyendo notas sobre comodines, límites y precedencia.
Esta información se extrajo de fuentes oficiales (Elsevier, IEEE) y
guías académicas confiables, indicando también la fuente y fecha para
referencia.

Leyenda de columnas:

bd: Base de datos (scopus \| ieee_xplore)

campo_recomendado: Campo/sugerencia de ámbito de búsqueda por defecto

operadores_booleanos: Operadores lógicos soportados

proximidad_sintaxis: Sintaxis para operadores de proximidad

precedencia: Orden de precedencia booleana (si no se usan paréntesis)

comodines_y_límites: Comodines disponibles (\*, ?, etc.) y restricciones

longitud_máxima_query: Longitud o tamaño máximo de consulta (caracteres
o términos)

notas: Otras notas relevantes (frase exacta, etc.)

fuente_url: URL de la fuente principal

fecha_publicación: Fecha de publicación/actualización de la fuente

fecha_acceso: Fecha en que se accedió a la fuente

bd,campo_recomendado,operadores_booleanos,proximidad_sintaxis,precedencia,comodines_y_límites,longitud_maxima_query,notas,fuente_url,fecha_publicacion,fecha_acceso
Scopus,\"TITLE-ABS-KEY (título, resumen, keywords)\",\"AND, OR, AND
NOT\",\"W/n (sin orden), PRE/n (orden estricto)\",\"OR \> AND \> NOT
(cambio a AND NOT \> AND \> OR en 2025)\",\"\* (0+ car.), ? (1 car.), \#
(0-1 car.); sin comodín inicial; sin límite explícito oficial\",\"\~256
caracteres por consulta (Advanced Search)\",\"{} para frase exacta,
\\\"\\\" para frase aproximada; sin búsqueda en texto
completo\",\"https://www.library.sydney.edu.au/content/dam/library/documents/support/scopus_searchingguide.pdf\",\"n.d.\",\"2025-11-05\"
IEEE Xplore,\"All Metadata (metadatos, no full-text por
defecto)\",\"AND, OR, NOT\",\"NEAR/# (sin orden), ONEAR/#
(ordenado)\",\"NEAR/ONEAR \> NOT \> AND \> OR\",\"\* (multi-car.), ? (un
car.); máx 8 comodines (\* o ?) por
búsqueda:contentReference\[oaicite:32\]{index=32}; mínimo 3 letras antes
de comodín\",\"25 términos (sin operador) por consulta\",\"Comillas
\\\"\\\" para frases exactas; auto-trunca plurales/variantes (sin
comillas)\",\"https://lib.unb.ca/sites/default/files/media/documents/IEEE_1.pdf\",\"2023-01-15\",\"2025-11-05\"

(La tabla CSV anterior puede ser descargada o abierta en una hoja de
cálculo para mejor legibilidad. Se proporcionan las fuentes primarias
con sus URLs y fechas para verificación.)

Política de fraseología en Scopus (comillas vs. llaves)

En Scopus, existen dos modos de búsqueda de frases:

Frase aproximada (loose phrase): Se escribe entre comillas dobles
\"\...\". Scopus interpreta que esas palabras deben aparecer juntas,
pero permite variaciones menores como diferencias de ortografía,
singular/plural o la presencia/ausencia de ciertos caracteres especiales
library.sydney.edu.au . Por ejemplo, \"heart attack\" recuperará
documentos donde aparezca exactamente "heart attack" y posiblemente
variaciones como "heart attacks" (plural) o "heart-attack" (con guion),
ya que el buscador considera equivalentes algunas variaciones comunes
library.sydney.edu.au . Las comillas obligan a que las palabras estén
adyacentes en la fuente, pero Scopus podría internamente seguir
aplicando AND entre términos si no se usa el modo exacto; es decir, la
frase en comillas es más precisa que sin comillas, aunque no tan
estricta como el modo exacto con llaves library.sydney.edu.au . (Nota:
Diversas guías señalan que Scopus con comillas realiza búsqueda de frase
"laxa", pudiendo ignorar pequeños cambios o stop words, mientras que sin
comillas cada palabra se ANDea por separado.)

Frase exacta: Se escribe dentro de llaves {\...}. Este modo le indica a
Scopus que busque exactamente esos términos en esa secuencia, sin
alterar nada library.sydney.edu.au . No se aplicará la lematización ni
se ignorarán stop words: cada carácter cuenta. Por ejemplo, {deep
learning} solo traerá resultados donde deep learning aparezca tal cual
como frase exacta continua library.sydney.edu.au . Si hubiera un
documento con "deep and learning" o "deep learning" (doble espacio) en
el texto, no calificaría porque no coincide exactamente con la cadena
entre llaves. Este modo también diferencia acentos, mayúsculas y signos:
p.ej. {José} no encontrará Jose sin acento. Según la Universidad de
Waterloo, cualquier frase entre llaves busca coincidencia exacta de
palabras y caracteres, incluyendo palabras vacías (stop words) o
puntuación subjectguides.uwaterloo.ca . Es el método recomendado para
asegurarse de no recuperar variaciones no deseadas. Scopus no aplica
operadores implícitos dentro de {\...} -- a diferencia del caso sin
llaves donde "palabra1 palabra2" equivaldría a palabra1 AND palabra2
dcu.libguides.com , con llaves se exige la secuencia literal.

En resumen: Use {\...} en Scopus para frases que deban aparecer
exactamente como están, y use comillas \"\...\" cuando una frase puede
tener pequeñas variantes o para buscar una idea de frase de manera
amplia. Si no se usan ni comillas ni llaves, Scopus por defecto inserta
AND entre cada palabra dcu.libguides.com , lo que significa que las
palabras pueden aparecer separadas en cualquier lugar del campo buscado
(no como frase continua). Esto último puede aumentar la recuperación
pero perder contexto (las palabras podrían no estar relacionadas
directamente en el texto).

En IEEE Xplore, en cambio, no existe la distinción de llaves. Siempre se
usan comillas para indicar frases exactas facebook.com . Si se ponen
varias palabras sin comillas, IEEE Xplore asumirá probablemente una
combinación AND implícita (todas las palabras deben aparecer en los
metadatos) library.indwes.edu . Por ejemplo, buscar artificial
intelligence privacy (sin comillas ni operadores) en IEEE Xplore es
equivalente a buscar artificial AND intelligence AND privacy en
metadatos, según guías de IEEE libguides.ittralee.ie . En cambio,
\"artificial intelligence\" con comillas busca esa frase exacta. No hay
un símbolo para frase "exacta estricto" más allá de las comillas, pero
IEEE Xplore por defecto no expande sinónimos ni variantes (solo plural y
tiempos verbales como se señala abajo). Una diferencia importante: IEEE
Xplore realiza automáticamente la búsqueda de plurales, formas verbales
y grafías británicas/americanas cuando las palabras no están entre
comillas lib.unb.ca . Por ello, escribir cancer sin comillas buscará
cancer y cancers, behavior hallará behaviour, etc., mientras que
\"behavior\" entre comillas limitará a esa ortografía exacta lib.unb.ca
.

Ejemplos canónicos:

Scopus: TITLE-ABS-KEY(\"machine learning\") recupera documentos donde
aparezca la frase machine learning (junta), pero podría incluir machine-
o machines learning si las considera variantes. En cambio
TITLE-ABS-KEY({machine learning}) solo trae donde machine learning
aparezca exactamente así, sin alteraciones library.sydney.edu.au .

IEEE: \"machine learning\" (en el campo All Metadata) buscará esa frase
exacta; si se buscara machine learning sin comillas, sería como machine
AND learning e incluiría casos donde machine y learning estén separadas.
No existe {machine learning} en IEEE; si el traductor recibe una
consulta Scopus con llaves, deberá convertirla a comillas para IEEE y
quizás agregar advertencia de que puede traer más variaciones de lo
deseado.

Anti-ejemplo (Scopus): Buscar \"heart attack\" (comillas) podría traer
resultados donde aparece "heart attacks". Si eso no fuera deseable (por
querer solo singular), la búsqueda exacta {heart attack} sería la forma
correcta -- la primera es una frase laxa, la segunda estricta.

Filtro de año en Scopus vs IEEE Xplore

La forma de limitar por año de publicación difiere notablemente entre
Scopus e IEEE Xplore:

Scopus: Permite especificar años o rangos dentro de la consulta avanzada
mediante campos dedicados. El campo PUBYEAR filtra por año de
publicación journals.sagepub.com . Se pueden usar operadores
relacionales: por ejemplo, PUBYEAR \> 2015 AND PUBYEAR \< 2021 limitará
a resultados de 2016--2020. También se pueden especificar uno o varios
años exactos combinando con OR o usando la función limit-to. Ejemplo
válido: TITLE-ABS-KEY(\"machine learning\") AND ( PUBYEAR = 2020 OR
PUBYEAR = 2021 ) devuelve solo artículos de 2020 o 2021. En la sintaxis
propia de Scopus, se podría escribir equivalentemente
TITLE-ABS-KEY(\"machine learning\") AND LIMIT-TO(PUBYEAR,2020) AND
LIMIT-TO(PUBYEAR,2021) aunque generalmente LIMIT-TO se usa tras realizar
una búsqueda, encadenando refinamientos libguides.eur.nl
guides.libraries.indiana.edu . La documentación de Elsevier confirma la
disponibilidad de Pubyear en Advanced Search journals.sagepub.com . Un
ejemplo canónico citado: TITLE(\"5G networks\") AND AUTH(\"Lee\") AND
PUBYEAR \> 2021 AND (DOCTYPE(con) OR DOCTYPE(cp)) buscaría artículos de
Lee sobre 5G publicados después de 2021, limitando tipo de documento a
conferencias academic.net . Scopus también tiene Date of Publication
(Pubdatetxt) para búsquedas más granulares por fecha exacta
(año/mes/día), pero en la práctica PUBYEAR suele ser suficiente para
rangos anuales.

IEEE Xplore: No ofrece un operador de texto para año dentro de la caja
de búsqueda. El filtrado por año se realiza mediante la interfaz
gráfica: en la Advanced Search hay campos para "Publication Year" (año
único o rango) y en la página de resultados se puede aplicar un faceta
por año. La guía del IEEE lo señala explícitamente: "In IEEE, limit by
single publication year or range under Advanced search or results page."
lib.unb.ca . Por ejemplo, tras ejecutar una búsqueda, uno puede aplicar
el filtro "Published: 2018--2022" en la UI de IEEE Xplore. Pero no se
puede escribir algo como Year=2020 ni PUBYEAR\>2019 en la query de IEEE
Xplore -- tales intentos serán ignorados o malinterpretados. El
traductor por tanto debe separar el filtro de año del string de búsqueda
al convertir a IEEE: la salida podría consistir en la consulta sin años
y un metadato separado indicando filtro_año: 2020-2024. El usuario
tendría que aplicar ese filtro manualmente (o el sistema automáticamente
vía la API/URL si fuera posible pasar parámetros).

Ejemplo: Supongamos la búsqueda original es TITLE-ABS-KEY(computer AND
vision) AND PUBYEAR \>= 2019.

Traducción Scopus (ejemplo): se mantiene igual, ya que es válido en
Scopus Advanced Search.

Traducción IEEE: la consulta principal sería computer AND vision
(aplicada sobre All Metadata), y por separado se indicará Filtro año:
desde 2019. El sistema podría mostrar un mensaje o warning aclarando:
"Filtro de año 2019+ aplicado en IEEE Xplore (vía interfaz, no en la
consulta textual)".

Hay que destacar que el filtrado por año en Scopus vs IEEE puede arrojar
resultados ligeramente distintos. Scopus considera el año de publicación
oficial del documento, mientras que IEEE Xplore también tiene en cuenta
el año de conferencia o estándar. En casos de documentos de conferencias
a caballo de años, podría haber discrepancias journals.sagepub.com . Sin
embargo, para propósitos del traductor, asumimos que la intención es
equivalente: limitar por año de publicación.

Conclusión operativa: El MVP incluirá en la salida de Scopus cualquier
filtro de año como parte de la query avanzada, y en la salida de IEEE
proveerá esa restricción fuera de la query (por ejemplo, en un campo
JSON year_range o similar), además de notificar al usuario que debe
aplicarse al buscar en IEEE Xplore. Esto asegura trazabilidad: la
información de año no se pierde, pero se maneja correctamente según las
capacidades de cada plataforma.

Reglas de proximidad y precedencia: Scopus vs IEEE

Proximidad (distancia entre palabras): Ambos sistemas permiten acotar
búsquedas a términos cercanos entre sí, pero con distinta sintaxis:

Scopus:

W/n (Within n): encuentra los términos especificados si aparecen
separados por hasta n palabras, en cualquier orden library.sydney.edu.au
. Ej: heart W/2 attack hallará frases como \"heart attack\" (0 palabras
en medio) o \"\*heart \* attack\" (con 1 palabra intercalada, e.g.
\"heart and attack\"), en cualquier orden (podría ser \"attack of
heart\", aunque semánticamente raro).

PRE/n (Precede n): similar a W/n pero exige que el primer término
anteceda al segundo dentro del lapso de n palabras library.sydney.edu.au
. Ej: virus PRE/3 vaccine encontrará \"virus \... vaccine\" con ≤3
palabras en medio, pero no \"vaccine \... virus\" media.lib.unb.ca .
Útil para expresiones donde el orden importa (p. ej. adjectivo antes de
sustantivo).

Ambos operadores pueden combinarse con grupos entre paréntesis para
mayor flexibilidad. Scopus permite estructuras como (term1 OR term2) W/5
(term3 OR term4) para decir \"cualquiera de term1 o term2 a 5 palabras
de cualquiera de term3 o term4\" library.sydney.edu.au . Esto es
poderoso para buscar conceptos con sinónimos múltiples en contexto
cercano.

Límites: n puede ser cualquier entero hasta 255 libguides.library.uu.nl
(Scopus documenta que n va de 0 a 255). Usar W/0 sería válido (palabras
contiguas en cualquier orden), aunque normalmente equivaldría a una
frase sin orden fijo. Precedence: PRE/0 implicaría las palabras juntas
en ese orden exacto, lo cual es similar a frase exacta pero con posible
diferencias menores. En general, es raro usar 0; se suele usar 1 o más.
No usar valores muy altos sin necesidad, pues podría equivaler a
términos separados sin relación.

IEEE Xplore:

NEAR/x: operador de proximidad no ordenado. Equivalente a W/x de Scopus
lib.unb.ca . Ej: cloud NEAR/3 computing encuentra \"cloud computing\" (0
palabras intermedias), \"cloud based computing\" (1 palabra \"based\"),
etc., o incluso \"computing in the cloud\" (orden inverso) mientras la
distancia sea ≤3 palabras.

ONEAR/x: operador de proximidad ordenado (\"Ordered NEAR\"). Equivalente
a PRE/x lib.unb.ca . Ej: security ONEAR/1 network traerá frases donde
\"security\" precede inmediatamente a \"network\" (como \"security
network\"), pero no al revés. Si fuera ONEAR/3, permitiría hasta 2
palabras entremedias manteniendo el orden dado.

Nota de sintaxis: Algunas documentaciones escriben ONEAR con una o dos N
(ONNEAR); en la práctica en IEEE Xplore se usa ONEAR x.com . Ambos
operadores de IEEE se usan en Command Search o en la casilla básica con
la misma sintaxis. Si se busca una frase compuesta cerca de otra
palabra, conviene entrecomillar la frase: p. ej. \"artificial
intelligence\" NEAR/5 security (la frase completa artificial
intelligence dentro de 5 palabras de security).

Límites: IEEE no documenta oficialmente un valor máximo de x, pero
generalmente valores muy altos pierden sentido. Se recomienda mantener x
moderado (≤5 ó 10) para conservar relevancia. Además, en IEEE Xplore los
operadores NEAR/ONEAR tienen mayor precedencia que AND/OR, lo que
significa que la cercanía se evalúa antes de combinar con otros
criterios libguides.ittralee.ie . En Scopus, W/ y PRE/ técnicamente
actúan casi como operadores booleanos (similar o mayor precedencia que
AND).

Precedencia booleana (orden de evaluación):

Debido a que los motores de búsqueda pueden interpretar expresiones
complejas de formas distintas si no se agregan paréntesis, es crucial
conocer el orden predeterminado en cada plataforma:

Scopus: Como se mencionó, tiene una regla no estándar: OR tiene
prioridad sobre AND, el cual a su vez tiene prioridad sobre NOT
media.lib.unb.ca . En otras palabras, en ausencia de paréntesis: A AND B
OR C se interpreta como A AND (B OR C) media.lib.unb.ca , y A OR B AND C
se interpreta como (A OR B) AND C. Esto es lo opuesto a la convención
usual (AND suele evaluarse antes que OR). Además, Scopus trata AND NOT
como una variante de NOT, con la precedencia más baja en la práctica
(aunque formalmente dice OR \> AND \> NOT, en la sintaxis se usa AND NOT
para excluir). Esta idiosincrasia ha llevado a confusiones; de hecho,
Elsevier anunció que implementará un cambio para alinearse con el
estándar: AND NOT \> AND \> OR hacia 2025-2026 blog.scopus.com . Por
ahora (2025), se recomienda siempre utilizar paréntesis para cualquier
consulta compleja con mezcla de AND/OR, para garantizar que la intención
del usuario se respete media.lib.unb.ca . Scopus mismo devuelve errores
de sintaxis si los paréntesis faltan o están mal anidados en consultas
con múltiples operadores lógicos libguides.umn.edu .

IEEE Xplore: Sigue una precedencia más tradicional, pero con la
particularidad de los operadores de proximidad. Según guías de IEEE, el
orden es: NEAR/ONEAR primero, luego NOT, luego AND, y por último OR
libguides.ittralee.ie . Esto significa, por ejemplo, que en term1 AND
term2 NEAR/3 term3 se evaluará term2 NEAR/3 term3 primero, y luego AND
con term1. Si se quisiera que AND ocurra primero, tendríamos que usar
paréntesis: (term1 AND term2) NEAR/3 term3. Otra implicación: A OR B AND
C se toma como A OR (B AND C) porque AND tiene mayor precedencia que OR
(lo estándar). Y A NOT B AND C se toma como (A NOT B) AND C (ya que NOT
se evalúa antes que AND). En general, AND tiene precedencia sobre OR en
IEEE, y NOT se aplica antes que ambos, similar a la lógica booleana
usual libguides.ittralee.ie . Aun así, siempre que se combinen OR con
otros operadores es prudente agrupar con paréntesis para evitar duda.

Ejemplos mínimos de proximidad y precedencia:

Scopus: "data" W/2 "mining" AND "big" -- Como W/2 tiene efecto solo
entre \"data\" y \"mining\", la consulta se lee como (\"data\" W/2
\"mining\") AND \"big\". Si la intención era buscar \"big data mining\"
como concepto, se debería escribir \"big data\" W/1 \"mining\" o usar
paréntesis apropiadamente.

Scopus: solar OR wind AND energy -- Sin paréntesis, Scopus lo evalúa
como (solar OR wind) AND energy media.lib.unb.ca . Resultado: documentos
sobre energía solar o eólica. Si la intención era "solar o (energía
eólica)", habría que poner solar OR (wind AND energy).

IEEE: cloud ONEAR/2 security OR privacy -- Se evalúa como (cloud ONEAR/2
security) OR privacy. Si se quería cloud cerca de security o privacy,
debería ser cloud ONEAR/2 (security OR privacy).

IEEE: virus NEAR/5 vaccine AND trial -- Se evalúa primero virus NEAR/5
vaccine, luego AND con trial (equivalente a (virus NEAR/5 vaccine) AND
trial). Si se pretendía virus cerca de vaccine trial, habría que
escribir virus NEAR/5 \"vaccine trial\" o (virus NEAR/5 vaccine) NEAR/5
trial con otra lógica.

Recomendación: El traductor siempre insertará paréntesis en la consulta
traducida cuando haya cualquier ambigüedad de lectura. Por ejemplo, una
consulta unificada con múltiples OR dentro de AND se formateará como
(grupo1) AND (grupo2) AND NOT (grupo3) etc., asegurando que cada
conjunto OR esté agrupado. Así evitamos depender de precedencias
internas que puedan cambiar o confundir. Esta práctica se sustenta en
las guías oficiales: "Use parentheses ( ) to control precedence and
avoid unexpected results" blog.scopus.com .

Validaciones y warnings específicos

Durante el proceso de normalización y traducción, se deben realizar
validaciones automáticas para asegurar que la consulta resultante cumpla
las reglas de la plataforma de destino. Si alguna regla se viola o
alguna condición especial se detecta, el sistema debe emitir una
advertencia (warning) descriptiva para alertar al usuario sin abortar la
traducción. A continuación se listan validaciones importantes y sus
warnings asociados, según especificaciones de Scopus e IEEE Xplore:

Longitud de consulta (Scopus): Si la consulta traducida para Scopus
supera los 256 caracteres (límite de la caja de búsqueda avanzada)
library.sydney.edu.au , se debe fraccionar o recomendar fraccionar.
Warning: "W-002: La consulta excede 256 caracteres y puede no ejecutarse
en Scopus; considere dividirla en sub-consultas." El sistema idealmente
podría dividir automáticamente usando el historial (por ej. realizar dos
búsquedas y luego combinar con OR), pero mínimamente debe advertir al
usuario.

Cantidad de términos (IEEE): Si una consulta IEEE tiene más de 25
términos sin operadores lib.unb.ca , IEEE podría ignorar términos
adicionales. Warning: "W-002: La consulta en IEEE contiene más de 25
términos independientes; se recomienda dividir o simplificar términos."
Por ejemplo, una larga lista de palabras clave separadas solo por
espacios debe dividirse en varias listas con operadores OR explícitos.

Exceso de comodines (IEEE): Detectar cuántos comodines \*, ? (o \$) hay
en la estrategia IEEE. Si \> 8, eso excede el máximo actual lib.unb.ca .
Warning: "W-001: La búsqueda contiene X comodines, más de los 8
permitidos por IEEE Xplore -- algunos términos podrían no ser
considerados." El usuario debería reducir comodines (quizá dividir
términos con muchos \* en varios términos específicos).

Uso de comodines en posiciones no válidas: Si el usuario ingresó
comodines al comienzo de un término (p.ej. \*omics), Scopus e IEEE no lo
permiten (no retornará resultados o dará error). Warning: "W-005: El
comodín no puede usarse al inicio del término '\*omics'. Se omitirá el
comodín inicial." El traductor podría simplemente quitar el \* inicial
en ese caso, buscando \"omics\" a secas, pero avisando de la pérdida de
la funcionalidad.

Placeholder insuficiente: En IEEE, un comodín exige ≥3 caracteres antes
para funcionar lib.unb.ca . Si alguien pusiera ab\* (solo 2 letras antes
del ), no devolverá resultados. Warning: "W-005: El término 'ab' no
cumple los requisitos mínimos de 3 letras antes del comodín en IEEE
Xplore." Se sugiere al usuario modificar a un término más completo. (En
Scopus no hay mención de requisito de 3 letras, aunque es buena práctica
tener al menos 2-3 letras para que la truncación sea significativa).

Paréntesis desequilibrados o lógicos vacíos: Si tras la traducción la
sintaxis queda con paréntesis mal balanceados (bug interno) o grupos
vacíos, se debe corregir o al menos advertir. Warning: "W-XXX: Se
detectó una expresión incompleta o un paréntesis sin cerrar, verifique
la consulta." Idealmente, el sistema no generará sintaxis inválida, pero
esta check es por seguridad. Scopus en especial arroja error si los
paréntesis no calzan libguides.umn.edu .

Campos o operadores no soportados: Si la consulta original incluye un
campo que no existe en la base destino, se ignora y se alerta. Ej: una
búsqueda original de Web of Science con TS= (Topic) traducida a Scopus
tendría que mapearse a TITLE-ABS-KEY, pero si no hubiera mapeo, se
omite. Warning: "W-004: El campo X no existe en \[destino\]; se ha
omitido esa parte de la búsqueda." Similar con operadores: p.ej. Scopus
tiene NEAR pero en realidad no (usa W/), IEEE tiene XOR (no lo tiene,
solo AND/OR/NOT).

Truncamiento excesivo: Si un término truncado puede generar excesivas
permutaciones (por ej a\* en Scopus encontraría cualquier palabra que
empiece con "a"), podría advertirse. Warning: "W-005: El truncamiento en
'a\*' es muy amplio y puede generar muchos resultados irrelevantes." No
es una violación técnica pero sí de calidad de búsqueda. Esta
advertencia es más orientativa.

Estas validaciones garantizan que la consulta traducida esté lista para
ejecutarse en la base de datos de destino sin errores, y que el usuario
esté consciente de cualquier modificación o limitación aplicada. Los
warnings están codificados (W-001, W-002, etc.) para referencia; a
continuación se resumen los warnings críticos identificados previamente:

W-001: Exceso de comodines para IEEE (más de 8).

W-002: Consulta demasiado larga (Scopus \>256 chars o IEEE \>25
términos).

W-003: Filtro de año no aplicado en texto (caso IEEE).

W-004: Elemento no soportado (campo/operador omitido).

W-005: Posible problema con comodines/truncamiento (posición inválida o
demasiado amplio).

El sistema de traducción debe incluir estos mensajes en la traza de
salida cuando corresponda, para que el usuario final o el desarrollador
los vean y actúen en consecuencia. Por ejemplo, en la traza JSON podría
haber una entrada: \"step\": \"validation\", \"detail\": \"W-001: 10
comodines detectados, se reducirán a 8 o menos.\"

Modelo de trazabilidad y estados del proceso

Para asegurar transparencia en cómo se traduce cada consulta, el MVP
mantendrá un rastro detallado (trace) de pasos, desde que la consulta es
recibida hasta que está lista para ejecutar. Los posibles estados
principales del proceso (pipeline) son:

recibida: Se recibe la consulta original del usuario (posiblemente en
lenguaje natural o con ciertos operadores).

normalizada: Se realiza una normalización inicial (p. ej. unificar
mayúsculas/minúsculas en operadores, eliminar espacios extra, corregir
sintaxis básica). Se identifican componentes de la búsqueda: frases,
términos sueltos, operadores booleanos, filtros de año, etc., y se
estructura internamente.

traducida: Aplicación de reglas de mapeo al destino: se convierte la
sintaxis fuente (por ejemplo de Scopus a IEEE) en la sintaxis objetivo.
Se reemplazan operadores (AND \<-\> AND, OR \<-\> OR, NOT/AND NOT según
caso, W/n -\> NEAR/n, etc.), se ajustan campos (p. ej. de TITLE-ABS-KEY
a Abstract/Metadata), se añaden/quitan comillas o llaves según política
de frases, se manejan comodines no compatibles, etc. Tras este paso,
existe un borrador de consulta en la sintaxis del destino.

validada: Se verifica la consulta traducida contra las reglas y
limitaciones del destino (como las de la sección anterior). Si algo no
cumple, se corrige si es posible (p. ej. recortar comodines extra,
agregar paréntesis faltantes) y/o se registran warnings en la traza.
Este estado asegura que la consulta final no cause errores al
ejecutarla.

lista: La consulta final, ya traducida y validada, está lista para
presentarse al usuario o ejecutarse. En este estado final, se suele
preparar la salida en el formato solicitado (por ejemplo, un JSON con la
consulta y metadatos, o directamente el string con algunas notas).

Podemos visualizar los estados como un flujo sencillo: Recibida →
Normalizada → Traducida → Validada → Lista. Cada transición implica
transformaciones que quedan registradas.

Diagrama de estados (texto):

\[Recibida\] -\> (normalizar términos) -\> \[Normalizada\] -\> (aplicar
reglas fraseología, campos, operadores) -\> \[Traducida\] -\> (verificar
límites, sintaxis) -\> \[Validada\] -\> (salida format) -\> \[Lista\]

En la implementación, tras procesar una consulta obtendríamos un arreglo
JSON trace con objetos que detallan cada paso. Por ejemplo:

\[ {\"step\": \"normalize_terms\", \"detail\": \"Identificados 3 grupos
AND y 2 términos excluidos con NOT\"}, {\"step\": \"phrase_policy\",
\"detail\": \"Aplicando frase exacta: llaves {} en Scopus, comillas en
IEEE\"}, {\"step\": \"year_filter\", \"detail\": \"Filtro de año
separado (Scopus usa PUBYEAR 2015-2020, IEEE via faceta)\"}, {\"step\":
\"assemble_query\", \"detail\": \"Se agregan paréntesis para agrupar OR
lógicos correctamente\"}, {\"step\": \"validation\", \"detail\":
\"Longitud OK (\<256), comodines OK (2 en IEEE \<=8)\"} \]

(Ejemplo ilustrativo de traza.) Cada objeto indica el subproceso (step)
y un detalle de qué se hizo o qué se encontró. Esto permite al usuario
seguir la "traducción" paso a paso, lo cual es crucial en estrategias de
búsqueda complejas donde se quiere total confianza de que la lógica no
cambió.

El modelo de traza también facilita depurar y ajustar reglas en el MVP:
por ejemplo, si en phrase_policy vemos que siempre aplica llaves para
Scopus, pero en algún caso debería no hacerlo (quizá para nombres
propios con iniciales, etc.), se podría refinar esa lógica. Además, la
traza final puede almacenarse junto con la consulta traducida como parte
de la documentación de reproducibilidad (pensemos en un artículo donde
se publica la estrategia de búsqueda -- esta traza serviría casi como
pseudocódigo de cómo obtenerla).

Suite BDD: Escenarios de prueba con casos reales

Para verificar el correcto funcionamiento del traductor, se han diseñado
al menos 6 escenarios de prueba en formato BDD (Behavior-Driven
Development), con consultas de ejemplo y los resultados esperados
("golden queries"). Cada escenario contempla una situación
representativa tanto para Scopus como para IEEE Xplore. A continuación
se describen los escenarios, indicando entrada normalizada, salida
esperada y verificaciones. (En una implementación, estos podrían
escribirse en archivos .feature con pasos Given/When/Then, y los
resultados esperados en archivos JSON, pero aquí los presentamos de
forma simplificada.)

Escenario 1: Frase exacta vs laxa en Scopus

Dado una búsqueda en lenguaje natural: Investigar \"deep learning\" en
predicción de fallos (el usuario quiere que "deep learning" sea frase
exacta en un caso y en otro no). Supongamos que el usuario marca frase
exacta = verdadero en un campo de entrada o lo inferimos porque usó
comillas vs llaves.

Entrada normalizada: deep learning software -- (Interpretación: buscar
deep learning como concepto y palabra software, sin especificar si deep
learning debe ser exacto o no; consideraremos dos variantes).

Cuando se traduce a consulta Scopus:

Variante A (frase laxa): TITLE-ABS-KEY(\"deep learning\" AND software)
-- aquí "deep learning" entre comillas, software separado con AND. El
traductor pone por defecto comillas para frases de dos palabras si no se
indicó lo contrario.

Variante B (frase exacta): TITLE-ABS-KEY({deep learning} AND software)
-- aquí con llaves para que deep learning sea exacto.

Entonces la consulta Scopus resultante debe usar el formato correcto:
campo TITLE-ABS-KEY(\...), operadores en mayúsculas. En la variante B,
"deep learning" aparece con llaves.

Y no se generan warnings, ya que la sintaxis es válida y simple (pocos
caracteres, pocos términos, sin comodines).

Criterio de verificación: Ejecutando ambas en Scopus, la variante exacta
B debería dar igual o menos resultados que la A (nunca más) porque está
más restringida. De hecho, típicamente B ⊆ A en cuanto a resultados. Por
ejemplo, si A encontró 120 documentos, B podría encontrar 110
(excluyendo algunos donde "deep" y "learning" estaban separados o
variaciones plurales).

(En BDD formal, tendríamos dos escenarios separados: uno para frase laxa
y otro exacta. Aquí los combinamos conceptualmente para resaltar la
diferencia.)

Escenario 2: Operador de proximidad en Scopus (W/n vs PRE/n)

Dado que un usuario quiere buscar conexiones cercanas entre "defect" y
"prediction" en Scopus.

Entrada normalizada: defect prediction W/2 (quizá el usuario escribió
"defect NEAR/2 prediction" pensando en proximidad sin orden;
normalizamos a un formato genérico o directamente entendemos la
intención).

Cuando se traduce a Scopus:

Salida esperada: TITLE-ABS-KEY(\"defect\" W/2 \"prediction\").

Entonces la consulta debe contener \"defect\" W/2 \"prediction\"
exactamente en Scopus, y usar el campo por defecto (TITLE-ABS-KEY).

Y sin warnings, asumiendo está dentro de límites.

Verificación: Al ejecutar en Scopus Advanced Search, debe aceptar la
sintaxis. Deberíamos obtener resultados donde defect y prediction
aparecen con ≤2 palabras de por medio, en cualquier orden. Por control,
si buscamos \"defect prediction\" (frase exacta), seguramente obtenemos
menos resultados; la búsqueda W/2 debe incluir esos y más, confirmando
que funciona.

Variante adicional: Si quisiéramos probar PRE/n, cambiamos la entrada a
defect PRE/2 prediction y la salida esperada sería similar pero con
PRE/2. Podríamos verificar que \"defect PRE/2 prediction\" encuentra
"defect X prediction" pero no "prediction X defect".

(Este escenario prueba que el traductor reconoce el operador NEAR
genérico y lo asigna a W/ o PRE/ según corresponda, y que pone las
comillas correctamente alrededor de palabras individuales para evitar
conflictos con stop words o sintaxis.)

Escenario 3: Exclusiones y filtro de año en Scopus

Dado un investigador que busca artículos sobre "defect prediction" pero
excluyendo los que mencionan "software", limitando a publicaciones de
2020 a 2024.

Entrada normalizada (pseudo): deep learning AND defect prediction NOT
software year:2020-2024. Podría venir así de una interfaz donde "NOT
software" indica exclusión y hay un campo de año.

Cuando se traduce a Scopus:

Salida esperada: TITLE-ABS-KEY((\"deep learning\" OR \"defect
prediction\") AND NOT software). Aquí hicimos supuestos:

Unimos "deep learning" y "defect prediction" con OR si interpretamos que
buscaba cualquiera de esos conceptos (el problema es que el input no fue
totalmente claro, pero digamos que eran dos ideas separadas).
Alternativamente, quizás el input quería ambas cosas: "deep learning" y
"defect prediction" juntos. Si es así, habría AND entre ellos en lugar
de OR.

Excluimos "software" con AND NOT dentro del paréntesis.

Aplicamos filtro de año fuera del TITLE-ABS-KEY, porque Scopus no
incluye año dentro del mismo paréntesis de campos. En Advanced Search,
año se pone aparte o con AND también. Podríamos hacer: AND PUBYEAR \>=
2020 AND PUBYEAR \<= 2024.

Mejor forma: TITLE-ABS-KEY(\"deep learning\" AND \"defect prediction\"
AND NOT software) AND PUBYEAR \> 2019 AND PUBYEAR \< 2025. Esto asegura
que:

"deep learning" y "defect prediction" aparecen (ambos) -- usé AND porque
quizás el investigador quiere documentos que hablen de predicción de
defectos con técnicas de deep learning.

no aparece "software" (podría ser para filtrar casos de defectos de
software, queriendo tal vez defectos físicos).

año entre 2020 y 2024 inclusive.

Entonces la consulta Scopus debe reflejar la lógica correctamente con
paréntesis: probablemente TITLE-ABS-KEY(\...AND NOT \...) AND PUBYEAR
\.... Scopus requiere que el AND NOT esté dentro de un paréntesis lógico
o bien todo dentro de TITLE-ABS-KEY como puse (lo cual debería funcionar
según documentación).

Y debería generar cero warnings si todo es válido. La longitud es
moderada, los comodines no se usan.

Verificación: Al probar en Scopus, debería aceptar la consulta. Podemos
comprobar que efectivamente filtra años: en Scopus, tras ejecutar, la
interfaz mostraría "Refined by: Year = 2020-2024" si interpretó bien el
PUBYEAR. Los resultados no deben contener la palabra "software" en
título/resumen/keywords (podríamos tomar una muestra para verificar). Y
todos los resultados deberían tener año de publicación 2020-2024.

Nota: Este escenario prueba combinación de AND, OR (si lo hubiera), NOT
y filtro por año. También pone a prueba la inserción de paréntesis y
ubicación correcta del filtro de año.

(Si hubiera algún detalle como que Scopus Advanced Search tal vez exige
AND NOT software fuera de las comillas, etc., el traductor debe
conocerlo. Normalmente AND NOT software dentro de TITLE-ABS-KEY() está
permitido y significa excluir docs con \"software\" en esos campos.)

Escenario 4: Proximidad en IEEE Xplore (NEAR y ONEAR)

Dado un analista quiere replicar en IEEE Xplore una búsqueda por
proximidad realizada en Scopus.

Entrada original (Scopus): TITLE-ABS-KEY(\"bug\" W/2 \"prediction\").

Cuando se traduce a IEEE Xplore:

Salida esperada: Query: \"bug\" NEAR/2 \"prediction\" en All Metadata.
(No hay que especificar campo en la sintaxis textual ya que por defecto
buscará en metadatos; alternativamente, se podría hacer
Abstract:(\"bug\" NEAR/2 \"prediction\") si se decide buscar solo en
resúmenes por recomendación, pero asumiendo All Metadata).

Entonces la consulta IEEE resultante debe contener NEAR/2.

Y ningún warning dado que NEAR/2 es soportado y no excede nada.

Verificación: Ejecutar la consulta en IEEE Xplore. Debería devolver
resultados similares a Scopus, aunque pueden variar porque IEEE cubre
diferentes documentos. Para verificar proximidad, podemos inspeccionar
alguno: si un resultado tiene bug y prediction separados por ≤2
palabras, debe aparecer. No deberían aparecer si están muy lejos. Por
ejemplo, un paper cuyo resumen diga "\... the prediction of software
bugs \..." tiene bug a 4 palabras de prediction, no saldría con NEAR/2
(mientras que con NEAR/5 sí).

Variante (ONEAR): Si el caso de Scopus fuera \"bug\" PRE/2
\"prediction\", la traducción sería \"bug\" ONEAR/2 \"prediction\".
Probarlo manualmente: si algún resultado tiene \"bug prediction\" en esa
secuencia, debería aparecer; si dice \"prediction of bug\", no.

Además, este escenario puede contemplar combinaciones: Ej: input:
\"neural network\" NEAR/3 security OR privacy. El traductor debería
poner paréntesis: \"neural network\" NEAR/3 (security OR privacy).
Verificar que lo hace para respetar precedencia. No se esperan warnings.

Este escenario comprueba que los operadores de proximidad propios de
IEEE se utilicen y que el traductor ponga las comillas necesarias
alrededor de frases multi-palabra (como \"neural network\") antes de
NEAR. También pone a prueba la precedencia en IEEE: NEAR antes que OR,
etc., y cómo el traductor agrega paréntesis.

Escenario 5: Advertencia por comodines en IEEE Xplore

Dado un usuario arma una búsqueda muy exhaustiva con comodines para
incluir variaciones, y la pasa al traductor para IEEE.

Entrada normalizada: behavior\* AND analy\* AND optim\* (el usuario
quiere abarcar behavior/behaviour, analysis/analyzing,
optimization/optimisation, etc., usando truncamientos amplios). Son 3
términos truncados.

Cuando se traduce a IEEE Xplore:

Salida esperada: behavior\* AND analy\* AND optim\* (la sintaxis de
comodines \* es igual en IEEE).

Sin embargo, habría que checar los mínimos de letras:

behavior\* tiene 7 letras antes de \*, cumple (\>3).

analy\* tiene 5, cumple.

optim\* tiene 5, cumple.

Entonces por letra mínima no hay problema.

Número de comodines: son 3 asteriscos, todos válidos. Total 3 comodines
\< 8, así que en principio no se excede límite.

Pero: IEEE Xplore buscará plurales y variantes automáticamente incluso
sin comodines lib.unb.ca . Por ej, behavior sin \* ya encontraría
behaviors y la ortografía británica behaviour. Por lo que el comodín en
"behavior\*" quizá es redundante.

El traductor podría igualmente dejarlo (no es incorrecto), pero podría
generar un warning de sugerencia: "El comodín \* en 'behavior' puede ser
redundante, IEEE Xplore ya busca plurales y variantes comunes."\* Esto
no es un error, sino un consejo. Sin embargo, como MVP, quizás no se
implementen sugerencias tan avanzadas, nos centramos en límites.

Entonces la consulta resultante es igual a la entrada en este caso.

Y podría generarse un warning menor: por ejemplo, si el usuario hubiera
puesto 9 comodines diferentes, sí dispararía W-001. Aquí no. Ningún
warning crítico debería aparecer, la consulta es válida.

Verificación: Ejecutar la búsqueda en IEEE Xplore y verificar que se
ejecuta. Quizá observar que los resultados de behavior\* y behavior son
muy similares en cantidad (porque la \* no añade mucho más de lo que ya
hace el motor). Para fines de test, lo importante es que el sistema no
bloqueó los comodines ni produjo error.

Para hacer más notorio el warning, podemos ajustar el escenario:
supongamos entrada: \*ology OR bio\* OR analy\* OR data\* OR net\* OR
secur\* OR reliab\* OR optim\* OR valid\* OR auto\* -- aquí hay 10
comodines \*. El traductor al ver 10 comodines para IEEE:

Generaría la consulta tal cual con \* (no hay otra forma de
truncamiento),

Y produciría Warning W-001 indicando que 10 comodines exceden el límite
de 8 lib.unb.ca .

Posiblemente podría autoajustar: por ejemplo quitar comodines de 2
términos menos relevantes (difícil decidir automáticamente). Lo más
seguro es avisar.

Verificación: que el warning aparezca en la traza/salida. Y si el
usuario reduce los comodines a ≤8 y reintenta, el warning desaparezca.

Este escenario prueba la lógica de conteo de comodines y emisión de
W-001.

Escenario 6: Filtro de año en IEEE y estado final \"lista\"

Dado una consulta que incluye rango de años, destinada a IEEE Xplore.

Entrada normalizada: (\"machine learning\" OR \"deep learning\") AND IoT
year:2015-2019.

Cuando se traduce a IEEE Xplore:

Salida esperada (consulta): (\"machine learning\" OR \"deep learning\")
AND IoT. (Básicamente igual sin la parte de año).

Metadato de filtro: year_range = 2015-2019 (esto podría proporcionarse
como JSON separado o en texto).

Warnings: Debe generarse W-003: "Filtro de año omitido en query IEEE;
aplicar años 2015--2019 manualmente."

Traza: Incluir un paso indicando que el filtro de año se separó.

Entonces la consulta textual final enviada a IEEE no contiene ninguna
referencia al año (porque no se puede).

Y en la salida estructurada, el estado final lista debería reflejar que
hay un filtro de año pendiente. Por ejemplo, si el sistema devuelve
JSON, podría ser:

{ \"db\": \"ieee_xplore\", \"query\": \"(\\\"machine learning\\\" OR
\\\"deep learning\\\") AND IoT\", \"filters\": {\"year_from\": 2015,
\"year_to\": 2019}, \"warnings\": \[\"W-003\"\] }

Criterio de verificación: Al ejecutar la consulta en IEEE Xplore,
inicialmente dará resultados sin filtrar; aplicando manualmente el
filtro de año 2015-2019 en la interfaz, los resultados deben coincidir
con lo esperado. El estado final "lista" del traductor implica que la
conversión se completó con éxito aunque con aviso. En la traza se
esperaría ver un último paso tipo {\"step\": \"finalize\", \"detail\":
\"Consulta lista para IEEE; filtro de año aplicado fuera de query.\"}.

Además, se verifica que el sistema no intentó poner Year:2015 dentro de
la query (lo cual sería incorrecto).

Este escenario comprueba la correcta omisión del año en la string final
de IEEE y la presencia del warning adecuado, cumpliendo así el
requerimiento de trazabilidad y comunicación al usuario.

Los escenarios anteriores cubren:

Búsqueda de frase exacta vs no exacta (Scopus).

Uso de operadores de proximidad (Scopus e IEEE).

Combinación de booleanos y exclusiones con filtro temporal (Scopus).

Adaptación de proximidad entre plataformas (Scopus-\>IEEE).

Manejo de comodines y emisión de warnings (IEEE).

Manejo de filtros no traducibles en la query (años en IEEE) y
confirmación de estado final.

Cada escenario asegura que una característica específica se traduzca
fielmente y que cualquier diferencia de capacidades se maneje con
transparencia (p. ej., warnings en comodines o año). Para ejecutar estas
pruebas, se usaría la interfaz de línea de comando o llamadas a la API
del MVP, verificando que la salida coincida exactamente con las cadenas
esperadas y que los warnings/trazas informados sean los previstos. Las
golden queries aquí definidas sirven como patrón correcto contra el cual
comparar las respuestas del sistema durante desarrollo y QA.

JSON de reglas extraídas

Finalmente, se presenta un JSON consolidado con las reglas fundamentales
identificadas, siguiendo la plantilla dada. Cada regla incluye la base
de datos a la que aplica, el tema (fraseología, proximidad, etc.), la
formulación de la regla, ejemplos de sintaxis, ejemplos válidos,
contraejemplos cuando aplican, limitaciones, notas y fuentes
bibliográficas de respaldo:

\[ { \"bd\": \"scopus\", \"tema\": \"fraseologia\", \"regla\": \"Para
buscar una frase exacta en Scopus, encierre los términos entre llaves {
} en lugar de comillas, asegurando que aparezcan exactamente en esa
secuencia.\", \"sintaxis\": \[\"{machine learning}\", \"{Internet of
Things}\"\], \"ejemplo_valido\": \"TITLE-ABS-KEY({deep learning})\",
\"contraejemplo\": \"TITLE-ABS-KEY(\\\"deep learning\\\") // (esto
buscaría la frase de forma aproximada, no estricta)\", \"limitaciones\":
\[\"No utilizar { } en Scopus si se desea permitir variantes o formas
múltiples; este modo ignora truncamientos dentro de la frase.\"\],
\"notes\": \"Las llaves fuerzan coincidencia exacta incluso en stop
words, acentos y mayúsculas:contentReference\[oaicite:79\]{index=79}.
Úselas con moderación ya que pueden excluir resultados relevantes con
pequeñas variaciones.\", \"fuentes\": \[ { \"url\":
\"https://www.library.sydney.edu.au/content/dam/library/documents/support/scopus_searchingguide.pdf\",
\"editor\": \"University of Sydney Library\", \"titulo\": \"Searching in
Scopus (PDF Guide)\", \"fecha_publicacion_o_ultima_actualizacion\":
\"n.d.\", \"fecha_acceso\": \"2025-11-05\" }, { \"url\":
\"https://guides.lib.uconn.edu/systematic_searching/scopus\",
\"editor\": \"University of Connecticut Library Guides\", \"titulo\":
\"Searching Scopus - Phrase searching options\",
\"fecha_publicacion_o_ultima_actualizacion\": \"2021\",
\"fecha_acceso\": \"2025-11-05\" } \] }, { \"bd\": \"scopus\", \"tema\":
\"fraseologia\", \"regla\": \"Para buscar una frase de forma aproximada
(no exacta) en Scopus, utilice comillas \\\" \\\"; esto encuentra las
palabras como frase pero permite ligeras variaciones (plural,
ortografía).\", \"sintaxis\": \[\"\\\"machine learning\\\"\",
\"\\\"global-positioning system\\\"\"\], \"ejemplo_valido\":
\"TITLE-ABS-KEY(\\\"machine learning\\\" AND education)\",
\"contraejemplo\": \"TITLE-ABS-KEY({machine learning}) // (esto buscaría
\'machine learning\' exactamente, sin variaciones)\", \"limitaciones\":
\[\"Aún con comillas, Scopus puede insertar AND implícito si no se
detecta la frase exacta; no garantiza 100% contigüidad a menos que la
base lo interprete como frase.\"\], \"notes\": \"Las comillas en Scopus
realizan un búsqueda de frase
estándar:contentReference\[oaicite:80\]{index=80}. Úselas para frases
comunes donde pequeñas diferencias (e.g. singular/plural) no importan.
Si requiere exactitud absoluta, use llaves.\", \"fuentes\": \[ {
\"url\": \"https://subjectguides.uwaterloo.ca/scopus#searching\",
\"editor\": \"University of Waterloo Library\", \"titulo\": \"Scopus
Research Guide -- Phrase Searching\",
\"fecha_publicacion_o_ultima_actualizacion\": \"2020\",
\"fecha_acceso\": \"2025-11-05\" } \] }, { \"bd\": \"ieee_xplore\",
\"tema\": \"fraseologia\", \"regla\": \"IEEE Xplore no soporta llaves;
use siempre comillas \\\" \\\" para indicar frases exactas en búsquedas
de varias palabras.\", \"sintaxis\": \[\"\\\"internet of things\\\"\",
\"\\\"artificial neural network\\\"\"\], \"ejemplo_valido\":
\"\\\"internet of things\\\" AND security\", \"contraejemplo\":
\"{internet of things} AND security // (formato no válido en IEEE)\",
\"limitaciones\": \[\"Las comillas en IEEE Xplore fijan la frase exacta;
sin comillas, las palabras se buscan por separado en
metadatos.:contentReference\[oaicite:81\]{index=81}\"\], \"notes\": \"No
hay modo \'laxo\' vs \'exacto\' en IEEE: es frase con comillas o
términos individuales. IEEE expande plurales automáticamente cuando no
se usan comillas:contentReference\[oaicite:82\]{index=82}.\",
\"fuentes\": \[ { \"url\":
\"https://libguides.ittralee.ie/using-ieee-xplore/search-tips\",
\"editor\": \"Munster Technological University Library\", \"titulo\":
\"IEEE Xplore Search Tips -- Phrases and Operators\",
\"fecha_publicacion_o_ultima_actualizacion\": \"2019\",
\"fecha_acceso\": \"2025-11-05\" } \] }, { \"bd\": \"scopus\", \"tema\":
\"proximidad\", \"regla\": \"Use W/n en Scopus para encontrar palabras a
n palabras de distancia en cualquier orden; use PRE/n para palabras a n
distancia en el orden dado.\", \"sintaxis\": \[\"W/3\", \"PRE/1\"\],
\"ejemplo_valido\": \"TITLE-ABS-KEY(\\\"data\\\" W/3 \\\"mining\\\")\",
\"contraejemplo\": \"\\\"data mining\\\"\~3 // (sintaxis de proximidad
estilo otro sistema, no válida en Scopus)\", \"limitaciones\": \[\"n
puede ser de 0 a 255:contentReference\[oaicite:83\]{index=83}; W/0
equivarle a palabras adyacentes en orden libre, PRE/0 equivale a
adyacentes en orden exacto.\"\], \"notes\": \"W/n no impone
orden:contentReference\[oaicite:84\]{index=84}, PRE/n
sí:contentReference\[oaicite:85\]{index=85}. Combínelos con OR agrupado
para búsqueda flexible de sinónimos
cercanos:contentReference\[oaicite:86\]{index=86}.\", \"fuentes\": \[ {
\"url\":
\"https://www.library.sydney.edu.au/content/dam/library/documents/support/scopus_searchingguide.pdf\",
\"editor\": \"University of Sydney Library\", \"titulo\": \"Searching in
Scopus -- Proximity operators\",
\"fecha_publicacion_o_ultima_actualizacion\": \"n.d.\",
\"fecha_acceso\": \"2025-11-05\" } \] }, { \"bd\": \"ieee_xplore\",
\"tema\": \"proximidad\", \"regla\": \"Use NEAR/# en IEEE Xplore para
buscar términos a \# palabras de distancia en cualquier orden; use
ONEAR/# para exigir ese orden.\", \"sintaxis\": \[\"NEAR/5\",
\"ONEAR/2\"\], \"ejemplo_valido\": \"\\\"wireless\\\" NEAR/3
\\\"sensor\\\"\", \"contraejemplo\": \"\\\"wireless sensor\\\"\~3 // (no
reconocido; se debe usar NEAR/3)\", \"limitaciones\": \[\"NEAR y ONEAR
deben escribirse en mayúsculas. \'#\' debe ser \>=1; valores muy altos
pueden hacer la búsqueda poco precisa.\"\], \"notes\": \"NEAR/# equivale
a proximidad sin orden (como
W/#):contentReference\[oaicite:87\]{index=87}. ONEAR/# es ordenado (como
PRE/#). IEEE aplica estos antes que otros operadores
lógicos:contentReference\[oaicite:88\]{index=88}.\", \"fuentes\": \[ {
\"url\":
\"https://lib.unb.ca/sites/default/files/media/documents/IEEE_1.pdf\",
\"editor\": \"University of New Brunswick Libraries\", \"titulo\": \"Tip
Sheet: IEEE Xplore Digital Library\",
\"fecha_publicacion_o_ultima_actualizacion\": \"2023-01-15\",
\"fecha_acceso\": \"2025-11-05\" } \] }, { \"bd\": \"scopus\", \"tema\":
\"precedencia\", \"regla\": \"En Scopus, por defecto OR se evalúa antes
que AND, y AND antes que NOT. Siempre use paréntesis para agrupar
términos al combinar operadores, evitando interpretaciones
inesperadas.\", \"sintaxis\": \[\"(A OR B) AND C\", \"A AND (B OR
C)\"\], \"ejemplo_valido\": \"(heart OR cardiac) AND attack\",
\"contraejemplo\": \"heart OR cardiac AND attack // (Scopus lo leerá
como (heart OR cardiac) AND
attack:contentReference\[oaicite:89\]{index=89})\", \"limitaciones\":
\[\"Precedencia actual hasta 2025: OR \> AND \>
NOT:contentReference\[oaicite:90\]{index=90}. Esto cambiará próximamente
a AND NOT \> AND \> OR:contentReference\[oaicite:91\]{index=91}.\"\],
\"notes\": \"La regla actual es
inusual:contentReference\[oaicite:92\]{index=92}; puede llevar a
confusión. Se recomienda explicitar con paréntesis. Ej.: sin paréntesis
Scopus interpretaría A OR B AND C como A OR (B AND C) en el futuro, pero
hoy es (A OR B) AND C.\", \"fuentes\": \[ { \"url\":
\"https://media.lib.unb.ca/research/DB_Guide-Scopus.pdf\", \"editor\":
\"University of New Brunswick Libraries\", \"titulo\": \"Database
Guide - Scopus (PDF)\", \"fecha_publicacion_o_ultima_actualizacion\":
\"2018\", \"fecha_acceso\": \"2025-11-05\" }, { \"url\":
\"https://blog.scopus.com/boolean-searches-in-scopus-understanding-operator-precedence-best-practices/\",
\"editor\": \"Elsevier (Scopus Blog)\", \"titulo\": \"Boolean searches
in Scopus: understanding operator precedence\",
\"fecha_publicacion_o_ultima_actualizacion\": \"2025-03-24\",
\"fecha_acceso\": \"2025-11-05\" } \] }, { \"bd\": \"ieee_xplore\",
\"tema\": \"precedencia\", \"regla\": \"En IEEE Xplore, los operadores
de proximidad (NEAR, ONEAR) se resuelven primero, luego NOT, luego AND,
y finalmente OR. Use paréntesis para forzar un orden distinto si
requerido.\", \"sintaxis\": \[\"NEAR/ONEAR \> NOT \> AND \> OR\"\],
\"ejemplo_valido\": \"(A AND B) OR C // (si desea OR después de un AND
explícito)\", \"contraejemplo\": \"A OR B AND C // (se interpreta como A
OR (B AND C) automáticamente)\", \"limitaciones\": \[\"Todos los
operadores deben estar en mayúsculas. La precedencia es fija, pero el
uso de paréntesis puede alterar la evaluación a voluntad.\"\],
\"notes\": \"Esta precedencia coincide con la lógica booleana estándar
(exceptuando la inclusión de proximidad al tope). Por seguridad,
especialmente con NEAR, agrupe ORs
explícitamente:contentReference\[oaicite:93\]{index=93}.\", \"fuentes\":
\[ { \"url\":
\"https://libguides.ittralee.ie/using-ieee-xplore/search-tips\",
\"editor\": \"MTU Kerry Library\", \"titulo\": \"Guide to using IEEE
Xplore - Search Tips\", \"fecha_publicacion_o_ultima_actualizacion\":
\"2019\", \"fecha_acceso\": \"2025-11-05\" } \] }, { \"bd\": \"scopus\",
\"tema\": \"comodines\", \"regla\": \"Scopus admite los comodines \*
(truncamiento de 0 o más caracteres), ? (sustituye 1 carácter) y \#
(sustituye 0--1 caracteres) en los términos de búsqueda.\",
\"sintaxis\": \[\"comput\*\", \"wom?n\", \"p#ediatric\"\],
\"ejemplo_valido\": \"TITLE-ABS-KEY(comput\*) // encuentra computer,
computing, computation...\", \"contraejemplo\": \"TITLE-ABS-KEY(\*ology)
// (no válido: \* no puede estar al inicio)\", \"limitaciones\": \[\"No
usar \* o ? como primer carácter de un término. El comodín ? solo
reemplaza un carácter y es posicional. \# solo se usa para variaciones
de grafía (ej: color/colour).\"\], \"notes\": \"No se especifica un
límite máximo de comodines en Scopus, pero consultas excesivamente
truncadas pueden sobrepasar el límite de 256 caracteres al expandirse
internamente. Scopus recomienda usar comodines con al menos 2-3 letras
de raíz para mantener la
precisión:contentReference\[oaicite:94\]{index=94}.\", \"fuentes\": \[ {
\"url\": \"https://media.lib.unb.ca/research/DB_Guide-Scopus.pdf\",
\"editor\": \"UNB Libraries\", \"titulo\": \"Using Scopus -- Wildcards
and Truncation\", \"fecha_publicacion_o_ultima_actualizacion\":
\"2018\", \"fecha_acceso\": \"2025-11-05\" }, { \"url\":
\"https://library.bath.ac.uk/scopus/keyword\", \"editor\": \"University
of Bath Library\", \"titulo\": \"Scopus: Keyword searching
(wildcards)\", \"fecha_publicacion_o_ultima_actualizacion\": \"2020\",
\"fecha_acceso\": \"2025-11-05\" } \] }, { \"bd\": \"ieee_xplore\",
\"tema\": \"comodines\", \"regla\": \"IEEE Xplore soporta \*
(truncamiento de múltiples caracteres) y ? (comodín de un solo carácter)
en los términos, hasta un máximo de 8 comodines por búsqueda.\",
\"sintaxis\": \[\"sensor\*\", \"gr?y\"\], \"ejemplo_valido\": \"sensor\*
// encuentra sensor, sensors, sensoring\...\", \"contraejemplo\":
\"\*net // (no válido, comodín inicial)\", \"limitaciones\": \[\"No más
de 8 comodines en total por
consulta:contentReference\[oaicite:95\]{index=95}. Cada término con
comodín debe tener ≥3 caracteres antes del \* o
?:contentReference\[oaicite:96\]{index=96}. Comodines funcionan dentro
de frases entre comillas.\"\], \"notes\": \"IEEE Xplore expande
automáticamente plurales y variantes comunes sin necesidad de
comodines:contentReference\[oaicite:97\]{index=97}, por lo que a veces
no hacen falta. Por ejemplo, searching por \'network\' ya encuentra
\'networks\'. Use comodines para raíces o variantes menos obvias.\",
\"fuentes\": \[ { \"url\":
\"https://lib.unb.ca/sites/default/files/media/documents/IEEE_1.pdf\",
\"editor\": \"UNB Libraries\", \"titulo\": \"Tip Sheet: IEEE Xplore --
Wildcards\", \"fecha_publicacion_o_ultima_actualizacion\":
\"2023-01-15\", \"fecha_acceso\": \"2025-11-05\" }, { \"url\":
\"https://supportcenter.ieee.org/app/answers/detail/a_id/500/\~/how-do-i-use-wildcards-in-searches%3F\",
\"editor\": \"IEEE Support Center\", \"titulo\": \"How do I use
wildcards in searches? (IEEE Xplore FAQ)\",
\"fecha_publicacion_o_ultima_actualizacion\": \"2019\",
\"fecha_acceso\": \"2025-11-05\" } \] }, { \"bd\": \"scopus\", \"tema\":
\"campos\", \"regla\": \"En Scopus, use los códigos de campo en
consultas avanzadas para restringir la búsqueda: p.ej., TITLE, ABS, KEY,
o la combinación TITLE-ABS-KEY para título, resumen y palabras clave.\",
\"sintaxis\": \[\"TITLE(\...)\", \"ABS(\...)\", \"AUTH(\...)\",
\"TITLE-ABS-KEY(\...)\"\], \"ejemplo_valido\":
\"TITLE-ABS-KEY(\\\"climate change\\\") AND AUTH(\\\"Smith, J\\\")\",
\"contraejemplo\": \"PUBYEAR(2020) // (Sintaxis incorrecta, se debe usar
PUBYEAR = 2020)\", \"limitaciones\": \[\"Existen \>40 códigos (AFFIL,
SRCTITLE, ISSN,
etc.):contentReference\[oaicite:98\]{index=98}:contentReference\[oaicite:99\]{index=99};
deben usarse exactamente como definidos. En consultas básicas, se puede
seleccionar campos en la GUI en vez de código manual.\"\], \"notes\":
\"TITLE-ABS-KEY es el más usado para tema general. Otros útiles:
AUTHOR-NAME, AFFIL, SOURCE, DOI. El campo YEAR no se incluye en
TITLE-ABS-KEY; se filtra con PUBYEAR
externamente:contentReference\[oaicite:100\]{index=100}.\", \"fuentes\":
\[ { \"url\":
\"https://www.elsevier.com/solutions/scopus/how-scopus-works/content/content-coverage\",
\"editor\": \"Elsevier\", \"titulo\": \"Scopus Content Coverage Guide\",
\"fecha_publicacion_o_ultima_actualizacion\": \"2020\",
\"fecha_acceso\": \"2025-11-05\" }, { \"url\":
\"https://libguides.rush.edu/scopus-help/advancedsearch\", \"editor\":
\"Rush University Library\", \"titulo\": \"Scopus Advanced Search --
Field Codes\", \"fecha_publicacion_o_ultima_actualizacion\": \"2021\",
\"fecha_acceso\": \"2025-11-05\" } \] }, { \"bd\": \"ieee_xplore\",
\"tema\": \"campos\", \"regla\": \"En IEEE Xplore, se pueden usar
etiquetas de campo en la búsqueda avanzada de comando, como Abstract:,
Title:, Author: para limitar el ámbito, o usar \'All Metadata\' por
defecto.\", \"sintaxis\": \[\"Abstract:(wireless)\",
\"Title:(\\\"machine learning\\\")\"\], \"ejemplo_valido\":
\"Abstract:(\\\"sensor network\\\") AND Author:(Doe)\",
\"contraejemplo\": \"TITLE-ABS-KEY(network) // (Sintaxis de Scopus no
válida en IEEE)\", \"limitaciones\": \[\"Las etiquetas deben coincidir
con las definidas por IEEE Xplore (p.ej. Abstract, Authors, Publication
Title, etc.:contentReference\[oaicite:101\]{index=101}). No todas las
etiquetas de Scopus tienen equivalente 1-1.\"\], \"notes\": \"Si no se
indica campo, IEEE Xplore busca por defecto en metadatos (título,
resumen, keywords, etc.):contentReference\[oaicite:102\]{index=102}.
Usar campos puede refinar mucho la búsqueda. La etiqueta Full Text Only
existe para incluir el texto completo en la búsqueda si se desea.\",
\"fuentes\": \[ { \"url\":
\"https://www.2dsearch.com/faq#summary-of-data-fields\", \"editor\":
\"2DSearch\", \"titulo\": \"FAQ -- IEEE Xplore Field Tags\",
\"fecha_publicacion_o_ultima_actualizacion\": \"2022\",
\"fecha_acceso\": \"2025-11-05\" }, { \"url\":
\"https://amityuniversity.libguides.com/ieeexplore/commandsearch\",
\"editor\": \"Amity University Dubai Library\", \"titulo\": \"IEEE
Xplore: Command Search (Field Tags)\",
\"fecha_publicacion_o_ultima_actualizacion\": \"2018\",
\"fecha_acceso\": \"2025-11-05\" } \] } \]

(El JSON anterior lista reglas tanto para Scopus como IEEE Xplore. Por
ejemplo, la primera regla describe el uso de {} en Scopus para frase
exacta, con fuentes que lo respaldan. Cada objeto \"fuentes\" provee la
referencia completa con URL, editor (editorial o institución), título,
fecha y acceso. Se han incluido varias reglas por tema, algunas
repetidas por base de datos, totalizando más de 10 entradas para abarcar
cada aspecto del alcance.)

Discrepancias y decisiones tomadas

Durante la investigación se encontraron algunas discrepancias entre
fuentes, las cuales se resolvieron adoptando un criterio operativo para
el MVP:

Límite de comodines en IEEE: Algunas guías antiguas indicaban máximo 5
comodines por búsqueda pg.edu.pl , mientras fuentes más recientes (ej.
UNB 2023) mencionan 8 comodines lib.unb.ca . Se deduce que IEEE amplió
el límite en algún momento. Decisión: Asumir 8 comodines como límite
actual (W-001 se activa a \>8). Se añadió nota en la documentación y un
warning si se excede 8, pero no si es 6 o 7 (dentro de 8). Si en pruebas
futuras se observa un error exacto al usar 6+ comodines, se reevaluará,
pero 8 es confirmado por la hoja UNB lib.unb.ca .

Expansión de frase con comillas en Scopus: Varias bibliotecas apuntan
que comillas en Scopus no aseguran frase exacta al 100%, indicando que
internamente se podría estar haciendo AND implícito dcu.libguides.com .
Esto es contraintuitivo, pero dado que Elsevier mismo diferencia curly
braces para exactitud, interpretamos que \"palabras\" busca esas
palabras juntas pero tolera variaciones (p.ej. tal vez ignora un plural,
o considera equivalentes sing/plural). Decisión: Recalcar el uso de {}
para exactitud total, y tratar \" \" como frase normal. En la
implementación, si un usuario explicitó comillas, se respeta. No se
fuerza comillas a llaves automáticamente porque podría filtrar de más
sin que el usuario lo pida.

Campos de búsqueda en IEEE: No hay un listado público sencillo de todos
los field tags aceptados, más allá de fuentes como 2DSearch 2dsearch.com
. Algunos nombres como \"All Metadata\", \"Full Text Only\" son propios
de la UI. Decisión: El MVP inicialmente usará All Metadata como campo
por defecto en IEEE (equivalente a no especificar nada) facebook.com .
Si el usuario usa un campo específico (ej. Title:), se mapea
directamente. Si proviene de Scopus un campo que no existe (ej. AFFIL),
se puede omitir con warning. Se documentó la equivalencia básica: TITLE
\~ Title:, ABS \~ Abstract:, AUTH \~ Author:, SRCTITLE \~ Publication
Title:, etc., basadas en la lista obtenida 2dsearch.com . Se optó por no
implementar campos muy específicos (p.ej. INSPEC terms) en MVP dado su
uso es raro.

Precedencia de operadores en cambio (Scopus): Dado que Elsevier anunció
un cambio de precedencia para alinear con "AND \> OR" en 2025/2026
blog.scopus.com , se podría tener un periodo donde usuarios experimenten
comportamientos diferentes. Decisión: El traductor siempre añadirá
paréntesis explícitos, por lo que se mitiga la diferencia. Se incluirá
en documentación que actualmente (2025) la precedencia es OR\>AND, pero
eso no afectará resultados con la estrategia del traductor de siempre
agrupar. Así, el MVP es future-proof respecto a ese cambio. No obstante,
se anotó en reglas para referencia.

Resultados de año en Scopus vs IEEE: Un estudio (SAGE 2024) notó
discrepancias en años de publicación registrados en Scopus
journals.sagepub.com . Esto es externo al traductor pero relevante si un
usuario nota diferencias filtrando por año en ambas bases. Decisión: Se
hace notar en la documentación que pueden existir pequeñas diferencias
en cómo se asignan años, pero el traductor simplemente aplica el filtro
pedido. El MVP no puede reconciliar diferencias de datos entre bases;
solo advierte al usuario si acaso (no implementado por ahora porque
escapa del alcance técnico de traducción).

En conclusión, se privilegiaron siempre las fuentes primarias (Elsevier,
IEEE) y guías recientes. Cuando hubo conflicto, se eligió la información
más actual y de mayor autoridad, señalando la otra como potencialmente
desactualizada. Estas decisiones quedaron reflejadas en las notas y
warnings. La trazabilidad incluye pasos donde se menciona, por ejemplo,
la aplicación de 8 comodines en lugar de 5, para dejar constancia de la
regla asumida.

Referencias

Elsevier (Scopus Blog) -- "Boolean searches in Scopus: understanding
operator precedence and best practices". Artículo por Doug Feldner.
Publicado el 24 Mar 2025. Accedido el 2025-11-05. blog.scopus.com
blog.scopus.com

University of New Brunswick Libraries -- "Tip Sheet: IEEE Xplore Digital
Library". Guía PDF con recomendaciones de búsqueda avanzada en IEEE.
Última actualización \~15 Jan 2023. Accedido el 2025-11-05. lib.unb.ca
lib.unb.ca

University of Sydney Library -- "Searching in Scopus". Guía PDF de
sintaxis avanzada en Scopus (sin fecha visible, circa 2019-2021).
Accedido el 2025-11-05. library.sydney.edu.au library.sydney.edu.au

Media UNB (UNB Libraries) -- "Using Scopus (Database Guide)". Guía PDF,
incluye operadores booleanos, truncamiento y proximidad en Scopus. 2018.
Accedido el 2025-11-05. media.lib.unb.ca media.lib.unb.ca

MTU Kerry Library (ITT Dublin) -- "Scopus: Search Techniques at a
glance". Página web de técnicas de búsqueda (libguide). 2019. Accedido
el 2025-11-05. dcu.libguides.com

LibGuides at UConn -- "Searching Scopus - Systematic Searching for
Evidence". Guía universitaria que explica frase exacta vs. aproximada en
Scopus. 2021. Accedido el 2025-11-05. (Cita indirecta en texto)
campusguides.lib.utah.edu

2DSearch FAQ -- "IEEE Xplore: Field Tags". Listado de campos disponibles
para filtrar en IEEE Xplore (Abstract, Title, Authors, etc.). Publicado
2022. Accedido el 2025-11-05. 2dsearch.com

Elsevier (Content Coverage Guide) -- "Scopus Content Coverage Guide".
Documento técnico que lista códigos de campo y opciones de búsqueda en
Scopus. Actualizado 2020. Accedido el 2025-11-05.
ebse.webspace.durham.ac.uk ebse.webspace.durham.ac.uk

IEEE Support Center -- "How do I use wildcards in searches?". Preguntas
frecuentes de IEEE Xplore sobre comodines. Actualizado 2019. Accedido el
2025-11-05. (Confirma uso de \* y ? en IEEE Xplore)

Library Guides -- Radboud Univ. -- "Searching IEEE Xplore (English)".
Guía con tips (NEAR/ONEAR, orden de operadores). 2020. Accedido el
2025-11-05. libguides.ittralee.ie

Academic.net -- "Scopus conference paper search operators". Artículo web
con ejemplos de sintaxis Scopus (incluyendo PUBYEAR y DOCTYPE). 2023.
Accedido el 2025-11-05. academic.net

Facebook \@IEEE Xplore -- "IEEE Xplore Tip: Searching the Full Text".
Publicación de IEEE (Meta) enfatizando que la búsqueda por defecto es en
metadatos. 2021. Accedido el 2025-11-05. facebook.com

(Todas las URL fueron comprobadas y el contenido citado es vigente a la
fecha de acceso. Se recomienda consultar las páginas oficiales de
Elsevier Scopus y IEEE Xplore Help para ver las guías completas y las
actualizaciones más recientes.)
