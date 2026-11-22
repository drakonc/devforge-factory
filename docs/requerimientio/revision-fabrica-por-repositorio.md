# Decisión de diseño posterior al análisis inicial

V1 recibe una funcionalidad escrita en Claude y guarda los informes de agentes en Markdown. Su sesión coordina un trabajo con worktree y revisiones de código, seguridad, UI y UX. [README de V1](https://github.com/zazencodes/zazencodes-season-3/blob/main/src/software-factory-claude-code/README.md)

V2 incorpora una cola de issues con etiqueta, admisión, selección de revisores y gates ejecutables antes de revisar. La persistencia permite continuar un trabajo y la salida se gestiona mediante PR. [Diseño de V2](https://github.com/zazencodes/zazencodes-season-3/blob/main/src/software-factory-claude-code-v2/DESIGN.md)

DevForge conserva la entrada directa de V1 y la admisión y los gates de V2. El usuario selecciona una issue abierta del repositorio actual, un requerimiento del Jira indicado, un documento de docs o una solicitud escrita. No hace falta etiquetar issues ni elegir entre Work y Personal. Un conjunto de agentes Markdown atiende todos los orígenes. La publicación requiere aprobación humana. El documento inicial se conserva como antecedente.

## Resultado frente a las brechas de la comparativa

| Brecha identificada | Resultado de esta iteración | Evidencia local |
| --- | --- | --- |
| Cierre | Revisión a terminado con decisión y confirmación para el commit vigente | test_delivery_flow y test_lifecycle |
| Rondas | Archivo round-N, rework y escalamiento al agotar el presupuesto de rondas | test_lifecycle |
| Cola y concurrencia | Reservas persistentes con límite por repositorio y bloqueo entre procesos | test_board |
| Dashboard | Instantánea HTML privada regenerable sin servicio web | test_board |
| Ramas | feature, fix, hotfix y chore | test_board y test_delivery_flow |
| Multi-repositorio | Cada repositorio mantiene su cola independiente. No hay coordinador entre repositorios. | Pendiente |

La comparación anterior estima paridad global sin definir pesos. Medimos cinco brechas con implementación y pruebas locales sobre las seis priorizadas. La ejecución de agentes concurrentes en Claude y la lectura autenticada de Azure Boards aún requieren validación en la sesión corporativa. Coste por trabajo, PR de Azure y resultados de Azure Pipelines siguen fuera de la cobertura comprobada.
