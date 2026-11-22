
https://github.com/zazencodes/zazencodes-season-3/tree/main/src/software-factory-claude-code


https://github.com/zazencodes/zazencodes-season-3/tree/main/src/software-factory-claude-code-v2


esos dos repositorios son dos fabricas de software que encontre quiero que me las explique prim,erp la q desspues la V2 y finalmente cual es la diferencia

Análisis técnico: Software Factory V1 vs V2 de ZazenCodes
He revisado ambas implementaciones del repositorio de ZazenCodes. Aunque están dentro del mismo repositorio de GitHub, representan dos arquitecturas distintas para automatizar el desarrollo de software utilizando Claude Code como orquestador y subagentes especializados como ejecutores.

La diferencia fundamental es esta:

V1: automatiza el desarrollo de una funcionalidad desde su descripción hasta la revisión y aprobación del código.

V2: convierte GitHub Issues en una cola de trabajo, controla tareas concurrentes, ejecuta validaciones automáticas y gestiona la entrega mediante Pull Requests.

Ambas utilizan Claude Code, agentes, Git y archivos Markdown para conservar el contexto y los resultados.

Evolución de la arquitectura

V1

Fábrica basada en funcionalidades

Solicitud manual

Especificación + código

4 revisores

Aprobación + merge

V2

Fábrica basada en Issues

Cola de GitHub Issues

Intake + planificación

Código + pruebas + revisión selectiva

Pull Request + merge

1. Software Factory V1: cómo funciona
Ver código fuente de la V1
1.1. Concepto
La V1 es una fábrica pequeña que convierte a Claude Code en un coordinador de siete subagentes.

El desarrollador describe lo que necesita y ejecuta:

/factory Implementar autenticación JWT

Claude organiza el trabajo, genera una especificación, escribe código, solicita cuatro revisiones independientes y decide si puede integrarlo o necesita intervención humana.

1.2. Los siete agentes
Agente

Modelo

Responsabilidad

spec-writer

Opus

Generar la especificación y criterios de aceptación

builder

Opus

Implementar código y realizar commits

reviewer-security

Opus

Revisar vulnerabilidades y seguridad

reviewer-ux

Sonnet

Evaluar experiencia de usuario

reviewer-ui

Sonnet

Revisar interfaz visual

reviewer-code

Sonnet

Evaluar calidad y corrección del código

approver

Opus

Decidir aprobación o escalamiento

Es importante entender que Claude orquestador no es uno de esos siete agentes. Es la sesión principal que ejecuta /factory, administra el proceso y se comunica con los subagentes.

1.3. Flujo de ejecución
Solicitud /factory

El usuario describe la funcionalidad
Spec Writer

Genera spec.md
Builder

Desarrolla en su rama aislada
Cuatro revisiones en paralelo

Security

UX

UI

Code

CHANGES: volver al Builder

Approver

Evalúa el resultado final
APPROVE

Merge a main
ESCALATE

Revisión humana
Ejemplo práctico con .NET:

Supongamos que solicitas implementar un endpoint para registrar pacientes en ASP.NET Core.

El spec-writer define el contrato HTTP, validaciones, reglas de negocio y criterios de aceptación. El builder implementa los controladores, servicios, persistencia y pruebas. Después, los cuatro revisores inspeccionan el resultado en paralelo.

Si reviewer-security identifica una vulnerabilidad, responde VERDICT: CHANGES. El orquestador espera los cuatro dictámenes y devuelve las observaciones al mismo builder, que corrige y genera una nueva ronda.

Si todos responden PASS, el approver determina si fusionar automáticamente o solicitar revisión humana. El ciclo de revisión tiene límites para evitar correcciones indefinidas.

1.4. Estructura y persistencia
.claude/
├── skills/
│   └── factory/
│       └── SKILL.md
└── agents/
    ├── spec-writer.md
    ├── builder.md
    ├── reviewer-security.md
    ├── reviewer-ux.md
    ├── reviewer-ui.md
    ├── reviewer-code.md
    └── approver.md

factory/
├── backlog.md
├── dashboard.html
└── jobs/
    └── 001-mi-funcionalidad/
        ├── job.json
        ├── spec.md
        ├── build.md
        ├── round-1/
        │   ├── review-security.md
        │   ├── review-ux.md
        │   ├── review-ui.md
        │   └── review-code.md
        └── decision.md
El detalle más importante es job.json: representa el estado de una ejecución. Los Markdown almacenan los entregables y permiten que los agentes intercambien información sin depender exclusivamente del contexto conversacional.

Cada trabajo dispone de su propio Git worktree y rama factory/<job-id>, lo que permite abrir varias sesiones de Claude Code y ejecutar funcionalidades independientes.

1.5. Comandos
/factory <feature>
/factory next
/factory approve <job-id>
/factory rework <job-id> <nota>

El dashboard HTML permite observar trabajos, etapas, revisiones y decisiones. Se ejecuta localmente mediante:

cd factory
python3 -m http.server

Dirección: http://localhost:8000/dashboard.html.

Fortalezas de la V1: es fácil de entender, implementar y personalizar. Resulta especialmente adecuada para aprender orquestación de subagentes, ejecutar funcionalidades individuales y experimentar con revisión automática.

Limitaciones: utiliza los cuatro revisores incluso para cambios sencillos, no tiene una puerta obligatoria de validaciones deterministas equivalente a la V2 y el merge se realiza localmente. Esto aumenta el consumo y puede generar conflictos en el checkout principal.

Un detalle del repositorio: BUILD_PROMPT.md describe la versión inicial, que usaba board.json. La implementación publicada evolucionó a un job.json independiente por trabajo, por lo que el README representa mejor el comportamiento actual de V1.

2. Software Factory V2: cómo funciona
Ver código fuente de la V2
2.1. Concepto
La V2 transforma la fábrica en un sistema de procesamiento de tareas, utilizando GitHub como herramienta de entrada y de entrega.

Ya no necesitas abrir una sesión independiente por cada funcionalidad.

En lugar de eso:

Creas un GitHub Issue.

Le asignas la etiqueta factory.

Ejecutas /factory run.

Claude procesa las tareas pendientes, respetando el límite de concurrencia.

Cada tarea produce su propio Pull Request.

La fábrica puede aprobar y fusionar el PR automáticamente o solicitar tu intervención.

Esta versión introduce controles deterministas: no depende únicamente de que otro modelo de IA considere que el código está correcto.

2.2. Los ocho agentes
Agente

Modelo

Función

intake

Fable

Analiza si la solicitud debe desarrollarse y evalúa el riesgo

spec-writer

Opus

Define especificaciones y criterios de aceptación

builder

Opus

Desarrolla, realiza commits y abre el PR

reviewer-code

Haiku / Sonnet

Revisa código según el riesgo

reviewer-security

Opus

Revisa seguridad cuando se requiere

reviewer-ux

Sonnet

Evalúa experiencia de usuario en cambios de UI

reviewer-ui

Haiku

Evalúa diseño visual en cambios de UI

approver

Opus

Aprueba o solicita intervención humana

La novedad principal es el agente intake, que realiza la clasificación inicial.

Los revisores también cambian: no se ejecutan todos obligatoriamente. Su participación depende del riesgo y del área afectada.

2.3. Flujo de ejecución de la V2
GitHub Issues

Solicitudes con etiqueta factory
Intake (Fable)

ACCEPT / NEEDS-INFO / REJECT
Route + Spec Writer

Selecciona revisores y genera la especificación
Builder

Implementa y abre un Draft PR
Quality Gate

Tests, lint, typecheck y build
Si falla, vuelve al Builder sin ejecutar revisores

Revisores seleccionados

Solo los necesarios según riesgo y superficie
Approver

Decide APPROVE o ESCALATE
PR Merge

Validación final
Revisión humana

PR pendiente
2.4. El motor de la V2: Scripts + agentes
Esta es una decisión arquitectónica importante.

En la V1, el propio orquestador actualizaba job.json y tomaba decisiones operativas sobre el flujo.

En la V2 hay una separación de responsabilidades:

Claude Code: coordina agentes.

Agentes: generan código, especificaciones y evaluaciones.

Scripts: ejecutan acciones deterministas, validaciones y transiciones de estado.

La V2 incorpora tres scripts principales:

Script

Responsabilidad

factory/bin/job

Controla estados, cola de tareas, feedback y merge

factory/bin/gate

Ejecuta validaciones técnicas

factory/bin/route

Selecciona revisores y modelos

Por ejemplo, si Claude intenta mover una tarea desde build hasta approve saltándose las pruebas, factory/bin/job debe rechazar esa transición.

Esto es más robusto que confiar exclusivamente en instrucciones escritas en el prompt.

2.5. Ejecución paralela
La V2 permite configurar cuántas tareas se ejecutan simultáneamente.

En su archivo factory/config.json encontramos:

{
  "concurrency": 3,
  "max_rounds": 3,
  "base_branch": "main",
  "merge_method": "merge"
}

Significa que un mismo orquestador puede gestionar hasta tres trabajos activos. Cada uno tiene su worktree, rama y archivos de estado.

Ejemplo conceptual con tres Issues

Issue #10

JWT

Build
Issue #11

Pacientes

Review
Issue #12

Auditoría

Gate
Un único orquestador supervisa los tres trabajos

Claude Code /factory run

La fábrica puede iniciar otros trabajos cuando se liberan espacios.

Importante: concurrency: 3 representa trabajos concurrentes, no necesariamente tres agentes activos. Cada trabajo puede tener varios subagentes y algunos revisores funcionan en paralelo.

2.6. Routing: optimización de modelos
Otra evolución relevante es que la V2 asigna modelos de revisión según el riesgo.

La configuración real establece:

Condición

Revisor

Modelo

Riesgo bajo

Code

Haiku

Riesgo medio

Code

Sonnet

Riesgo alto

Code

Sonnet

Cambio de interfaz

UX + UI

Sonnet + Haiku

Superficie de seguridad

Security

Opus

El builder continúa utilizando Opus.

Por ejemplo, cambiar el texto de un botón podría requerir únicamente un revisor de código económico y dos revisores de interfaz, mientras que modificar una autenticación podría activar revisión de seguridad con Opus.

Este enfoque reduce llamadas innecesarias a modelos costosos, aunque la clasificación inicial también tiene su propio consumo.

2.7. Quality Gate: validación real
El archivo factory/checks.sh representa el contrato de calidad de cada repositorio.

En un proyecto .NET, una configuración adaptada podría ejecutar:

#!/usr/bin/env bash
set -euo pipefail

dotnet restore
dotnet build --no-restore
dotnet test --no-build

Esto es un ejemplo para tu stack, no el contenido predeterminado del repositorio.

La V2 no permite pasar a revisión mientras estas validaciones fallen. También ejecuta de nuevo el gate después de sincronizar la rama con main, antes del merge.

El sistema protege sus propios archivos de configuración y validación frente a modificaciones del trabajo que se está evaluando.

Es una mejora importante porque la aprobación ya no depende solamente de opiniones de los revisores.

2.8. Recuperación y seguimiento
La V2 conserva el estado de cada trabajo en factory/jobs/<job-id>/.

Si cierras la sesión de Claude Code, puedes volver a ejecutar:

/factory run

La fábrica intenta recuperar los trabajos pendientes a partir de sus estados y archivos.

El dashboard también evoluciona: muestra Issues, Pull Requests, resultados del gate, revisiones, riesgo, duración y estimación del consumo por agente.

La estimación económica utiliza información de los transcripts de Claude Code y precios equivalentes de API. No representa necesariamente lo que pagas en una suscripción; además, no incluye todo el consumo del orquestador.

2.9. Instalación de la V2
La propia documentación propone darle a Claude Code esta instrucción:

Install this software factory in this project from
the reference repository:

https://github.com/zazencodes/zazencodes-season-3/tree/main/src/software-factory-claude-code-v2
Claude debe seguir INSTALL.md, copiar los componentes, adaptar checks.sh, configurar los agentes e instalar las etiquetas necesarias en GitHub.

Requisitos documentados: Claude Code 2.1.257 o posterior, Python 3.10 o posterior y GitHub CLI (gh) autenticado con permisos suficientes.

No es un servicio que permanezca activo permanentemente. La fábrica se ejecuta localmente cuando lanzas /factory run; crear un Issue por sí solo no inicia el desarrollo.

3. Diferencias entre V1 y V2
Característica

V1

V2

Entrada de solicitudes

Prompt o backlog.md

GitHub Issues

Orquestación

Una sesión por trabajo

Una sesión para múltiples trabajos

Agentes especializados

7

8

Clasificación inicial

No existe intake

Intake con Fable

Paralelismo de trabajos

Varias sesiones

Un orquestador con concurrencia

Selección de revisores

Los cuatro siempre

Según riesgo y superficie

Validaciones automáticas obligatorias

Sin gate dedicado

checks.sh + gate

Transiciones de estado

Controladas por Claude

Controladas por script

Integración con GitHub

Ramas y merge local

Issues, PR y merge remoto

Recuperación tras interrupción

Limitada

Recuperación explícita por estado

Seguimiento de consumo

No incorporado

Estimación por trabajo

Instalación

Copia y adaptación manual

Guía para instalación por agente

Licencia en la carpeta

Sin licencia específica

GPLv3 y opción comercial

¿Cuál es más eficiente económicamente?
Para visualizarlo, podemos comparar un escenario hipotético: una tarea que supera todas las validaciones en la primera ronda, sin reintentos.

Cantidad de invocaciones de agentes por trabajo

0
3
6
9
V1, cualquier tarea
V2, riesgo bajo
V2, cambio de UI
V2, UI + seguridad
V1, cualquier tarea: Invocaciones 7
V2, riesgo bajo: Invocaciones 5
V2, cambio de UI: Invocaciones 7
V2, UI + seguridad: Invocaciones 8
Ejemplo sin reintentos: se incluyen intake, especificación, builder, revisores y approver.

Menos invocaciones no garantiza menor costo: los modelos, tokens, contexto y reintentos afectan el consumo.
La V2 no siempre ejecuta menos agentes que la V1. Su ventaja es que utiliza modelos y revisores de forma selectiva y evita gastar revisiones cuando el código ni siquiera pasa las pruebas.

4. ¿Cuál elegiría para una fábrica de software propia?
Dado tu objetivo de crear una plataforma modular de desarrollo con subagentes, utilizaría la V2 como base arquitectónica, pero no la copiaría sin modificaciones.

Su separación entre orquestación, máquinas de estado, ejecución y validación es mucho más apropiada para evolucionar hacia una fábrica que trabaje con múltiples tecnologías y proveedores de modelos.

Además, en tu escenario actual, donde quieres que Claude planifique y otros agentes puedan encargarse del desarrollo, hay una limitación que debes tener en cuenta:

Ninguna de estas dos implementaciones incorpora de forma nativa una capa universal para ejecutar OpenCode, Codex, Pi u otros runtimes. Están diseñadas alrededor del sistema de subagentes de Claude Code.

Para convertir la V2 en una fábrica modular, propondría esta evolución:

Orquestador

Claude Code — planificación, dependencias y asignación
Task Scheduler + State Machine

Cola, prioridades, dependencias y recuperación
Executor Adapter Layer

Interfaz común para ejecutar tareas
Claude Code

OpenCode

Codex / Pi

Quality Gates + Code Review

Tests, seguridad, arquitectura, rendimiento y PR
Esta capa adicional permitiría asignar tareas a diferentes ejecutores sin acoplar toda la fábrica a un único proveedor. Sería una ampliación propia, no una capacidad ya implementada en ZazenCodes.

También incorporaría políticas más estrictas de aprobación para cambios de bases de datos, autenticación, infraestructura y despliegues, especialmente en aplicaciones empresariales.

Un punto legal: la V2 incluye licencia GPLv3. Si vas a distribuir una versión derivada como producto propietario, conviene revisar sus obligaciones y la opción de licencia comercial que menciona el autor.

5. Conclusión
V1 para aprender el patrón

Es una buena referencia para entender cómo Claude Code coordina un builder, varios revisores y un aprobador mediante archivos.

V2 para construir una plataforma más robusta

Ofrece mejores mecanismos de control, integración con GitHub, recuperación de trabajos, validaciones y gestión de concurrencia.

Para tu fábrica de software, el camino que considero más sólido es partir de los principios de la V2, conservar su pipeline de calidad y desacoplar la ejecución de los agentes mediante adaptadores. Eso permitiría evolucionar de una fábrica exclusiva para Claude Code hacia un sistema multiagente y multimodelo.

Fuentes principales: README V1, Diseño técnico y cambios de V2, Instalación V2.

Este análisis corresponde a los archivos publicados, no a una prueba ejecutada de ambas fábricas.

en mi trabajo usamos jira cada jira puede llegar a ser un desarrolo y las ramas se sacan de develop secrea el feature fix hotfix /codigo-jira-nombre de la rama eso a nivel de trabajo que tengo clade max no necesito otros harneces

a nivel personal estoy manejando Isues o requerimientos intenros uso claude pro  y los codigos se los paso a opencode o codex 


como puedo adaptar en una sola vercion las factory una para mi trabajo otra para mi personal
DevForge Factory: una arquitectura, dos modos de operación
Mi propuesta es construir una sola fábrica de software reutilizable, basada principalmente en ZazenCodes V2, incorporando algunos elementos de V1, pero con dos perfiles completamente independientes:

Work Factory: Jira + Claude Max, con Claude Code como orquestador y ejecutor mediante subagentes. Ramas basadas en develop.

Personal Factory: GitHub Issues o requerimientos internos + Claude Pro como orquestador + OpenCode y Codex como ejecutores. Ramas configurables según cada proyecto.

No construiría dos fábricas independientes porque duplicarías la lógica de planificación, control de estados, validación, revisión y seguimiento. La diferencia debe estar en los adaptadores y las políticas de ejecución.

DevForge Factory
Núcleo único de orquestación

Intake · Planner · Scheduler · Builder · QA · Review · Delivery

Trabajo

Jira

Claude Max

Orquestador
Claude Code

Subagentes ejecutores
feature/fix/hotfix → develop

Personal

Issues / Backlog

Claude Pro

Orquestador
OpenCode

Codex

Pull Request → rama base

1. Qué conservaría de las dos versiones
Componente

Origen

Adaptación

spec-writer

V1 / V2

Especificaciones y criterios de aceptación

builder

V1 / V2

Ejecutores intercambiables

Revisores especializados

V1 / V2

Seguridad, código, arquitectura, UI, UX

Intake y clasificación

V2

Analizar Jira, Issues o tareas internas

Scripts de estado

V2

Una máquina de estados común

checks.sh

V2

Validaciones adaptadas al stack

Worktrees

V1 / V2

Aislamiento de cada desarrollo

Dashboard

V2

Mostrar los dos perfiles por separado

Recuperación de trabajos

V2

Reanudar después de cerrar sesión

Routing de modelos

V2

Routing de modelos y de ejecutores

Correcciones iterativas

V1 / V2

Reintentos limitados y trazables

La pieza que reemplazaría completamente es el mecanismo que ejecuta al builder: en vez de invocar obligatoriamente un subagente de Claude, usaríamos un Executor Adapter.

Esto permite trabajar con Claude Code en el entorno empresarial y con OpenCode o Codex en el personal sin duplicar el pipeline.

2. Perfil empresarial: Work Factory
En tu trabajo, el requerimiento nace en Jira y el desarrollo debe ajustarse al flujo de ramas del equipo. Por tanto, Jira debe ser la fuente oficial de tareas y Git debe seguir las convenciones de la empresa.

Flujo empresarial propuesto
1. Jira

Leer código, descripción, prioridad y criterios
2. Intake + Architect

Clasificar el cambio y sus dependencias
3. Git Branch

Crear worktree desde develop
4. Claude Builder

Implementar funcionalidad
5. Quality Gate + Review

Compilar, probar, revisar seguridad
6. Pull Request

Dirigido a develop, con aprobación humana
Convención obligatoria de ramas
La fábrica generaría el nombre utilizando el identificador de Jira y el tipo de desarrollo.

Tipo

Rama de ejemplo

Funcionalidad

feature/EVR-1234-agendamiento-pacientes

Corrección

fix/EVR-1235-validacion-documento

Hotfix

hotfix/EVR-1236-error-autenticacion

El patrón sería:

{tipo}/{JIRA-KEY}-{descripcion-kebab-case}
Por defecto, la rama parte de origin/develop y el PR apunta a develop.

Para los hotfix, dejaría una excepción configurable por repositorio, porque algunas empresas los crean desde la rama de producción y posteriormente los integran en develop. No asumiría esa excepción sin que esté definida en el proyecto.

Comandos del perfil Work
/factory run EVR-1234
/factory queue
/factory status EVR-1234
/factory review EVR-1234
/factory retry EVR-1234

Estos serían comandos de la fábrica que vamos a construir; no son comandos existentes en ZazenCodes.

Al ejecutar /factory run EVR-1234:

Consulta el Jira y sus criterios de aceptación.

Detecta el repositorio que corresponde a la solicitud.

Propone un plan y crea la rama desde develop.

Ejecuta Claude Code como desarrollador.

Corre pruebas y revisores.

Crea el PR y registra su enlace en Jira.

Deja el resultado pendiente de aprobación cuando corresponda.

Jira Cloud ofrece una API para buscar Issues mediante JQL y consultar sus transiciones de estado. El adaptador podría usar esas operaciones, sujeto a los permisos y a la versión de Jira de tu empresa. 

developer.atlassian.com
+1

Política de ejecución empresarial
Dado que tienes Claude Max, no incluiría OpenCode ni Codex en este perfil.

Utilizaría agentes de Claude Code para planificación, arquitectura, desarrollo, QA, seguridad y aprobación técnica. Los modelos específicos quedarían configurables.

Regla fundamental: para cambios empresariales, la fábrica nunca debería desplegar ni fusionar automáticamente a ramas protegidas sin la autorización establecida por tu equipo. El approver evalúa la calidad técnica, pero la aprobación organizacional sigue siendo humana.

3. Perfil personal: Personal Factory
Aquí cambia la distribución de responsabilidades.

Claude Pro debe concentrarse en lo que aporta más valor: comprender requisitos, planificar, asignar, supervisar resultados y decidir si se alcanzaron los criterios de aceptación.

OpenCode y Codex realizan la mayor parte del desarrollo.

Flujo personal propuesto
GitHub Issues / Backlog interno

Una solicitud puede convertirse en uno o varios trabajos
Claude Pro — Planner

Analiza, divide tareas y detecta dependencias
OpenCode

Executor A
Worktree A

Codex

Executor B
Worktree B

Quality Gate

Tests + build + seguridad + revisión
Claude Pro — Evaluación final

Aprueba, solicita correcciones o escala
Pull Request

Integración y cierre del requerimiento
Distribución inteligente de tareas
En lugar de asignar aleatoriamente los trabajos, crearía un componente TaskScheduler.

Por ejemplo, si un Issue requiere desarrollar un módulo de gestión de pacientes:

Tarea

Puntos

Ejecutor

Crear entidades y migraciones

3

OpenCode

Implementar API REST

5

Codex

Crear componentes Angular

5

OpenCode

Implementar pruebas de integración

3

Codex

Con esta planificación, cada ejecutor acumularía 8 puntos de complejidad.

El reparto seguiría una distribución objetivo del 50 % para OpenCode y 50 % para Codex, medida por complejidad asignada y no por número de tareas. También debe considerar dependencias, disponibilidad y errores.

Si una tarea depende de otra, no se ejecuta hasta que su predecesora esté lista.

Para evitar conflictos Git, cada tarea trabajaría en su propio worktree. La fábrica integraría los resultados de forma controlada en la rama del requerimiento antes de ejecutar las validaciones finales.

Esto último es importante: una funcionalidad repartida entre dos ejecutores no debería terminar con dos cambios independientes integrados sin una validación conjunta.

Cómo reducir el consumo de Claude Pro
Implementaría estas reglas:

Claude genera el plan una vez y lo persiste en archivos.

OpenCode y Codex leen directamente las especificaciones; no requieren que Claude les repita el contexto continuamente.

Los resultados se comunican mediante JSON y Markdown resumidos.

Los scripts ejecutan builds, tests y verificaciones de estado.

Claude interviene cuando hay decisiones, bloqueos, cambios de alcance o aprobación final.

Con este diseño se intenta reservar el consumo de Claude Pro para coordinación y razonamiento, aunque el ahorro real dependerá de los límites de tus planes y la frecuencia de las ejecuciones.

4. Arquitectura de carpetas de la fábrica unificada
Propongo separar el núcleo de las configuraciones por perfil:

devforge-factory/
│
├── core/
│   ├── orchestrator/
│   ├── scheduler/
│   ├── state-machine/
│   ├── workflow/
│   ├── quality-gates/
│   └── cost-tracker/
│
├── adapters/
│   ├── sources/
│   │   ├── jira/
│   │   ├── github-issues/
│   │   └── internal-backlog/
│   │
│   ├── executors/
│   │   ├── claude-code/
│   │   ├── opencode/
│   │   └── codex/
│   │
│   └── git/
│       ├── branches/
│       ├── worktrees/
│       └── pull-requests/
│
├── agents/
│   ├── intake.md
│   ├── architect.md
│   ├── spec-writer.md
│   ├── builder.md
│   ├── code-reviewer.md
│   ├── security-reviewer.md
│   ├── qa.md
│   └── approver.md
│
├── profiles/
│   ├── work.yaml
│   └── personal.yaml
│
├── projects/
│   └── registry.yaml
│
├── runtime/
│   ├── jobs/
│   ├── logs/
│   └── worktrees/
│
└── dashboard/
Esto es una estructura objetivo para tu implementación, no la estructura original de ZazenCodes.

5. Configuración: Work y Personal
El punto más importante es que los perfiles deben poder cambiarse sin modificar el núcleo.

Explorador de perfiles

Trabajo
Personal
profiles/work.yaml


profile: work

source:
  provider: jira
  selection: explicit

executor:
  provider: claude-code
  concurrency: 2

git:
  base_branch: develop
  target_branch: develop
  branch_pattern: "{type}/{key}-{slug}"
  allowed_types:
    - feature
    - fix
    - hotfix
  auto_merge: false

quality:
  require_build: true
  require_tests: true
  require_code_review: true
  require_security_review: true
  require_human_approval: true
      

Configuraciones iniciales sugeridas. Los valores de concurrencia son límites de diseño, no garantías de capacidad de las suscripciones.
La rama base del perfil personal sería configurable por proyecto, en lugar de asumir siempre main.

También separaría las credenciales de Jira, GitHub y los proveedores de IA. No deben almacenarse directamente en estos YAML.

6. Contratos de integración entre componentes
Para mantener la fábrica independiente de los proveedores, establecería tres contratos principales.

Ejemplo conceptual en TypeScript

interface WorkItemSource {
  get(id: string): Promise<WorkItem>;
  listReady(): Promise<WorkItem[]>;
  updateStatus(id: string, status: string): Promise<void>;
  addComment(id: string, comment: string): Promise<void>;
}

interface AgentExecutor {
  execute(task: AgentTask): Promise<ExecutionResult>;
  resume(taskId: string): Promise<ExecutionResult>;
  cancel(taskId: string): Promise<void>;
}

interface QualityGate {
  validate(worktree: string): Promise<GateResult>;
}

Con estos contratos:

JiraSource y GitHubIssueSource implementan WorkItemSource.

ClaudeCodeExecutor, OpenCodeExecutor y CodexExecutor implementan AgentExecutor.

Las verificaciones para .NET, Angular, Node o Python implementan QualityGate.

El orquestador trabaja con interfaces, no con implementaciones concretas.

Una consideración: OpenCode y Codex son procesos externos, no subagentes nativos de Claude Code. Sus adaptadores deberán ocuparse de invocarlos, capturar resultados, gestionar errores y recuperar ejecuciones. No basta con cambiar el nombre del modelo dentro del archivo Markdown de un agente.

7. Dashboard unificado
Mantendría la idea del dashboard de ZazenCodes V2, añadiendo una vista independiente por perfil.

DevForge Dashboard

Vista conceptual
Work Factory
Personal Factory
Trabajos

3
Activos

2
Pendientes

1
Trabajo

Ejecutor

Estado

EVR-1234

Agendamiento

Claude Code

En desarrollo

EVR-1235

Corrección de validación

Claude Code

En QA

EVR-1236

Integración API

Sin asignar

Pendiente

Datos ilustrativos, no conectados a Jira ni GitHub.
Además de los estados, incluiría historial de reintentos, evidencia de pruebas, ramas, enlaces de PR, consumo estimado y agente responsable de cada tarea.

8. Cómo organizaría la implementación
No intentaría construir todo simultáneamente. Dividiría el desarrollo en cuatro etapas.

1
Núcleo compartido

Partir de la V2: máquina de estados, jobs, worktrees, quality gates, recuperación y dashboard. Separar las políticas y los adaptadores del pipeline.

2
Work Factory

Integración Jira, resolución de repositorios, nomenclatura de ramas, Claude Code como ejecutor y PR contra develop. Validar primero con un Jira de prueba.

3
Personal Factory

Integrar GitHub Issues y backlog interno; implementar los adaptadores OpenCode y Codex, el balanceo por puntos y la integración de sus resultados.

4
Endurecimiento

Dashboard, políticas de permisos, observabilidad, pruebas de recuperación, detección de conflictos Git y controles de seguridad.

9. Dos decisiones arquitectónicas que considero imprescindibles
Primera: separar físicamente los entornos de trabajo y personal. Aunque compartan el mismo código de fábrica, no deberían compartir historiales, credenciales, registros de tareas ni almacenamiento de contexto. Para proteger el código y los datos de tu empresa, recomiendo mantener también instalaciones y directorios de ejecución separados. Revisa la política corporativa antes de permitir que agentes procesen información privada.

Segunda: contemplar que un Jira puede abarcar varios repositorios. En una aplicación con API .NET, Angular y otros servicios, un solo requerimiento puede implicar varias ramas y varios Pull Requests. El núcleo debe representar un requerimiento padre con tareas y entregables por repositorio, sin asumir que siempre habrá un único PR.

Por ejemplo:

Jira EVR-1234
│
├── api-everest
│   └── feature/EVR-1234-agendamiento
│
├── mf-everest
│   └── feature/EVR-1234-agendamiento
│
└── menu-frontend
    └── feature/EVR-1234-agendamiento
Cada repositorio mantiene su propio worktree y validaciones. El requerimiento solo se considera técnicamente terminado cuando todos los entregables requeridos han pasado sus controles.

Recomendación final
Para tu caso, construiría DevForge Factory como núcleo común, con dos instalaciones y dos perfiles, reutilizando la lógica de la V2 pero permitiendo sustituir tanto la fuente de requerimientos como el ejecutor.

No necesitas una segunda plataforma de agentes en el trabajo. Y en lo personal no necesitas gastar Claude Pro implementando tareas que OpenCode y Codex pueden ejecutar.

El principal valor de esta arquitectura es que podrás mejorar el proceso de desarrollo una sola vez —por ejemplo, incorporando un mejor control de seguridad o una nueva estrategia de QA— y aprovechar esa mejora en ambos perfiles, sin mezclar los entornos ni sus políticas.

de echo Work Factory puede venir tambien de documentacion o peticiones
Perfecto. Entonces Work Factory no debe depender exclusivamente de Jira. Jira será una de las fuentes de entrada, pero también podrá recibir documentación, solicitudes directas y requerimientos que todavía no tengan un ticket creado.

Esto cambia un elemento importante de la arquitectura: necesitamos un módulo de ingesta y normalización de requerimientos (Requirement Intake), independiente de la fuente.

1. Arquitectura actualizada de Work Factory
Fuentes de requerimientos
Jira

Tickets existentes
Documentación

PDF, Word, Markdown
Petición directa

Instrucciones en lenguaje natural
Correo / Solicitud

Requerimientos recibidos
Requirement Intake

Extraer, normalizar y validar requerimientos
Claude Max — Orchestrator

Analizar, planificar, clasificar y delegar
Claude Code — Subagentes

Architect · Builder · QA · Security · Reviewer
Quality Gate + Git Workflow

Validación, ramas, Pull Requests y aprobación
2. ¿Cómo funcionaría cada entrada?
Origen

Ejemplo

Comportamiento

Jira

EVR-1234

Consulta Jira y extrae los criterios

Documentación

requerimientos.pdf

Analiza el documento, identifica funcionalidades y dependencias

Petición directa

«Implementa auditoría de usuarios»

Convierte la instrucción en una especificación

Correo

Solicitud de un cliente

Extrae el alcance y los requisitos

Varios orígenes

Jira + documento adjunto

Consolida las fuentes sin duplicar requerimientos

Una diferencia importante: no todas las solicitudes deben convertirse automáticamente en desarrollos.

Un documento podría contener diez funcionalidades. El agente intake debe poder generar diez unidades de trabajo, identificar dependencias y presentar el plan antes de ejecutar.

3. ¿Qué pasa con las ramas cuando no existe Jira?
Mantendría tu convención actual para los tickets de Jira:

feature/EVR-1234-agendamiento
fix/EVR-1235-validacion
hotfix/EVR-1236-autenticacion
Para solicitudes sin Jira, la fábrica asignaría un identificador interno persistente:

feature/REQ-0001-auditoria-usuarios
fix/REQ-0002-error-consulta
hotfix/REQ-0003-fallo-conexion
Cuando una solicitud adquiera posteriormente un Jira, se asociaría el código de Jira al requerimiento interno para mantener la trazabilidad. No renombraría automáticamente una rama que ya esté publicada.

4. Modelo unificado de requerimientos
Todos los orígenes deben transformarse en un mismo objeto de dominio:

interface Requirement {
  id: string;
  externalId?: string;

  source: "jira" | "document" | "prompt" | "email";

  title: string;
  description: string;

  type: "feature" | "fix" | "hotfix";

  acceptanceCriteria: string[];

  references: string[];
  dependencies: string[];

  repositories: string[];

  status:
    | "draft"
    | "needs-info"
    | "ready"
    | "in-progress"
    | "review"
    | "done"
    | "blocked";
}

Un requerimiento interno puede estar asociado a varios documentos, correos o tickets. Por eso, en la implementación definitiva, source y references evolucionarían a una colección de fuentes con sus identificadores y metadatos.

El identificador interno no debe depender de que Jira esté disponible.

5. Comandos propuestos
# Ejecutar un Jira
/factory run EVR-1234

# Procesar documentación
/factory import ./docs/requerimientos.pdf

# Solicitud directa
/factory create "Implementar auditoría de usuarios"

# Analizar requerimientos sin desarrollar todavía
/factory plan REQ-0001

# Procesar requerimientos aprobados
/factory run REQ-0001

# Consultar trabajos
/factory status

# Revisar cola de trabajo
/factory queue

Estos comandos serían parte de DevForge, no de la implementación original de ZazenCodes.

También añadiría un mecanismo para que una solicitud pueda entrar como simple consulta o análisis, sin crear una rama ni modificar código.

6. Arquitectura definitiva de los perfiles
Característica

Work Factory

Personal Factory

Orquestador

Claude Max

Claude Pro

Ejecutores

Subagentes Claude Code

OpenCode y Codex

Fuentes

Jira, documentos, peticiones, correo

GitHub Issues, documentos, peticiones internas

Identificador

Jira o REQ interno

Issue o REQ interno

Rama base

develop

Configurable

Rama de desarrollo

feature/fix/hotfix

Configurable

Arquitectura y planificación

Compartida

Compartida

QA y revisores

Compartidos

Compartidos

Máquina de estados

Compartida

Compartida

Aprobación

Según política empresarial

Según política personal

Mi recomendación adicional: separar Intake de Planning.

Intake recibe, interpreta y normaliza cualquier solicitud. Planning decide cómo resolverla, qué repositorios afecta, qué dependencias existen y cuántos agentes necesita.

Así, la fábrica no queda limitada a Jira ni obliga a ejecutar código por cada petición que recibe.

Hay una decisión funcional que sería especialmente importante para tu entorno laboral: cuando el requerimiento no venga de Jira, la fábrica debería poder trabajar con un identificador interno sin obligarte a crear un ticket, aunque también permitiría crear o vincular uno posteriormente cuando el proceso de la empresa lo requiera.

Una consideración: OpenCode y Codex son procesos externos, no subagentes nativos de Claude Code. Sus adaptadores deberán ocuparse de invocarlos, capturar resultados, gestionar errores y recuperar ejecuciones. No basta con cambiar el nombre del modelo dentro del archivo Markdown de un agente.  en el personal los ejecuto mediante herdr ellos on los sub agentes,


es necsario que los comandos sean sensillos y facil de recordar para mi+
Perfecto. Entonces ajustamos la arquitectura: en Personal Factory, Herd ya se encarga de ejecutar OpenCode y Codex como subagentes. No necesitamos construir adaptadores propios para lanzarlos, salvo que posteriormente encontremos alguna limitación específica de Herd.

Y simplificaremos los comandos para que uses prácticamente los mismos en Work Factory y Personal Factory.

1. Arquitectura corregida
DevForge Factory

Un único núcleo con dos perfiles
Work

Claude Max

Claude Code

Orquestador
Subagentes Claude

Personal

Claude Pro

Claude Code

Orquestador
Herd

Distribución y ejecución
OpenCode

Codex

La fábrica define qué hacer, cuándo hacerlo y cómo validar el resultado. Herd se encarga de la ejecución y distribución de tareas personales.

2. Comandos simplificados
Te propongo utilizar una sola entrada: /factory.

Comando

Funcionalidad

/factory

Mostrar panel, estado y opciones

/factory hacer

Crear o ejecutar un requerimiento

/factory plan

Analizar sin modificar código

/factory seguir

Continuar trabajos pendientes

/factory ver

Consultar trabajos y resultados

/factory revisar

Ejecutar QA y revisión técnica

/factory parar

Detener la ejecución de la fábrica

Solo necesitas recordar /factory. Los demás son accesos rápidos.

Ejemplos en Work Factory
/factory hacer EVR-1234
/factory hacer "Crear endpoint para pacientes"
/factory plan EVR-1234
/factory seguir

También podrás indicar un archivo directamente:

/factory hacer ./docs/requerimientos.md

Ejemplos en Personal Factory
/factory hacer 42
/factory hacer "Crear módulo de usuarios"
/factory plan 42
/factory seguir

Cuando ingresas un número, la fábrica lo interpreta según la fuente configurada para el perfil. En Personal, por ejemplo, puede representar el GitHub Issue #42.

Los comandos serían los mismos en ambos entornos. La fábrica identifica automáticamente su perfil a partir de la configuración del proyecto, por lo que no necesitas escribir work o personal constantemente.

3. Panel interactivo cuando ejecutas /factory
En vez de memorizar comandos, el comando principal podría presentar un menú en Claude Code:

DevForge Factory

Diseño propuesto

Hacer un requerimiento

Crear un plan

Continuar pendientes

Ver trabajos

Revisar código

Detener ejecución
Jira, Issue, ruta de documento o descripción
EVR-1234 o Crear módulo de pacientes
Este panel ilustra la experiencia que implementaría dentro de Claude Code. No está conectado a una fábrica instalada.
4. Reglas de funcionamiento
El comportamiento será automático:

Origen: la fábrica acepta Jira, Issues, archivos, instrucciones o documentación según el perfil.

Ramas: identifica el tipo de requerimiento y aplica las convenciones del proyecto.

Ejecución: Work utiliza subagentes Claude; Personal delega en Herd.

Validación: los dos perfiles comparten Quality Gates y revisores.

Recuperación: /factory seguir retoma trabajos pendientes sin repetir todo el análisis.

Seguridad: si una ejecución necesita aprobación humana, no realizará el merge automáticamente.

Para mantener la simplicidad, los comandos deberían aceptar también lenguaje natural:

/factory arregla el error de autenticación
/factory revisa el último desarrollo
/factory qué tengo pendiente

El orquestador interpretará la intención, pero confirmará las acciones ambiguas o con impacto significativo.

5. Decisión arquitectónica
La separación definitiva sería:

Responsabilidad

Work

Personal

Orquestación

Claude Code

Claude Code

Ejecución

Subagentes Claude

Herd → OpenCode / Codex

Distribución de carga

Claude

Herd

Seguimiento

DevForge

DevForge

Calidad

DevForge

DevForge

Git

DevForge

DevForge

Mi recomendación es conservar un solo comando principal, /factory, y cinco o seis acciones cortas. Todo lo demás —seleccionar modelos, distribuir trabajos, gestionar worktrees, ejecutar pruebas y generar Pull Requests— debe quedar automatizado.

Así evitas tener que aprender una herramienta diferente para cada entorno y mantienes la posibilidad de evolucionar la arquitectura sin modificar la interfaz que utilizas diariamente.

ese panel me gusta, tener n cuenta que en el personal esto Herd → OpenCode / Codex solo funciona si estoy en herdr
Perfecto. Entonces incorporamos una regla fundamental en DevForge Factory: la ejecución depende tanto del perfil como del entorno donde se inicia.

En Personal Factory, OpenCode y Codex solo estarán disponibles cuando Claude Code se esté ejecutando dentro de Herd. No asumiremos que Herd está disponible en cualquier sesión de Claude Code.

Comportamiento según el entorno
Perfil

Entorno

Ejecución

Work

Claude Code

Subagentes Claude

Personal

Claude Code + Herd activo

Herd → OpenCode / Codex

Personal

Claude Code sin Herd

Planificación disponible; ejecución delegada bloqueada

Personal

Herd instalado pero inactivo

Solicitar activación; no ejecutar automáticamente con Claude

En el perfil personal, no se cambiará silenciosamente a subagentes Claude si Herd no está disponible. Esto evita consumir innecesariamente tu suscripción Claude Pro.

Panel con detección del entorno
Esta sería la experiencia propuesta. Puedes cambiar el perfil y el estado de Herd para visualizar cómo reaccionaría el panel.

DevForge Factory
Panel de control
Prototipo
Perfil
Trabajo
Personal
Entorno Herd

Activo
Herd activo
Sin Herd
Simulación del detector de entorno. En la implementación real, el estado se obtendrá automáticamente.
OpenCode
Codex
Disponibles mediante Herd

¿Qué deseas hacer?


Hacer un requerimiento

Crear un plan

Continuar pendientes

Ver trabajos

Revisar código

Detener ejecución
Requerimiento, Issue, Jira o documento
Ej. Crear API de pacientes
Regla técnica para la implementación
El módulo EnvironmentDetector tendrá que distinguir entre Herd instalado, Herd activo y Herd integrado realmente con la sesión actual.

No basta con comprobar si existe un ejecutable de Herd en el sistema. La fábrica debe verificar que su mecanismo de delegación está disponible, preferentemente mediante una capacidad o comprobación oficial de Herd, antes de asignar trabajos.

La política sería:

personal:
  executor:
    provider: herd
    require_active_session: true
    agents:
      - opencode
      - codex

    fallback:
      provider: none
      on_unavailable: block_execution

  allow_without_herd:
    - plan
    - ver
    - revisar

En este esquema, revisar significa realizar una revisión de solo lectura con las herramientas disponibles; una revisión que requiera ejecutar agentes de Herd quedaría bloqueada.

Así mantienes un solo panel /factory, con detección automática del entorno y sin gastar Claude Pro en desarrollos que deberían realizar OpenCode o Codex.

no Personal

Claude Code sin Herd

Planificación disponible; ejecución delegada bloqueada si no esta en herder funciona igual que el work
Entendido. Corregimos la arquitectura: Personal Factory nunca bloquea la ejecución por no estar en Herd. Cuando Herd no está activo, funciona exactamente como Work Factory, utilizando subagentes nativos de Claude Code.

Comportamiento definitivo
Perfil

Entorno

Ejecutor

Work

Claude Code

Subagentes Claude Code

Personal

Claude Code con Herd

Herd → OpenCode / Codex

Personal

Claude Code sin Herd

Subagentes Claude Code

La selección será automática y transparente. No necesitas cambiar el perfil manualmente para elegir ejecutores.

Lógica de selección
/factory
¿Perfil?
Subagentes Claude Code
¿Herd activo en esta sesión?
Herd → OpenCode / Codex
Pipeline de desarrollo
Quality Gates + Review + PR
Work
Personal
Sí
No
Configuración actualizada
profiles:
  work:
    executor:
      default: claude-code

  personal:
    executor:
      default: claude-code
      when_herd_active: herd

      herd:
        agents:
          - opencode
          - codex

        balancing:
          strategy: complexity
          target:
            opencode: 50
            codex: 50

El panel /factory
Mantendremos el mismo panel interactivo que te gustó, con seis acciones sencillas: Hacer, Plan, Seguir, Ver, Revisar y Parar.

Lo único que cambia automáticamente es el motor de ejecución:

En Work muestra Claude Code.

En Personal con Herd muestra Herd · OpenCode + Codex.

En Personal sin Herd muestra Claude Code.

El resto del proceso permanece idéntico: ingesta de requerimientos, planificación, asignación, ramas, worktrees, pruebas, revisión y Pull Requests.

Esta será la regla definitiva de DevForge Factory: un solo núcleo, dos perfiles y selección automática de ejecutores según el entorno.

como digo que no esta activo when_herd_active: herd
Para indicar que Herd no está activo, puedes utilizar false. Sin embargo, te recomiendo separar la configuración de la detección automática.

Opción 1: Desactivar Herd manualmente
executor:
  default: claude-code
  herd:
    enabled: false

enabled: true: utilizar Herd cuando esté disponible.

enabled: false: utilizar siempre subagentes Claude Code.

Opción 2: Detección automática (recomendada)
executor:
  default: claude-code

  herd:
    enabled: auto
    agents:
      - opencode
      - codex

En esta propuesta, auto es un valor que debemos implementar en DevForge, no una funcionalidad nativa de YAML.

El comportamiento sería:

Configuración

Resultado

enabled: false

Siempre Claude Code

enabled: true

Herd obligatorio; error si no está disponible

enabled: auto

Herd si está activo en la sesión; de lo contrario Claude Code

Mi recomendación: utiliza enabled: auto en Personal Factory. Así no necesitas modificar la configuración cada vez que abras Claude Code dentro o fuera de Herd.

La detección debe comprobar la integración real de Herd en la sesión actual, no simplemente si Herd está instalado.

dame la arquitectura final de como se veria mi proyecto de fabrica y como seria la confifguracoipn de los yaml para el tema de los perfiles
DevForge Factory — Arquitectura final V1.0
Una sola fábrica de software, dos perfiles de trabajo y selección automática de ejecutores.

La arquitectura definitiva de tu proyecto estará basada en los principios de Software Factory V2 de ZazenCodes, incorporando la revisión multiagente de V1 y adaptando la orquestación a tus dos entornos.

El objetivo es que puedas instalar DevForge Factory en cualquier proyecto, ejecutar /factory y disponer del mismo panel, los mismos controles de calidad y el mismo flujo de desarrollo, independientemente de si trabajas con Jira, GitHub Issues, documentación o instrucciones directas.

1. Arquitectura general
DevForge Factory
Interfaz única: /factory
Hacer · Plan · Seguir · Ver · Revisar · Parar

Requirement Intake

Jira

Issues

Docs

Prompt

Normalización, análisis, clasificación y criterios de aceptación
Claude Code — Orquestador

Planning · Architecture · Scheduling · Seguimiento
Profile Resolver + Environment Detector

Work

Claude Max

Claude Agents

Personal

Claude Pro

Herd activo

OpenCode / Codex
Sin Herd

Claude Agents
Quality Engine

Build · Tests · Architecture · Code Review · Security · QA
Git Delivery

Worktrees → Commits → Pull Request → Aprobación → Merge
Reglas fundamentales
El núcleo de la fábrica es único y compartido.

El perfil determina las fuentes, las políticas Git y las reglas de ejecución.

Claude Code siempre funciona como orquestador.

Work utiliza subagentes nativos de Claude Code, sin depender de Herd.

Personal utiliza Herd con OpenCode y Codex cuando esa integración está disponible en la sesión; de lo contrario, utiliza subagentes Claude Code.

Cada desarrollo tiene su propio estado persistente, worktree, registros y resultados.

Ningún agente puede saltarse los controles de calidad.

La integración automática del código depende de la política del perfil y del repositorio.

2. Estructura completa del proyecto
Esta es la estructura que implementaría en el repositorio central devforge-factory.

devforge-factory/
│
├── .claude/
│   ├── skills/
│   │   └── factory/
│   │       └── SKILL.md
│   │
│   └── agents/
│       ├── intake.md
│       ├── planner.md
│       ├── architect.md
│       ├── spec-writer.md
│       ├── builder.md
│       ├── code-reviewer.md
│       ├── security-reviewer.md
│       ├── qa.md
│       ├── ui-reviewer.md
│       ├── ux-reviewer.md
│       └── approver.md
│
├── factory/
│   │
│   ├── core/
│   │   ├── orchestrator/
│   │   ├── workflow/
│   │   ├── state-machine/
│   │   ├── scheduler/
│   │   ├── requirements/
│   │   ├── profile-resolver/
│   │   ├── environment-detector/
│   │   ├── quality-engine/
│   │   ├── git-manager/
│   │   └── telemetry/
│   │
│   ├── adapters/
│   │   ├── sources/
│   │   │   ├── jira/
│   │   │   ├── github-issues/
│   │   │   ├── documents/
│   │   │   └── manual/
│   │   │
│   │   ├── executors/
│   │   │   ├── claude-code/
│   │   │   └── herd/
│   │   │
│   │   └── scm/
│   │       └── git/
│   │
│   ├── profiles/
│   │   ├── work.yaml
│   │   └── personal.yaml
│   │
│   ├── config/
│   │   ├── factory.yaml
│   │   ├── commands.yaml
│   │   ├── routing.yaml
│   │   └── quality.yaml
│   │
│   ├── workflows/
│   │   ├── feature.yaml
│   │   ├── fix.yaml
│   │   └── hotfix.yaml
│   │
│   ├── templates/
│   │   ├── requirement.md
│   │   ├── specification.md
│   │   ├── implementation-plan.md
│   │   ├── review.md
│   │   └── pull-request.md
│   │
│   ├── bin/
│   │   ├── job
│   │   ├── gate
│   │   ├── route
│   │   └── environment
│   │
│   ├── runtime/
│   │   ├── jobs/
│   │   ├── logs/
│   │   └── worktrees/
│   │
│   └── dashboard/
│       ├── index.html
│       ├── styles.css
│       └── app.js
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── INSTALL.md
│   ├── CONFIGURATION.md
│   ├── WORKFLOWS.md
│   └── SECURITY.md
│
├── CLAUDE.md
├── README.md
└── .gitignore
El núcleo puede implementarse inicialmente con Python 3.10+ y scripts de shell, aprovechando la aproximación de ZazenCodes V2, sin necesidad de introducir un backend HTTP o una base de datos desde el primer día.

El estado inicial puede persistirse en archivos JSON y Markdown. Si posteriormente necesitas coordinación entre máquinas o múltiples usuarios, podremos agregar una capa de persistencia más sólida.

Importante: runtime/ se utilizaría para ilustrar la estructura del componente. En instalaciones reales, los datos de ejecución deben quedar separados por proyecto y entorno, fuera de los archivos versionados y con un .gitignore apropiado. No se debe crear una carpeta compartida donde se mezclen los datos de Work y Personal.

3. Configuración central: factory/config/factory.yaml
Este archivo define el comportamiento común. No contiene reglas específicas de Jira, GitHub ni Herd.

version: "1.0"

factory:
  name: DevForge Factory
  command: /factory

  profile:
    directory: factory/profiles
    default: personal
    resolution: project-config

  orchestration:
    engine: claude-code
    persist_state: true
    resume_interrupted_jobs: true
    max_build_rounds: 3

  requirements:
    normalize: true
    generate_acceptance_criteria: true
    detect_dependencies: true
    allow_multiple_repositories: true
    require_approval_when_ambiguous: true

  execution:
    isolation: git-worktree
    require_plan: true
    require_quality_gate: true
    stop_on_critical_failure: true

  state:
    format: json
    documentation: markdown

  dashboard:
    enabled: true
    port: 8765
    refresh_seconds: 3

  security:
    protect_factory_config: true
    prevent_secret_commits: true
    restrict_destructive_commands: true
    require_approval_for_deploy: true

resolution: project-config significa que el perfil se selecciona desde la configuración del proyecto donde se está ejecutando DevForge.

El campo default: personal sería únicamente un valor de respaldo. En instalaciones empresariales exigiría que el perfil work esté declarado explícitamente, para no seleccionar accidentalmente el entorno equivocado.

Los nombres de estos campos forman parte del contrato que implementaremos en DevForge; no son opciones existentes de Claude Code.

4. Configuración empresarial: factory/profiles/work.yaml
Esta configuración contempla Jira, documentación, peticiones directas y otros requerimientos internos.

version: "1.0"
profile: work

identity:
  name: Work Factory
  environment: enterprise

orchestrator:
  provider: claude-code
  executor: claude-code

  agents:
    planning: planner
    architecture: architect
    implementation: builder
    quality: qa
    security: security-reviewer
    review: code-reviewer
    approval: approver

execution:
  concurrency: 2
  max_rounds: 3

  isolation:
    mode: git-worktree

  routing:
    strategy: native-claude-agents

requirements:
  id_prefix: REQ

  sources:
    jira:
      enabled: true
      mode: on-demand
      key_pattern: "^[A-Z][A-Z0-9]+-[0-9]+$"

    documents:
      enabled: true
      extensions:
        - .md
        - .txt
        - .pdf
        - .docx

    manual:
      enabled: true

    email:
      enabled: false

  intake:
    analyze_scope: true
    detect_dependencies: true
    split_large_requirements: true
    require_acceptance_criteria: true

git:
  base_branch: develop
  target_branch: develop

  branch:
    pattern: "{type}/{key}-{slug}"

    types:
      feature: feature
      fix: fix
      hotfix: hotfix

    fallback_id_prefix: REQ

  worktrees:
    enabled: true
    isolated_per_job: true

  pull_request:
    enabled: true
    auto_create: true
    auto_merge: false

    title_pattern: "[{key}] {title}"
    include_jira_reference: true

quality:
  require_build: true
  require_tests: true
  require_code_review: true
  require_security_review: true

  validate_architecture: true
  validate_acceptance_criteria: true

approval:
  require_human_for_merge: true
  require_human_for_deployment: true

  always_escalate:
    - database_destructive_changes
    - authentication_changes
    - production_configuration_changes
    - infrastructure_changes

tracking:
  update_jira: true
  comment_on_jira: true
  attach_pr_link: true
  change_jira_status: false

Qué hace exactamente
Supongamos que ejecutas:

/factory hacer EVR-1234

DevForge:

Obtiene el Jira y extrae el requerimiento.

Identifica el tipo de trabajo (feature, fix o hotfix).

Determina el repositorio y la rama base.

Crea feature/EVR-1234-descripcion desde origin/develop, si corresponde a un feature.

Prepara un plan y delega el desarrollo a Claude Code.

Ejecuta pruebas, análisis de código y seguridad.

Abre un PR hacia develop.

Registra los resultados y espera la aprobación requerida.

Si el requerimiento llega por documentación o petición directa, utiliza un identificador como REQ-0001.

El tipo de rama se puede inferir inicialmente, pero debe poder corregirse antes de crearla. Para un hotfix, la fábrica consultará las reglas del repositorio en lugar de asumir que siempre nace de develop.

Consideraciones importantes del perfil Work
El valor mode: on-demand evita procesar automáticamente todos los Jira a los que tengas acceso.

La fábrica no modifica estados de Jira hasta configurar expresamente esa funcionalidad y las transiciones autorizadas.

Las peticiones recibidas por correo estarán disponibles cuando habilites el adaptador correspondiente.

require_security_review: true asegura una revisión de seguridad en todos los desarrollos empresariales, además de las comprobaciones automáticas.

La aprobación de merges permanece en manos del equipo.

5. Configuración personal: factory/profiles/personal.yaml
Aquí está la configuración definitiva para tu flujo con Claude Pro y Herd.

version: "1.0"
profile: personal

identity:
  name: Personal Factory
  environment: personal

orchestrator:
  provider: claude-code

execution:
  concurrency: 2
  max_rounds: 3

  isolation:
    mode: git-worktree

  executor:
    default: claude-code

    herd:
      enabled: auto
      require_active_session: true

      agents:
        - opencode
        - codex

      balancing:
        enabled: true
        strategy: complexity-points

        points:
          - 1
          - 3
          - 5
          - 8

        target:
          opencode: 50
          codex: 50

      respect_dependencies: true

    fallback:
      when_herd_unavailable: claude-code

requirements:
  id_prefix: REQ

  sources:
    github_issues:
      enabled: true
      label: factory

    documents:
      enabled: true
      extensions:
        - .md
        - .txt
        - .pdf
        - .docx

    manual:
      enabled: true

    internal_backlog:
      enabled: true

  intake:
    analyze_scope: true
    detect_dependencies: true
    split_large_requirements: true
    require_acceptance_criteria: true

git:
  base_branch: main
  target_branch: main

  branch:
    pattern: "{type}/{key}-{slug}"

    types:
      feature: feature
      fix: fix
      hotfix: hotfix

    fallback_id_prefix: REQ

  worktrees:
    enabled: true
    isolated_per_job: true

  pull_request:
    enabled: true
    auto_create: true
    auto_merge: false

quality:
  require_build: true
  require_tests: true
  require_code_review: true

  validate_architecture: true
  validate_acceptance_criteria: true
  security_review_on_risk: true

approval:
  require_human_for_merge: true
  require_human_for_deployment: true

tracking:
  update_github_issue: true
  attach_pr_link: true
  close_issue_on_merge: true

Regla especial de Herd
Esta es la lógica que implementaría:

Personal Factory
¿Herd integrado en lasesión?
Herd
OpenCode
Codex
Claude Code Agents
Quality Gate
Code Review + PR
Sí
No
La interpretación de enabled: auto será:

Situación

Comportamiento

Herd activo e integrado en la sesión

Delegar a OpenCode y Codex

Herd instalado pero sesión normal de Claude Code

Ejecutar subagentes Claude Code

Herd no instalado

Ejecutar subagentes Claude Code

Herd detectado, pero falla una tarea

Aplicar política de reintentos; no cambiar ejecutor silenciosamente

Para detectar Herd, la implementación deberá utilizar un mecanismo verificable de la integración real. No sería correcto confiar solamente en una variable de entorno inventada, la existencia del binario o el directorio actual.

La fábrica registrará qué ejecutor recibió cada tarea para permitir seguimiento, reintentos y recuperación.

Distribución de carga en Herd
La asignación del 50 % es un objetivo de balanceo, no una obligación de repartir cada requerimiento por mitades.

Ejemplo:

Trabajo

Complejidad

Ejecutor

Implementar API

5

Codex

Construir interfaz

5

OpenCode

Crear migraciones

3

OpenCode

Añadir pruebas

3

Codex

Total

16

8 / 8 puntos

El planificador propone tareas, puntos y dependencias. Cuando Herd está activo, delega a sus subagentes según las capacidades de la integración.

Si estás fuera de Herd, el mismo plan se ejecutará con subagentes Claude Code y no necesitarás modificar personal.yaml.

6. Configuración por proyecto
No todos tus repositorios tendrán las mismas tecnologías, comandos de compilación ni reglas de ramas.

Por eso, cada proyecto tendrá un archivo local:

factory.project.yaml

Este archivo tendrá prioridad sobre los valores del perfil únicamente para las opciones que permitamos sobrescribir.

Ejemplo: proyecto empresarial .NET + Angular
version: "1.0"

project:
  name: Everest
  profile: work

  repositories:
    - name: everest-api
      path: ../everest-api
      technology: dotnet

    - name: everest-web
      path: ../everest-web
      technology: angular

git:
  base_branch: develop
  target_branch: develop

  branch:
    pattern: "{type}/{key}-{slug}"

quality:
  repositories:
    everest-api:
      commands:
        - dotnet restore
        - dotnet build --no-restore
        - dotnet test --no-build

    everest-web:
      commands:
        - npm ci
        - npm run build
        - npm test -- --watch=false

policies:
  require_human_approval: true
  allow_automatic_merge: false

Los comandos de pruebas son ejemplos; la instalación deberá adaptarlos a los scripts reales del proyecto.

Esto permite que un mismo Jira afecte varios repositorios y que cada repositorio tenga su propio worktree y Quality Gate.

Ejemplo: proyecto personal con Laravel
version: "1.0"

project:
  name: SaludSystem
  profile: personal

  repositories:
    - name: salud-system
      path: .
      technology: laravel

git:
  base_branch: develop
  target_branch: develop

quality:
  commands:
    - composer validate
    - php artisan test
    - npm run build

Observa que en este ejemplo personal la rama base es develop, aunque el valor predeterminado de personal.yaml es main.

La configuración del proyecto puede sobrescribirla.

También recomiendo validar los YAML con un esquema formal y rechazar propiedades desconocidas. Así evitamos que una clave escrita incorrectamente sea ignorada sin avisar.

7. Configuración del panel: factory/config/commands.yaml
Para que los comandos sean fáciles de recordar, dejaría únicamente seis acciones principales.

version: "1.0"

commands:
  root: /factory
  interactive_menu: true

  actions:
    hacer:
      description: Crear o desarrollar un requerimiento
      aliases:
        - run
        - crear

    plan:
      description: Analizar y planificar sin implementar

    seguir:
      description: Reanudar trabajos pendientes
      aliases:
        - continuar

    ver:
      description: Consultar trabajos y resultados
      aliases:
        - estado

    revisar:
      description: Validar código y resultados
      aliases:
        - review

    parar:
      description: Detener ejecución de trabajos
      aliases:
        - stop

  natural_language:
    enabled: true

Comandos que utilizarías diariamente
Necesidad

Comando

Abrir panel

/factory

Ejecutar Jira

/factory hacer EVR-1234

Desarrollar GitHub Issue

/factory hacer 42

Crear un requerimiento

/factory hacer Crear API de pacientes

Analizar documentación

/factory plan ./docs/requerimientos.pdf

Ejecutar documento

/factory hacer ./docs/requerimientos.pdf

Recuperar trabajos

/factory seguir

Ver progreso

/factory ver

Revisar desarrollo

/factory revisar

Detener

/factory parar

El significado de un identificador se determina según el perfil y la fuente. Por ejemplo, en Personal el número 42 puede representar GitHub Issue #42, mientras que en Work se reconocerá un código como EVR-1234.

En caso de ambigüedad, el panel debe permitir elegir la fuente.

/factory parar deberá detener las tareas de forma controlada y conservar su estado para recuperarlas posteriormente.

Vista del panel final
DevForge Factory
Panel de ejecución — diseño de referencia
V1.0
Perfil del proyecto
Work Factory
Personal Factory
Motor de ejecución

Disponible
Claude Code → Subagentes nativos

En la implementación final, el perfil y Herd se detectarán automáticamente. Aquí pueden cambiarse para visualizar el comportamiento.
Selecciona una acción

Hacer


Plan


Seguir


Ver


Revisar


Parar

Requerimiento
EVR-1234, ruta del documento o descripción del desarrollo

Prototipo visual interactivo, no conectado todavía al sistema de ejecución.
8. Pipeline de desarrollo compartido
Los dos perfiles utilizan las mismas etapas. Lo que cambia es la fuente del requerimiento, el ejecutor y las políticas de entrega.

Intake

Obtener la solicitud, analizar documentación, validar alcance y crear un requerimiento normalizado.

Planning

Descomponer el trabajo, determinar complejidad, dependencias, repositorios y criterios de aceptación.

Architecture

Revisar la arquitectura existente y determinar los cambios mínimos necesarios.

Build

Crear ramas y worktrees, asignar ejecutores y desarrollar.

Quality Gate

Ejecutar compilación, pruebas, validaciones y controles deterministas. Si falla, regresar al builder.

Review

Inspeccionar corrección, mantenibilidad, seguridad y, cuando corresponda, UI/UX. Si se requieren cambios, abrir otra ronda.

Approval & Delivery

Evaluar el resultado, sincronizar con la rama base, repetir el gate y preparar el PR. La política del perfil determina cuándo puede fusionarse.

9. Máquina de estados
La máquina de estados será compartida, persistente y controlada por scripts, como en la V2.

CREATED
INTAKE
¿Requerimiento válido?
NEEDS_INFO
REJECTED
PLANNING
READY
BUILDING
GATE
¿Quedan intentos?
NEEDS_HUMAN
REVIEW
APPROVAL
DELIVERY
DONE
Falta información
Rechazado
Aceptado
FAIL
Sí
No
PASS
CHANGES
PASS
Requiere humano
Correcciones
Aprobado
Autorizado
El orquestador no debería modificar arbitrariamente los estados. Los scripts deben validar las transiciones permitidas y registrar quién realizó cada cambio.

Un trabajo pausado o interrumpido conservará su estado, identificador, ejecutor, rama y resultados para reanudarse con /factory seguir.

10. Cómo instalaría DevForge en tus proyectos
Recomiendo conservar un repositorio central con el código de DevForge y crear instalaciones por proyecto, sin copiar manualmente componentes cada vez.

Cada instalación tendría una estructura como esta:

mi-proyecto/
│
├── .claude/
│   └── skills/
│       └── factory/
│           └── SKILL.md
│
├── .devforge/
│   ├── factory.project.yaml
│   ├── jobs/
│   └── logs/
│
├── src/
├── tests/
└── CLAUDE.md
El directorio .devforge/jobs/ conservará el estado y estará excluido de Git. El núcleo compartido deberá estar disponible mediante una instalación versionada y una ruta controlada, evitando depender de rutas absolutas personales.

Para las sesiones que manejen múltiples repositorios, el almacenamiento podrá ubicarse fuera de cada checkout y asociarse mediante identificadores estables de proyecto.

Separación de instalaciones
Entorno Work

Instalación empresarial

Configuración Work, repositorios corporativos, Jira y credenciales empresariales.

Aislado
Entorno Personal

Instalación personal

Configuración Personal, proyectos privados, GitHub Issues y Herd opcional.

Aislado
Las dos instalaciones comparten el código y las actualizaciones de DevForge, pero no comparten automáticamente credenciales, sesiones, historiales o contenidos del proyecto.

11. Qué archivos son indispensables para la primera versión
Para evitar sobreingeniería, no desarrollaría todos los módulos del árbol inicial desde el primer momento.

La primera versión funcional debería incluir:

Componente

Prioridad

SKILL.md y menú /factory

Esencial

work.yaml y personal.yaml

Esencial

factory.project.yaml

Esencial

Intake de Jira, Issues, documentos y prompt

Esencial

Máquina de estados

Esencial

Claude Code Executor

Esencial

Integración con Herd

Esencial para Personal con Herd

Git worktrees y ramas

Esencial

Quality Gates

Esencial

Code Review y QA

Esencial

PR y aprobación

Esencial

Recuperación de trabajos

Esencial

Dashboard HTML

Primera versión

Métricas de consumo avanzadas

Posterior

Persistencia distribuida

Posterior

Integración automática con correo

Posterior

Los archivos de configuración anteriores son una especificación de diseño, no código que ZazenCodes o Claude Code reconocerán directamente. La implementación deberá desarrollar los resolutores, validadores y adaptadores que les den funcionamiento.

También habrá que verificar la interfaz real de Herd para saber cómo detectar una sesión activa, delegar trabajos, consultar resultados y recuperar tareas. Esa integración es la principal dependencia técnica todavía por comprobar.

12. Resultado final esperado
Tu flujo cotidiano quedaría así:

En el trabajo abres Claude Code, ejecutas /factory, seleccionas Hacer, introduces un Jira, adjuntas documentación o escribes una petición. La fábrica planifica, implementa con subagentes Claude, valida el desarrollo y prepara el PR según tus reglas de ramas.

En tus proyectos personales haces exactamente lo mismo. Si estás utilizando Herd, los desarrollos se distribuyen entre OpenCode y Codex. Si estás en una sesión normal de Claude Code, los realizan subagentes Claude.

La arquitectura final queda definida como un núcleo único, dos perfiles YAML, un archivo de configuración por proyecto, un pipeline común y una interfaz /factory que no cambia según el entorno.

Esta estructura conserva lo más valioso de ZazenCodes V1/V2, incorpora tu flujo empresarial y permite aprovechar Herd en los proyectos personales sin convertirlo en una dependencia obligatoria.

llevemos esto a codex para empezar con el desarrollo  la carpeta la crearia aca /home/jcastro/Desarrollo/FullStack
Ha trabajado durante 0s
Continuado en Work
He trasladado el desarrollo de DevForge Factory a Codex en una nueva sesión de trabajo.

La ubicación definida para el proyecto es:

/home/jcastro/Desarrollo/FullStack/devforge-factory

Codex tiene las instrucciones para comenzar con:

Estructura inicial: núcleo compartido, agentes, configuraciones YAML y documentación.

Work Factory: Jira, documentación y solicitudes directas; Claude Code y ramas desde develop.

Personal Factory: GitHub Issues y requerimientos internos; Herd con OpenCode/Codex cuando esté activo, o subagentes Claude Code cuando no lo esté.

Panel /factory: Hacer, Plan, Seguir, Ver, Revisar y Parar.

Calidad: worktrees, pruebas, revisiones, estados persistentes y Pull Requests con aprobación humana.

También deberá consultar las dos versiones de ZazenCodes, verificar la integración real de Herd y ejecutar pruebas sobre lo que implemente.

El desarrollo se ha transferido a Codex; todavía no estoy confirmando que los archivos se hayan creado o que las pruebas hayan pasado. Eso deberá verificarse en la nueva sesión.

No se autorizaron publicaciones, despliegues ni git push automáticos.




Draggable item local:01a200b0-94ec-7fe3-b2a2-beff5e9f80f5 was dropped over droppable area sidebar-thread-container:project:975c8426-69ef-4e13-931f-33c261ea89230
