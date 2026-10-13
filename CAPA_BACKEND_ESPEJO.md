# Capa Omni — infraestructura espejo aislada (13/10/2026)

## Qué quedó funcionando

- **Nueva instancia:** https://capa-omni-mcp.onrender.com
- **Health:** https://capa-omni-mcp.onrender.com/health
- **Código de backend:** https://github.com/Martingim-10/capa-seguros-chatgpt/tree/feature/omni-mcp-isolated-20261013
- **MCP:** https://capa-omni-mcp.onrender.com/mcp
- **Pruebas externas:** https://github.com/Martingim-10/capa-seguros-chatgpt/actions/workflows/omni-isolated-mcp-smoke.yml

Replica el backend Node.js MCP v0.6.2 con los módulos de identidad/invitaciones, cartera, evidencia, caches y conector a Sancor, **sin trasladar cuentas, tokens, documentos, ni la base de datos del otro entorno**.

Se endureció el comportamiento: cuando Auth0 no está configurado, `/mcp` devuelve 503 (fail-closed). También está deshabilitado por defecto `ALLOW_DEMO_IDENTITY`.

Esta nueva instancia está **activa**, pero **no está lista para consultar seguros reales**: todavía no cuenta con PostgreSQL propio, cliente Auth0 propio ni credenciales autorizadas para el puente Sancor.

El servicio Python `capa-seguros-omni` original y su rama main permanecen sin cambios. **No desplegar su código actual contra pólizas reales**, porque los identificadores de acceso al piloto están hardcodeados y no acreditan identidad/consentimiento.

## Bloqueantes para activar asegurados de forma segura

1. PostgreSQL aislado: Render rechazó crear un segundo PostgreSQL gratuito (`cannot have more than one active free tier database`). Requiere otra base gestionada independiente o autorización previa para un plan pago. **Nunca apuntar a la DB de asegurados de Capa original.**
2. Configurar un cliente OAuth Auth0 y credenciales propias del servicio. Vinculación explícita del asegurado a su referencia; nunca aceptar DNI/ref arbitrarios como autorización.
3. Configurar credencial *de mínimo privilegio* para el puente Sancor `capa-cleanroom`, o acceso oficial Sancor equivalente, otorgado específicamente a este entorno. **No copiar tokens internos de Capa ni pegarlos en GitHub o chats.**
4. Crear `APP_ENCRYPTION_KEY` y `ADMIN_API_KEY` nuevas para esta instalación. Guardar únicamente en Render Secrets/Environment.
5. Cerrar y verificar pendientes de QA de telemetría antes de emitir invitaciones reales (ver PR #27 de Capa).

## Estado de referencia

La prueba externa desde GitHub Actions verifica cuatro respuestas sin datos de clientes: `/health = 200`, configuración de identidad aislada, `/mcp = 503` sin OAuth, y `/.well-known/oauth-protected-resource = 503` sin OAuth.

La igualdad de condiciones real requiere identidad autorizada, base separada y credenciales verificables. Hasta entonces, **infraestructura levantada no equivale a MVP operativo de asegurados**.

**Enlaces:**
- Proyecto Node de referencia: https://github.com/Martingim-10/capa-seguros-chatgpt
- Versión Python Gemini: https://github.com/Martingim-10/capa-seguros-omni
- Logs de la nueva instancia: https://dashboard.render.com/web/srv-db7ag4id0e5s73fsp2h0
