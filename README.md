# DevForge Factory

Fábrica local de software con un núcleo Python, configuración YAML por repositorio, un comando `/factory` para Claude Code y estado persistente por proyecto.

Los agentes y el orquestador están definidos en Markdown. Python implementa el núcleo local determinista (estado, worktrees, normalización y gates); V2 de referencia también contiene scripts Python con shebang en `factory/bin/`, aunque no usen extensión `.py`. DevForge no copia esos scripts ni sus prompts.

## Inicio rápido

Requiere Python 3.11 o superior, Git, Bubblewrap (`bwrap`), Claude Code y PyYAML 6. Instala el CLI desde este repositorio con `python3 -m pip install -e .`. Para usar `/factory` en todos tus proyectos sin copiar archivos, ejecuta `./scripts/instalar-global.sh`; después abre Claude Code en cada repositorio y ejecuta `/factory init`. Consulta [INSTALL.md](INSTALL.md).

El proyecto debe tener la rama base configurada (se prefiere `develop` si existe) y local. Configura `test_command` en `.devforge/project.yaml` como lista de argumentos, por ejemplo `["python3", "-m", "unittest", "discover"]`. Los trabajos se guardan en `.devforge/jobs/`; sus worktrees quedan en `.devforge/worktrees/`, ignorados por Git. Los gates corren sin red con el filesystem de solo lectura, salvo el worktree.

## Entradas desde Claude Code

| Petición | Qué hace la fábrica |
| --- | --- |
| `/factory hacer` | Identifica el repositorio desde Git y lista sus issues abiertas para elegir. |
| `/factory hacer Jira ABC-123` | Lee ese ticket del Jira indicado. |
| `/factory hacer docs` | Lista documentos del proyecto. Puedes señalar directamente una ruta como `docs/requisitos/pedidos.md`. |
| `/factory agrega un filtro por estado` | Crea un trabajo con tu texto. |

## Acciones

- `devforge hacer "Agregar ..."` crea una solicitud directa.
- `/factory hacer` importa Jira, correo o GitHub Issues con las integraciones conectadas en Claude; el núcleo no necesita tokens de esos servicios.
- `devforge hacer --file .devforge/import-staging/import-abc123.md --source github --key GH-org-repo-123` registra una importación temporal y elimina el archivo al crear el trabajo.
- `devforge hacer --file solicitud.md` lee Markdown, TXT, PDF o DOCX. PDF requiere `pdftotext`.
- `devforge plan`, `seguir`, `ver`, `revisar` y `parar` implementan el menú persistente.

La acción auxiliar `devforge publicar ID` exige informes APTO ligados al mismo SHA, Quality Gates aprobados y una confirmación escrita con la URL remota saneada. Solo crea PR borrador; no fusiona ni despliega. El comando no se invoca sin aprobación humana explícita. Consulta [INSTALL.md](INSTALL.md), [CONFIGURATION.md](CONFIGURATION.md), [ARCHITECTURE.md](ARCHITECTURE.md) y [SECURITY.md](SECURITY.md).

## Referencias de diseño

Se revisaron [Software Factory Claude Code V1](https://github.com/zazencodes/zazencodes-season-3/tree/main/src/software-factory-claude-code) y [V2](https://github.com/zazencodes/zazencodes-season-3/tree/main/src/software-factory-claude-code-v2). V2 está bajo GPLv3. DevForge implementa su propio núcleo, flujo y redacción de agentes; no se copiaron archivos fuente de esas fábricas.

## Cambios de OpenSpec

`devforge openspec <cambio>` importa un cambio de `openspec/changes/<cambio>/` que tenga `proposal.md`, `design.md`, `tasks.md` y al menos un `specs/**/spec.md`. El trabajo guarda esos artefactos en su `request.md` y registra `document: openspec/changes/<cambio>`.

Al ejecutar `devforge cerrar ID`, la fábrica valida el cambio con `openspec validate --strict`, sincroniza las delta specs y lo archiva con `openspec archive --yes`. Si la validación o el archivado fallan, el trabajo sigue en revisión. Requiere el CLI de OpenSpec instalado.

## Operar un backlog local

| Acción | Resultado |
| --- | --- |
| `/factory init` | Prepara el repositorio y pregunta rama base, comando de pruebas, variables, rondas, concurrencia, reservas y gates. |
| `/factory hacer Azure AB-123` | Usa el conector Azure de la sesión para leer el elemento en la organización y el proyecto indicados. |
| `devforge hacer "Corregir total" --type fix` | Crea el trabajo en una rama de corrección. También se admiten feature, hotfix y chore. |
| `devforge cola` | Lista los trabajos ordenados por creación, sus reservas y libera las caducadas. |
| `/factory procesar cola` | Coordina los trabajos ya admitidos en la cola local con las plazas disponibles de la sesión. |
| `devforge dashboard` | Genera una instantánea HTML local con estado, ronda, origen y reserva de cada trabajo. La página se recarga cada 5 segundos; vuelve a ejecutar el comando para regenerar el contenido. |
| `devforge cerrar ID` | Cierra localmente un trabajo revisado tras la decisión humana. El cierre no equivale a una fusión del código. |

Usa `devforge tomar` para reservar un trabajo pendiente y `devforge liberar ID` para devolver su plaza. Una sesión interrumpida conserva sus reservas para inspección. En Azure Repos el equipo conserva la publicación de PR y las políticas de rama en Azure DevOps.
