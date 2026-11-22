# Arquitectura

## Límites

`devforge_factory` es el núcleo local responsable de configuración, normalización, persistencia, transiciones, worktrees y Quality Gates aislados. `.claude/skills/factory/SKILL.md` dirige el flujo conversacional; cada rol tiene una definición Markdown independiente en `.claude/agents/`. La sesión Claude importa elementos de Azure Boards, correo, Jira y GitHub usando las integraciones conectadas disponibles; el núcleo consume temporalmente un archivo de staging ignorado y lo elimina tras crear el trabajo. El núcleo local no hace solicitudes HTTP a esos servicios ni lee tokens API. Cada proyecto tiene `.devforge/project.yaml` y trabajos JSON/Markdown bajo `.devforge/jobs/`.

```text
Fuentes Claude conectadas / archivos / texto
                    |
       Skill /factory + agentes Markdown
                    |
     CLI local recibe contenido por stdin
                    |
   normalización + estado JSON + worktree
                    |
   Quality Gates aislados + revisiones Claude
                    |
        aprobación humana de publicación
```

Cada repositorio mantiene su configuración en `.devforge/project.yaml`. El orquestador identifica GitHub por el remoto origin y limita las consultas Jira al sitio o proyecto indicado. También acepta texto y requerimientos de `docs/`. Todos entran al mismo flujo de admisión, plan, construcción, gates y revisión. Los informes se vinculan al commit revisado y el estado persistente permite reanudar el trabajo.

## Ramas y aislamiento

Cada trabajo usa su propio worktree y rama `feature/{key}-{slug}` desde `base_branch` (configurada al inicializar el repositorio). Los cambios de implementación se dirigen al worktree asignado. El contenido importado se conserva como dato no confiable. Los Quality Gates ejecutan las pruebas dentro de un namespace Bubblewrap sin red, con filesystem mínimo de solo lectura y solo el worktree escribible; si el aislamiento no está disponible, fallan cerrados.

La fábrica sitúa los worktrees en `.devforge/worktrees/`, bajo la raíz del proyecto y excluidos de Git. Claude Code debe tener activo su sandbox y las restricciones de lectura de credenciales conocidas antes de delegar. La configuración actual no confina todas las herramientas Claude al worktree: sus permisos cubren el proyecto completo y se limitan por patrones de nombres de secretos; repositorios con credenciales locales no cubiertas requieren limpieza o aislamiento adicional antes de procesar entradas no confiables.

## Herdr

El SDK local inspeccionado (`~/.config/herdr-app/herdr.d.ts`) expone `knownAgents()` para mods; la CLI local permite consultar terminales e iniciar procesos con `hc run`. También se comprobaron las ayudas de OpenCode y Codex. No se verificó que los procesos `hc run` hereden el sandbox ni la integridad de resultados. Por ello el comando no inicia esos agentes en esta versión y continúa con subagentes nativos Claude Code. El núcleo CLI no inventa protocolos propios de Herdr; la integración queda pendiente de aislamiento equivalente.

## Ciclo local

La cola ordena los trabajos por creación. Una reserva atómica bajo bloqueo de archivo evita asignar un trabajo dos veces entre procesos cooperantes. El bloqueo de operaciones por trabajo serializa cambios de estado. Los constructores pueden operar en paralelo en worktrees distintos. Los informes vigentes se archivan en `round-N/` al solicitar una ronda de correcciones o al cerrar. El cierre requiere evidencia vigente y confirmación humana. El tablero es una vista HTML estática que se regenera desde el estado local.
