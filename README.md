# DevForge Factory

Fábrica local de software para Claude Code. Conviertes una petición (texto, issue de GitHub, ticket Jira, elemento de Azure Boards, documento o cambio OpenSpec) en un trabajo que se planifica, se implementa en un worktree aislado, pasa Quality Gates y revisiones independientes, y queda listo para tu decisión.

- **`/factory`** (skill de Claude Code) orquesta el flujo y delega en los agentes `devforge-*`.
- **`devforge`** (CLI en Python) guarda el estado, crea los worktrees y ejecuta los gates deterministas.
- **Tú decides**: nada se publica, fusiona ni despliega sin tu aprobación explícita.

## Requisitos

- Python 3.11+, Git y Claude Code.
- Bubblewrap (`bwrap`) para ejecutar las pruebas aisladas.
- Opcionales: `gh` (publicar PR en GitHub), `openspec` (cambios OpenSpec), `pdftotext` (leer PDF).

## Instalación

Una sola vez por máquina:

```bash
uv tool install git+https://github.com/drakonc/devforge-factory
devforge instalar-global
```

Sin `uv`: `pipx install git+https://github.com/drakonc/devforge-factory`. Desde un clon local: `./scripts/instalar-global.sh`.

`devforge instalar-global` instala en `~/.claude/` la skill `/factory`, los 9 agentes y la configuración de referencia de Claude Code. Si ya tienes `~/.claude/settings.json`, **lo combina sin pisar nada**: conserva tus valores, añade solo lo que falta y deja un respaldo en `settings.json.bak`.

Esa configuración activa el sandbox de Bash y excluye `devforge` de él (`excludedCommands: ["devforge", "devforge *"]`), porque el CLI necesita crear worktrees en `.git/worktrees`. Las pruebas que lanza `devforge` siguen aisladas con su propio `bwrap`.

Comprueba con `devforge --version`. Detalles en [INSTALL.md](INSTALL.md).

## Primeros pasos en un proyecto

Abre Claude Code en el repositorio y ejecuta:

```text
/factory init
```

La fábrica detecta y te pregunta rama base, comando de pruebas, variables de prueba, rondas máximas, concurrencia, horas de reserva y gates, y lo guarda en `.devforge/project.yaml`. Puedes commitear ese archivo para compartirlo con el equipo. Opciones en [CONFIGURATION.md](CONFIGURATION.md).

## Uso diario

Escribe `/factory` para ver el menú, o pide directamente:

| Quieres | Escribe |
| --- | --- |
| Crear un trabajo con tu texto | `/factory agrega un filtro por estado` |
| Elegir entre las issues abiertas del repo | `/factory hacer` |
| Traer una issue concreta | `/factory hacer #42` |
| Traer un ticket Jira | `/factory hacer Jira ABC-123` |
| Traer un elemento de Azure Boards | `/factory hacer AB#123` |
| Usar un requerimiento en `docs/` | `/factory hacer docs` o `/factory hacer docs/requisitos/pedidos.md` |
| Trabajar un cambio OpenSpec | `/factory openspec add-user-auth` |
| Planificar alcance y criterios | `/factory plan ID` |
| Implementar o reanudar | `/factory seguir ID` |
| Ejecutar gates y revisiones | `/factory revisar ID` |
| Ver el estado de los trabajos | `/factory ver` |
| Pausar sin perder nada | `/factory parar ID` |
| Procesar varios trabajos | `/factory procesar cola` |

GitHub, Jira y Azure Boards se leen con los conectores de tu sesión de Claude; el CLI no necesita tokens de esos servicios.

## Ciclo de un trabajo

```text
hacer ──> plan ──> seguir ──> revisar ──> decisión humana ──> cerrar / publicar
          │        │          │
          │        │          ├─ gates: git diff --check, pruebas en bwrap, aprobación humana
          │        │          └─ revisores: código, seguridad, QA (+ UX/UI si hay interfaz)
          │        └─ devforge-builder implementa en .devforge/worktrees/<id>
          └─ devforge-intake admite o pide información; devforge-planner escribe plan.md
```

- Si un gate o un revisor pide cambios, se abre otra ronda (`rework`) hasta `max_rounds`.
- `devforge-approver` emite una **recomendación**; la aprobación es siempre tuya.
- `devforge cerrar ID` cierra el trabajo localmente con tu confirmación escrita. En cambios OpenSpec también valida, sincroniza y archiva el cambio.
- `devforge publicar ID` solo crea una PR borrador en GitHub, con informes APTO del mismo SHA y tu confirmación. No fusiona ni despliega.

Cada trabajo vive en `.devforge/jobs/<id>/` (solicitud, plan, informes por ronda) y su código en `.devforge/worktrees/<id>/`, ambos ignorados por Git. Tu checkout principal no se toca.

## Comandos del CLI

Normalmente los ejecuta `/factory`, pero puedes usarlos directamente:

| Comando | Qué hace |
| --- | --- |
| `devforge init` | Crea `.devforge/project.yaml` con valores por defecto. |
| `devforge hacer "texto" [--type fix]` | Crea un trabajo; también `--file ruta` (MD, TXT, PDF, DOCX) o `--stdin`. |
| `devforge openspec <cambio>` | Importa un cambio de `openspec/changes/`. |
| `devforge plan\|seguir\|revisar\|parar ID` | Avanza, reanuda, verifica o pausa un trabajo. |
| `devforge ver` / `devforge cola` | Lista trabajos / backlog con reservas. |
| `devforge tomar [ID]` / `devforge liberar ID` | Reserva o libera un trabajo de la cola. |
| `devforge dashboard` | Genera un tablero HTML local que se recarga solo. |
| `devforge repo` / `devforge documentos` | Identifica el remoto (GitHub/Azure) / lista requisitos en `docs/`. |
| `devforge cerrar ID` / `devforge publicar ID` | Cierre local / PR borrador, ambos con confirmación humana. |

## Problemas frecuentes

**`devforge: orden no encontrada` dentro de Claude Code.** El sandbox oculta `~/.local/bin`. Comprueba que `~/.claude/settings.json` (o `.claude/settings.local.json`) tiene `"devforge"` y `"devforge *"` en `sandbox.excludedCommands`. Si no, vuelve a ejecutar `devforge instalar-global` y reinicia la sesión. La regla `"devforge"` sola solo cubre el comando sin argumentos.

**Todo comando falla con `apply-seccomp: write /proc/self/setgroups ... Permission denied`.** En Ubuntu 24.04+ el perfil AppArmor `bwrap-userns-restrict` impide el userns anidado que usa el sandbox de Claude Code. Desactiva ese perfil y crea uno que permita `userns` a `/usr/bin/bwrap`:

```bash
sudo ln -s /etc/apparmor.d/bwrap-userns-restrict /etc/apparmor.d/disable/
sudo apparmor_parser -R /etc/apparmor.d/bwrap-userns-restrict
sudo tee /etc/apparmor.d/bwrap > /dev/null <<'EOF'
abi <abi/4.0>,
include <tunables/global>

profile bwrap /usr/bin/bwrap flags=(unconfined) {
  userns,
  include if exists <local/bwrap>
}
EOF
sudo apparmor_parser -r /etc/apparmor.d/bwrap
```

Con esto `bwrap` queda sin confinamiento AppArmor, aunque mantiene su propio aislamiento.

**El gate de pruebas falla siempre.** Revisa que `test_command` en `.devforge/project.yaml` no esté vacío y que `bwrap` funcione. Sin aislamiento, el gate falla cerrado a propósito.

## Más documentación

[INSTALL.md](INSTALL.md) · [CONFIGURATION.md](CONFIGURATION.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [SECURITY.md](SECURITY.md)

## Estado y licencia

Beta. La integración con conectores y el aislamiento de agentes deben validarse en cada entorno. Licencia MIT, ver [LICENSE](LICENSE).

DevForge se inspiró en [Software Factory Claude Code V1](https://github.com/zazencodes/zazencodes-season-3/tree/main/src/software-factory-claude-code) y [V2](https://github.com/zazencodes/zazencodes-season-3/tree/main/src/software-factory-claude-code-v2) (GPLv3); implementa su propio núcleo, flujo y agentes sin copiar sus archivos.
