# PMOVES.AI Integration Guide for BoTZ MCP Gateway

## Integration Complete

The PMOVES.AI integration template has been applied to BoTZ MCP Gateway.

## Next Steps

### 1. Customize Environment Variables

Edit the following files with your service-specific values:

- `env.shared` - Base environment configuration
- `env.tier-agent` - AGENT tier specific configuration
- `chit/secrets_manifest_v2.yaml` - Add your service's required secrets

### 2. Update Docker Compose

Add the PMOVES.AI environment anchor to your `docker-compose.yml`:

```yaml
services:
  botz-gateway:
    <<: [*env-tier-agent, *pmoves-healthcheck]
    # Your existing service configuration...
```

### 3. Integrate Health Check

Add the health check endpoint to your service:

```python
from pmoves_health import add_custom_check, get_health_status

@app.get("/healthz")
async def health_check():
    return await get_health_status()
```

### 4. Add Service Announcement

Add NATS service announcement to your startup:

```python
from pmoves_announcer import announce_service

@app.on_event("startup")
async def startup():
    await announce_service(
        slug="botz-gateway",
        name="BoTZ MCP Gateway",
        url=f"http://botz-gateway:8080",
        port=8080,
        tier="agent"
    )
```

### 5. Test Integration

```bash
# Test health check
curl http://localhost:8080/healthz

# Verify environment variables loaded
docker compose exec botz-gateway env | grep PMOVES

# Verify NATS announcement
nats sub "services.announce.v1"
```

## Service Details

- **Name:** BoTZ MCP Gateway
- **Slug:** botz-gateway
- **Tier:** agent
- **Port:** Per config (gateway)
- **Health Check:** http://localhost:8080/healthz
- **NATS Enabled:** True
- **GPU Enabled:** False

## Support

For questions or issues, see the PMOVES.AI documentation.
