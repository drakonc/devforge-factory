# Pendientes de DevForge Factory

**Estado revisado:** 21 de noviembre de 2026  
**Alcance:** brechas que siguen abiertas después del último ciclo de implementación. La fábrica no debe considerarse completa para operación empresarial hasta cerrar o aceptar explícitamente estos puntos.

## Ya implementado desde la comparativa

Estos puntos ya no se consideran faltantes de implementación:

- Ciclo persistente por trabajo, con rondas de revisión y retrabajo limitadas por configuración.
- Pausa y reanudación por etapa, cierre local sujeto a gates y decisión humana, y liberación explícita de reservas.
- Cola local con reservas, límite de concurrencia configurable y liberación automática de reservas caducadas según `reservation_ttl_hours`, además de un tablero HTML local con recarga periódica.
- Tipos de rama `feature`, `fix`, `hotfix` y `chore`, con nombres derivados de la clave y el resumen.
- Reconocimiento de URL de Azure Repos. La skill de `/factory` contempla la consulta de Azure Boards mediante el conector ya disponible en Claude.
- Prueba de recorrido sintética con repositorio Azure SSH: 39 pruebas locales pasaron y `compileall` terminó correctamente en la última verificación registrada.
- Bloqueo por trabajo con `flock`, `O_NOFOLLOW` y permisos `0600`, y liberación de reservas caducadas al consultar la cola.

La implementación de Azure no equivale todavía a una validación contra la organización real: no se hicieron llamadas remotas ni se verificaron permisos corporativos.

## Pendientes de implementación

| Prioridad | Pendiente | Estado / alcance |
|---|---|---|
| Alta | Crear y verificar Pull Requests en Azure Repos | La publicación automatizada actual cubre GitHub mediante `gh`. Para Azure Repos, la creación y comprobación del PR sigue siendo manual. |
| Alta | Integrar Azure Pipelines | No hay consulta automatizada de ejecuciones, resultados, políticas de build ni estado requerido por el PR. Los Quality Gates locales no sustituyen esos controles del servidor. |
| Alta | Reforzar el aislamiento de agentes | Los gates deterministas se ejecutan aislados cuando el entorno lo permite, pero los agentes Claude Code no están confinados automáticamente a su worktree. Antes de ejecutar tareas no confiables o en paralelo, definir y verificar límites de escritura, procesos y secretos. |
| Media | Orquestar varios repositorios en una misma solicitud | La cola y el estado son locales a la fábrica/repositorio; no existe coordinación transaccional de un cambio que abarque varios repositorios. |
| Media | Telemetría de consumo por trabajo | No se guarda un registro uniforme de tokens/costo, proveedor, duración y resultado para comparar trabajos. |

## Pendientes de validación en el entorno real

- Probar el acceso del Claude corporativo a Azure Boards: organización, proyecto, área, permisos, tipos de work item y enlaces a repositorios. Resolver resultados ambiguos o inaccesibles sin asumir que la consulta fue exitosa.
- Confirmar el flujo corporativo de Azure Repos: ramas permitidas, políticas, revisores obligatorios, permisos de creación de PR y estrategia de merge. La fábrica no debe completar el merge sin aprobación humana.
- Ejecutar una prueba controlada de dos trabajos simultáneos para confirmar el límite de concurrencia y la reserva/liberación de la cola en el equipo donde se usará.
- Validar la recuperación de una reserva abandonada tras interrumpir el proceso. La reserva caduca a las `reservation_ttl_hours` (12 por defecto) y `devforge cola` informa las liberadas; confirmar el plazo adecuado para el equipo y que `liberar ID` siga disponible para el cierre manual.
- Revisar aislamiento y exposición de credenciales con los comandos reales de cada proyecto. No asumir que un worktree separa por sí solo los permisos o secretos del agente.

## Criterio para dar estos puntos por cerrados

- **Azure Boards:** consulta real autorizada, resultado trazable y manejo correcto de falta de permisos, ausencia y ambigüedad.
- **Azure Repos:** PR de prueba creado en un repositorio controlado, comprobación de rama base, políticas y estado; merge sujeto a decisión humana.
- **Azure Pipelines:** lectura verificable de ejecuciones y gates requeridos, con tratamiento explícito de fallo y ausencia de ejecución.
- **Aislamiento:** evidencia de que agentes y comandos solo pueden modificar el espacio previsto y no exponen credenciales; revisar también el comportamiento cuando la herramienta de aislamiento no está disponible.
- **Concurrencia y recuperación:** prueba reproducible de límite, exclusión de reservas duplicadas y recuperación documentada tras interrupción.
- **Multi-repositorio y telemetría:** contrato funcional y pruebas antes de presentar esas capacidades como soportadas.

## Restricciones operativas vigentes

- No se han realizado operaciones remotas en Azure DevOps o GitHub durante esta revisión.
- No se ha creado ningún Pull Request ni ejecutado un pipeline.
- La aprobación humana sigue siendo necesaria para publicar/mergear cambios.
- No se requiere un sistema de perfiles para el diseño actual.
