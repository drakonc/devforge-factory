# Configuración del proyecto

Desde el repositorio de destino, ejecuta `devforge init`. Consulta `.devforge/project.yaml` para ajustar la rama y el comando de pruebas. Si existe configuración previa se conserva. Las antiguas claves de perfil o habilitación de conectores se ignoran y los trabajos existentes se pueden seguir consultando.

```yaml
base_branch: develop
worktree_dir: .devforge/worktrees
quality_gates:
  - git-diff-check
  - tests-configured
  - human-approval
test_command: []
test_env: []
```

La inicialización elige `develop` si existe localmente. Después considera la rama predeterminada de origin si está disponible localmente y finalmente la rama actual. Para implementar se necesita al menos un commit en la base.

Configura `test_command` con el comando real del proyecto como lista de argumentos. Las pruebas se ejecutan con Bubblewrap sin red y el gate falla si faltan el comando o el aislamiento. Incluye en `test_env` solo variables necesarias para pruebas.

El origen se elige en cada solicitud. Azure Boards, GitHub y Jira usan los conectores disponibles en la sesión Claude. Los cambios de OpenSpec se importan desde `openspec/changes/<cambio>/` con `devforge openspec` y se validan, sincronizan y archivan al cerrar el trabajo; eso requiere el CLI `openspec`. `devforge repo` identifica el repositorio de GitHub o Azure Repos asociado a origin. `devforge documentos` descubre Markdown, TXT, PDF y DOCX bajo `docs/`. El historial de `docs/requerimientio/` se conserva fuera del listado automático y se puede importar por ruta explícita. Al importar un documento se registra su ruta y se conserva el original.

## Capacidad y rondas

`concurrency` limita las reservas simultáneas de la cola local (2 por defecto). `max_rounds` fija el número máximo de rondas de construcción y revisión de cada trabajo nuevo (3 por defecto). `reservation_ttl_hours` (12 por defecto) caduca las reservas abandonadas: al consultar o reservar, el núcleo libera las que superaron ese plazo y `devforge cola` informa cuántas liberó. Las reservas siguen liberándose a mano con `devforge liberar ID`; antes de recuperar una reserva comprueba que su agente haya terminado. En repositorios inicializados anteriormente se aplican estos valores cuando faltan las claves. El límite gobierna la cola cooperativa y los trabajos iniciados a mano quedan bajo coordinación del operador.

GitHub se identifica por propietario/repositorio. Para Azure DevOps Services, `devforge repo` normaliza el remoto HTTPS de dev.azure.com o SSH v3 de ssh.dev.azure.com a la URL HTTPS de Azure Repos. La consulta de Boards se limita a la organización y proyecto elegidos en Claude. La publicación automática de PR sigue disponible solo en GitHub.

Si falla una importación conectada, el archivo de staging se conserva para reintentar. Un trabajo creado correctamente consume y elimina su copia temporal.
