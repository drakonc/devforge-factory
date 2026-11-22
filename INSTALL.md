# Instalación

## Núcleo

1. Instala Python 3.11+, Git, Bubblewrap (`bwrap`) y PyYAML 6. Para desarrollo usa un entorno virtual: `uv venv && uv pip install --editable .` (y ejecuta `.venv/bin/devforge`). Si prefieres el `pip` del sistema y no existe, instala antes `python3-pip`; en equipos con `uv` también sirve `uv tool install --editable /ruta/a/devforge-factory`.
2. Para leer PDF instala `pdftotext` (por ejemplo, `poppler-utils`). DOCX se lee con la biblioteca estándar.
3. Para importar cambios de OpenSpec y archivarlos al cerrar, instala el CLI `openspec` y ejecuta `openspec init` en el proyecto.
4. Comprueba `devforge --version` y `devforge --help`.

Si responde `devforge: command not found`, ejecuta `scripts/instalar-global.sh` o comprueba que `~/.local/bin` está en `PATH`.

## Instalación global (recomendada)

Instala una vez y usa `/factory` en todos tus proyectos:

```bash
./scripts/instalar-global.sh
```

El script:

1. Instala el CLI con `pipx` si `devforge` no existe.
2. Enlaza la skill en `~/.claude/skills/factory` (symlink: los cambios del repo se ven al instante).
3. Copia los agentes `devforge-*.md` a `~/.claude/agents/`.
4. Copia `.claude/settings.json` a `~/.claude/settings.json` solo si no existe; si existe, avisa para combinarlo.

Repite el script cuando actualices los agentes. La skill se actualiza sola por el symlink. Usa `CLAUDE_CONFIG_DIR` si tu configuración de Claude vive en otra ruta.

Equivalente manual:

```bash
ln -sfn /ruta/devforge-factory/.claude/skills/factory ~/.claude/skills/factory
cp /ruta/devforge-factory/.claude/agents/devforge-*.md ~/.claude/agents/
```

## Por proyecto

Cada repositorio conserva su configuración en `.devforge/project.yaml`. Desde Claude Code:

```text
/factory init
```

La fábrica ejecuta `devforge init`, detecta la rama base y el comando de pruebas, y **pregunta** rama, `test_command`, `test_env`, `max_rounds`, `concurrency`, `reservation_ttl_hours` y gates antes de escribir el YAML. Si prefieres valores por defecto sin preguntas, ejecuta `devforge init` directamente. Puedes commitear `.devforge/project.yaml` para compartirlo con el equipo. Si prefieres aislar los agentes por repositorio, copia `.claude/skills/factory/` y `.claude/agents/` al proyecto en lugar de usar la instalación global.

Antes de delegar, confirma en Claude Code que `/sandbox` indica sandbox activo y que `/status` carga las restricciones.

La configuración de referencia habilita el sandbox de Bash de Claude Code con fallo cerrado si no está disponible y bloquea las lecturas de herramientas de archivos fuera de los directorios de trabajo. Claude documenta que el sandbox de Bash no cubre las herramientas integradas de archivos, Web, MCP ni hooks; revisa los límites en la [documentación oficial de sandbox](https://code.claude.com/docs/en/sandboxing).

Los worktrees se crean en `.devforge/worktrees/`, ignorado por Git. Los Quality Gates requieren `bwrap`: ejecuta las pruebas con filesystem de solo lectura salvo el worktree, HOME temporal, red aislada y solo variables explícitas en `test_env`. Si `bwrap` no está instalado o el sistema no permite crear el aislamiento, las pruebas fallan cerradas.

Para comprobar la instalación abre Claude en el proyecto y escribe `/factory hacer docs`. Para ver sus issues abiertas usa `/factory hacer`.

## Otra máquina sin copiar el repositorio

El wheel incluye el CLI, la skill y los 9 agentes. En la máquina de destino basta instalar el paquete y ejecutar una vez:

```bash
devforge instalar-global
```

Eso copia la skill a `~/.claude/skills/factory`, los agentes a `~/.claude/agents/` y los settings solo si no existen.

### Desde un repositorio interno (Azure Repos)

```bash
uv tool install "git+https://dev.azure.com/ORG/PROYECTO/_git/devforge-factory@v0.1.0"
devforge instalar-global
```

Usa el credential manager de Git para autenticar; no pegues un PAT en el comando. Versión por tag para que la instalación sea reproducible.

### Desde un feed PyPI interno (Azure Artifacts)

En una máquina con acceso al feed:

```bash
uv build --wheel
uv publish --publish-url https://pkgs.dev.azure.com/ORG/PROYECTO/_packaging/FEED/pypi/upload dist/*
```

En la máquina de destino:

```bash
uv tool install devforge-factory==0.1.0 --index https://pkgs.dev.azure.com/ORG/PROYECTO/_packaging/FEED/pypi/simple/
devforge instalar-global
```

El feed debe tener también PyYAML. Configura las credenciales con el gestor de secretos de uv o el credential helper; nunca en la línea de comandos.

### Desde un wheel compartido

```bash
uv tool install /ruta/compartida/devforge_factory-0.1.0-py3-none-any.whl
devforge instalar-global
```

### Sin red (air-gapped)

Descarga el wheel de DevForge y el de PyYAML en una máquina conectada, cópialos juntos y:

```bash
uv tool install --no-index --find-links ./dist devforge-factory==0.1.0
devforge instalar-global
```

Actualizar: `uv tool upgrade devforge-factory` y repite `devforge instalar-global` para refrescar los agentes. La skill se actualiza al reinstalar.

## Credenciales

La ingesta remota usa las integraciones conectadas a la sesión Claude; el CLI local no consulta Jira, GitHub ni correo y no requiere tokens API. No pegues tokens en solicitudes, YAML, argumentos, archivos de trabajo o logs. No se requiere push para crear y revisar trabajos.
