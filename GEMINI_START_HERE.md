# PARA GEMINI — Traspaso operativo de Capa Omni (13/10/2026)

**Propósito:** permitir que Gemini retome el MVP sobre infraestructura Capa ya montada, sin pedir al usuario que reconstruya integraciones, copie secretos en el chat ni programe a ciegas. Este archivo es **el punto de entrada técnico**. El código Python de `capa-seguros-omni` no ha sido conectado aún a esta infraestructura.

## 1. Lo que existe realmente

| Componente | Enlace / estado |
|---|---|
| Backend Omni separado (Node.js + MCP) | https://capa-omni-mcp.onrender.com — **LIVE** |
| Diagnóstico de preparación (sin secretos) | https://capa-omni-mcp.onrender.com/pilot/readiness |
| Health | https://capa-omni-mcp.onrender.com/health |
| Descubrimiento OAuth | https://capa-omni-mcp.onrender.com/.well-known/oauth-protected-resource |
| Endpoint MCP | https://capa-omni-mcp.onrender.com/mcp — **OAuth protegido** |
| Código del backend Omni | https://github.com/Martingim-10/capa-seguros-chatgpt/tree/feature/omni-mcp-isolated-20261013 |
| Servicio Render del backend Omni | https://dashboard.render.com/web/srv-db7ag4id0e5s73fsp2h0 |
| Base de datos independiente | `capa-omni-pilot-db`, PostgreSQL 17, Oregon, **conectada** |
| Auth0 | Tenant `dev-1xadutu23ydo7tvz.us.auth0.com`; API audience `https://capa-omni-mcp.onrender.com` |
| OAuth | Client de onboarding exclusivo Omni, secreto ya en Render; `insurance:read` agregado a API Auth0 |
| Puente real a Sancor | `https://capa-cleanroom.onrender.com` — **NO autorizado aún para la nueva instancia Omni** |
| Cambio para permitir acceso Omni al puente | PR #28: https://github.com/Martingim-10/capa-seguros-chatgpt/pull/28 — **DRAFT, sin merge ni despliegue** |
| QA independiente | Radar coordina por https://github.com/Martingim-10/capa-seguros-chatgpt/issues/1 |

El `/pilot/readiness` NO indica que el MVP completo esté operativo: las piezas Omni DB/cifrado/admin y Auth0 están configuradas; el acceso autorizado al puente Sancor sigue pendiente. El login PKCE y el rechazo de MCP anónimo pasaron pruebas; **no** se probó un token auténtico de usuario con `insurance:read` ni una consulta real desde Omni.

## 2. Qué debe hacer Gemini desde ahora

**NO volver a solicitar `SANCOR_USERNAME`, `SANCOR_PASSWORD`, `SANCOR_CLIENT_ID` ni `SANCOR_API_TOKEN` para `capa-seguros-omni`.** La ruta convenida es usar el backend Omni aislado y, detrás de éste, un acceso Sancor autorizado con credencial secundaria, previa revisión. Evitar duplicar Sancor/Auth0.

1. Inspeccionar el servidor Omni existente y sus **seis herramientas MCP** (cuatro de consulta + contexto de protección y contacto PAS), respetando OAuth `insurance:read` y el vínculo de invitación verificado. Nunca enviar DNI ni referencia arbitrarios como autorización.
2. Adaptar la versión de Gemini para consumir ese backend (a través de un cliente MCP con OAuth o del flujo autorizado correspondiente), en lugar de respuestas hardcodeadas. **No** insertar tokens de invitación, claves o datos reales en el repositorio.
3. Mantener su repositorio `Martingim-10/capa-seguros-omni` y su servidor Python `capa-seguros-omni.onrender.com` **independientes**. Este archivo es el traspaso; aún no se ha implementado el cliente MCP en Python.
4. Probar primero conexión pública `/health`, OAuth discovery y denegación de `/mcp` sin credenciales. Recién después de revisión/permiso, una consulta con usuario autenticado y contrato autorizado.
5. Preparar pruebas funcionales sobre Auto 200 con póliza real autorizada, separando claramente discovery, PDF realmente legible y respuesta contractual con evidencia. Para Hogar 1800, discovery está soportado, pero PDF permanece pendiente: **nunca anunciarlo como resuelto**.
6. Para publicación en ChatGPT móvil, NO confundir manifest preparado con plugin efectivamente publicado/instalable. La publicación externa sigue pendiente.

## 3. Seguridad obligatoria

- La versión Python actual de Gemini contiene registros de pólizas sintéticas en `engine.py` e identificadores de acceso de piloto en `api_server.py`. **No usarla con credenciales reales hasta corregir estos puntos.**
- La PR #28 del puente restringe el **token secundario** a referencias autorizadas, Auto 200, sin búsquedas generales por documento, y filtra la respuesta. No está desplegada: hasta aprobarla, no hay credencial útil para Omni.
- La PR #27 de telemetría de Capa principal tiene hallazgos FAIL de Radar. No habilitar clientes reales ni afirmar cierre integral de seguridad sin resolverlos y repetir QA.
- No usar la base, `APP_ENCRYPTION_KEY`, `ADMIN_API_KEY`, `CAPA_INTERNAL_TOKEN` ni otros secretos de Capa principal. La réplica ya tiene secretos propios en Render.
- Sin cuenta autenticada/vínculo verificado, ningún usuario puede obtener pólizas. No permitir acceso por solo poseer un token escrito en código.

## 4. Pruebas reproducibles ya ejecutadas

- Omni OAuth/PKCE y MCP anónimo denegado: https://github.com/Martingim-10/capa-seguros-chatgpt/actions/runs/38477953158
- Omni con DB PostgreSQL configurada: https://github.com/Martingim-10/capa-seguros-chatgpt/actions/runs/38475252275
- QA de token secundario Cleanroom: https://github.com/Martingim-10/capa-seguros-chatgpt/actions/runs/38479388341 — 9/9 PASS con Sancor **simulado**, no integración real Omni.

## 5. Criterio honesto de “listo”

- **LISTO para desarrollar/integrar:** infraestructura Omni levantada, Postgres propio, OAuth configurado, repositorio y QA.
- **NO LISTO para piloto real:** falta aprobar/desplegar conexión Sancor scoped, probar token real OAuth con scope correcto, completar integración Gemini↔backend y resolver hallazgos de seguridad.

**Instrucción de equipo:** reutilizar lo probado, cuestionar lo imperfecto, documentar hechos y trabajar con Radar. Nunca dar a entender que el MVP de Gemini consulta Sancor si no existe una prueba E2E autorizada.
