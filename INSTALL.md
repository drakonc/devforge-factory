# Instalación

## Núcleo

1. Instala Python 3.11+, Git, Bubblewrap (`bwrap`) y PyYAML 6. En Windows no hace falta Bubblewrap ni WSL: consulta [Windows nativo](#windows-nativo). Para desarrollo usa un entorno virtual: `uv venv && uv pip install --editable .` (y ejecuta `.venv/bin/devforge`). Si prefieres el `pip` del sistema y no existe, instala antes `python3-pip`; en equipos con `uv` también sirve `uv tool install --editable /ruta/a/devforge-factory`.
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
4. Copia `.claude/settings.json` a `~/.claude/settings.json` solo si no existe; si existe, lo combina: conserva todos tus valores y solo añade las claves y elementos de lista que falten (las entradas con `name` o `path` se comparan por ese campo). Si tu archivo no es JSON válido, no se toca. `devforge` necesita correr fuera del sandbox de Claude para crear worktrees; sus tests se aíslan con su propio `bwrap`.

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

La configuración de referencia habilita el sandbox de Bash de Claude Code con fallo cerrado si no está disponible. Deja `blockReadsOutsideWorkingDirectories` en `false` para que Claude no pida permiso en cada lectura fuera del proyecto; las lecturas sensibles siguen denegadas por `permissions.deny` y `sandbox.filesystem.denyRead`. Claude documenta que el sandbox de Bash no cubre las herramientas integradas de archivos, Web, MCP ni hooks; revisa los límites en la [documentación oficial de sandbox](https://code.claude.com/docs/en/sandboxing).

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
uv tool install "git+https://dev.azure.com/ORG/PROYECTO/_git/devforge-factory@v0.1.2"
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
uv tool install devforge-factory==0.1.2 --index https://pkgs.dev.azure.com/ORG/PROYECTO/_packaging/FEED/pypi/simple/
devforge instalar-global
```

El feed debe tener también PyYAML. Configura las credenciales con el gestor de secretos de uv o el credential helper; nunca en la línea de comandos.

### Desde un wheel compartido

```bash
uv tool install /ruta/compartida/devforge_factory-0.1.2-py3-none-any.whl
devforge instalar-global
```

### Sin red (air-gapped)

Descarga el wheel de DevForge y el de PyYAML en una máquina conectada, cópialos juntos y:

```bash
uv tool install --no-index --find-links ./dist devforge-factory==0.1.2
devforge instalar-global
```

Actualizar: `uv tool upgrade devforge-factory` y repite `devforge instalar-global` para refrescar los agentes. La skill se actualiza al reinstalar.

## Windows nativo

Funciona en Windows 10/11 sin WSL, desde PowerShell o cmd. Requisitos: Python 3.11+, Git para Windows y `uv` (o `pipx`).

```powershell
uv tool install git+https://github.com/drakonc/devforge-factory
devforge instalar-global
```

Desde un clon local: `uv tool install --editable C:\ruta\devforge-factory`. `scripts/instalar-global.sh` es solo para Linux; en Windows `devforge instalar-global` hace lo mismo copiando la skill en lugar de enlazarla, así que repítelo al actualizar.

Diferencias respecto a Linux:

- **Sandbox de Claude Code.** No existe en Windows nativo, y con `sandbox.failIfUnavailable` Claude Code se niega a arrancar. Por eso `devforge instalar-global` omite el bloque `sandbox` y solo añade `permissions`. Los comandos de los agentes se ejecutan sin sandbox; `/sandbox` no aplica.
- **Gate de pruebas.** Bubblewrap no existe, así que `tests-configured` falla cerrado por defecto. Para ejecutar las pruebas añade a `.devforge/project.yaml`:

  ```yaml
  test_isolation: none
  ```

  Las pruebas se lanzan sin shell, con un entorno mínimo más `test_env`, con `USERPROFILE`, `APPDATA`, `LOCALAPPDATA` y `TEMP` apuntando a una carpeta temporal, y con el límite de 30 minutos. **No hay aislamiento de disco ni de red.** El valor se fija al crear cada trabajo: los trabajos anteriores al cambio siguen fallando cerrados.
- **Perfil temporal.** Las herramientas que guardan caché en el perfil (NuGet, npm, Composer) no la encuentran. Declara en `test_env` el nombre de la variable que apunta a la caché real, por ejemplo `NUGET_PACKAGES` o `npm_config_cache`, y defínela en tu entorno.
- **`test_command`.** El primer argumento se resuelve en `PATH` con `PATHEXT` (`npm` encuentra `npm.cmd`); una ruta relativa como `vendor/bin/phpunit` se resuelve dentro del worktree.
- **Enlaces simbólicos.** Las comprobaciones que los rechazan siguen activas; no hace falta el modo desarrollador.

## Ubuntu 24.04+ y 26.04: sandbox de Claude

Ubuntu 26.04 trae `/etc/apparmor.d/bwrap-userns-restrict`, que apila los procesos hijos de `bwrap` en el perfil `unpriv_bwrap` y les niega `CAP_SYS_ADMIN`. Claude Code necesita un espacio de nombres de usuario **anidado** para su paso `apply-seccomp`, así que todo comando falla con:

```
apply-seccomp: write /proc/self/setgroups (nested userns is capability-restricted; caller must provide CAP_SYS_ADMIN): Permission denied
```

`bwrap` directo funciona, lo que despista. El perfil de distro es la causa. Para sustituirlo por el perfil que documenta Claude Code:

```bash
sudo mkdir -p /etc/apparmor.d/disable
sudo ln -sf /etc/apparmor.d/bwrap-userns-restrict /etc/apparmor.d/disable/
sudo apparmor_parser -R /etc/apparmor.d/bwrap-userns-restrict

sudo tee /etc/apparmor.d/bwrap >/dev/null <<'EOF'
abi <abi/4.0>,
include <tunables/global>

profile bwrap /usr/bin/bwrap flags=(unconfined) {
  userns,
  include if exists <local/bwrap>
}
EOF

sudo apparmor_parser -r /etc/apparmor.d/bwrap
sudo aa-status | grep -E 'bwrap|unpriv_bwrap'
```

Debe quedar solo `bwrap`; si aparece `unpriv_bwrap`, el perfil anterior sigue cargado. Reinicia Claude Code y comprueba `/sandbox`.

Es un cambio con coste de seguridad: se permite que los hijos de `bwrap` conserven capacidades dentro del espacio de nombres. La alternativa conservadora es no usar el sandbox de Claude y ejecutar `devforge` desde una terminal normal, pero entonces `/factory` no delega.

`enableWeakerNestedSandbox` no resuelve este caso: cambia la ruta y falla con `unshare(CLONE_NEWUSER): Invalid argument`.

## Credenciales

La ingesta remota usa las integraciones conectadas a la sesión Claude; el CLI local no consulta Jira, GitHub ni correo y no requiere tokens API. No pegues tokens en solicitudes, YAML, argumentos, archivos de trabajo o logs. No se requiere push para crear y revisar trabajos.
