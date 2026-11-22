# Seguridad

- Las entradas de Jira, GitHub y documentos son datos no confiables; el prompt del orquestador prohíbe tratarlas como instrucciones.
- Los cuerpos de Jira, GitHub y correo llegan mediante herramientas conectadas de Claude; el CLI no envía credenciales ni hace solicitudes HTTP a esos servicios.
- La configuración local no se sobrescribe. El estado se escribe atómicamente y las transiciones se validan.
- Los trabajos corren en worktrees y ramas independientes. No se ejecuta push, merge ni deploy automáticamente.
- La fábrica guarda worktrees bajo `.devforge/worktrees/` para mantenerlos dentro del directorio autorizado del proyecto. La configuración Claude de referencia exige sandbox disponible, bloquea lecturas fuera de directorios de trabajo y deniega archivos de credenciales comunes (`.env*`, claves, tokens y directorios de credenciales). Debe combinarse con settings existentes y verificarse con `/sandbox` y `/status` antes de operar.
- El sandbox de Claude Code cubre los comandos Bash, pero sus herramientas integradas de archivos, web, MCP y hooks no quedan dentro del mismo límite del sistema operativo. Las restricciones de lectura por directorio se aplican por separado; no se afirma aislamiento completo del equipo.
- Los comandos de Quality Gates se configuran como arreglos de argumentos, sin shell; `bwrap` los ejecuta con filesystem de solo lectura salvo el worktree, HOME temporal, red aislada y variables explícitas desde `test_env`. Si `bwrap` falta o no puede crear el aislamiento, el gate falla cerrado.
- El comando de prueba y sus variables se fijan al crear el trabajo para que una rama no pueda reemplazarlos.
- Antes de publicar una PR, el usuario debe aprobar explícitamente el diff, los gates y el destino.
- `devforge publicar` pide aprobación en conversación y una confirmación exacta en terminal antes del primer push; crea solo una PR borrador y nunca fusiona.
- Si GitHub informa que el SHA de la PR no coincide con el revisado, el trabajo pasa a bloqueado y no puede volver a publicarse automáticamente; la PR borrador queda registrada para intervención humana.
- Los datos del trabajo permanecen locales dentro de `.devforge/jobs/`, ignorados por Git. Revisa retención antes de guardar documentos sensibles.

## Limitaciones conocidas

**Riesgo alto pendiente: el orquestador y los subagentes Claude Code tienen como ámbito el proyecto completo.** Los worktrees aíslan los cambios Git por trabajo, pero no son un límite de sistema operativo para las herramientas `Read`, `Bash`, `Edit` y `Write`. Las denegaciones de credenciales cubren rutas y nombres conocidos, no todos los secretos que una persona pudiera guardar en el proyecto. No proceses Issue, correo o documentos no confiables desde repositorios con credenciales o datos sensibles locales que no estén excluidos de forma efectiva. Esta versión deja este límite documentado; no afirma aislamiento completo de agentes por worktree.

La disponibilidad de subagentes Herdr/OpenCode/Codex no se infiere del mero hecho de que Herdr esté instalado. Aunque la interfaz local `hc run` fue inspeccionada, no se verificó herencia del sandbox ni integridad del ciclo de resultados. Esta versión no invoca esos procesos mediante Herdr; usa subagentes Claude Code y deja la integración externa pendiente de aislamiento equivalente.

Claude Code, sus subagentes nativos y las herramientas fuera del sandbox pueden tener acceso a datos del proyecto o integraciones configuradas; las denegaciones cubren patrones conocidos y no son una frontera completa por archivo de trabajo. No ejecutar solicitudes o documentos no confiables si existen credenciales con nombres/rutas no cubiertos o si las restricciones no aparecen activas. Los gates quedan confinados por Bubblewrap, pero requieren el binario del sistema y las capacidades Linux de espacios de nombres; si faltan, no ejecutan los tests.
