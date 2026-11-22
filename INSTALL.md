# Instalación

## Núcleo

1. Instala Python 3.11+, Git, Bubblewrap (`bwrap`) y PyYAML 6. Los repositorios locales pueden usar `python3 -m pip install -e /ruta/a/devforge-factory`.
2. Para leer PDF instala `pdftotext` (por ejemplo, `poppler-utils`). DOCX se lee con la biblioteca estándar.
3. Para importar cambios de OpenSpec y archivarlos al cerrar, instala el CLI `openspec` y ejecuta `openspec init` en el proyecto.
4. Comprueba `devforge --help`.

## Claude Code

Copia o enlaza `.claude/skills/factory/SKILL.md`, `.claude/agents/` y `.claude/settings.json` a la raíz del proyecto donde ejecutarás la fábrica. Revisa y combina las restricciones con la configuración existente; no sobrescribas settings existentes. Antes de delegar, confirma en Claude Code que `/sandbox` indica sandbox activo y que `/status` carga las restricciones. Ejecuta `devforge init` desde ese repositorio. Ajusta `test_command` y `base_branch` en `.devforge/project.yaml`.

La configuración de referencia habilita el sandbox de Bash de Claude Code con fallo cerrado si no está disponible y bloquea las lecturas de herramientas de archivos fuera de los directorios de trabajo. Claude documenta que el sandbox de Bash no cubre las herramientas integradas de archivos, Web, MCP ni hooks; revisa los límites en la [documentación oficial de sandbox](https://code.claude.com/docs/en/sandboxing).

Los worktrees se crean en `.devforge/worktrees/`, ignorado por Git. Los Quality Gates requieren `bwrap`: ejecuta las pruebas con filesystem de solo lectura salvo el worktree, HOME temporal, red aislada y solo variables explícitas en `test_env`. Si `bwrap` no está instalado o el sistema no permite crear el aislamiento, las pruebas fallan cerradas.

Para comprobar la instalación abre Claude en el proyecto y escribe `/factory hacer docs`. Para ver sus issues abiertas usa `/factory hacer`.

## Credenciales

La ingesta remota usa las integraciones conectadas a la sesión Claude; el CLI local no consulta Jira, GitHub ni correo y no requiere tokens API. No pegues tokens en solicitudes, YAML, argumentos, archivos de trabajo o logs. No se requiere push para crear y revisar trabajos.
