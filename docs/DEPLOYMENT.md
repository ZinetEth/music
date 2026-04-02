# Deployment Guide

## Production Deployment Checklist

### 1. Environment Configuration

Copy `.env.example` to `.env` and update with production values:

```bash
# Database Configuration
POSTGRES_USER=your_production_user
POSTGRES_PASSWORD=your_secure_db_password
POSTGRES_DB=musicdb
DATABASE_URL=postgresql://your_production_user:your_secure_db_password@postgres:5432/musicdb

# Redis Configuration
REDIS_PASSWORD=your_secure_redis_password
REDIS_URL=redis://:your_secure_redis_password@redis:6379/0

# Application Configuration
APP_ENV=production
APP_TITLE=Music Platform Backend
APP_VERSION=1.0.0
SECRET_KEY=your-super-secret-key-min-32-characters-long
ADMIN_API_KEY=your-secure-admin-api-key

# Security Configuration
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
HTTPS_REDIRECT=true
DOCS_ENABLED=false
REDOC_ENABLED=false

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# Logging
LOG_LEVEL=INFO
```

### 2. Security Requirements

Before deploying to production:

- [ ] Set strong `SECRET_KEY` (minimum 32 characters)
- [ ] Set secure `ADMIN_API_KEY`
- [ ] Configure `ALLOWED_HOSTS` with your domain(s)
- [ ] Configure `ALLOWED_ORIGINS` with your frontend URL(s)
- [ ] Set `HTTPS_REDIRECT=true`
- [ ] Disable API docs: `DOCS_ENABLED=false`
- [ ] Use PostgreSQL database (not SQLite)
- [ ] Set strong database and Redis passwords

### 3. Docker Deployment

#### Build and Deploy

```bash
# Build production images
docker compose -f docker-compose.yml build

# Start services
docker compose -f docker-compose.yml up -d

# Check service status
docker compose -f docker-compose.yml ps

# View logs
docker compose -f docker-compose.yml logs -f
```

#### Health Checks

Monitor service health:

```bash
# Backend health
curl https://yourdomain.com/health

# Database readiness
curl https://yourdomain.com/health/ready

# Liveness probe
curl https://yourdomain.com/health/live
```

### 4. SSL/TLS Configuration

#### Using Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/your/cert.pem;
    ssl_certificate_key /path/to/your/key.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. Monitoring and Logging

#### Structured Logging

The application outputs structured JSON logs by default. Monitor for:

- Request processing time
- Error rates
- Rate limit violations
- Database connection issues

#### Key Metrics to Monitor

- Response time (p95, p99)
- Error rate (4xx, 5xx)
- Database connection pool usage
- Redis connection status
- Memory and CPU usage

### 6. Backup Strategy

#### Database Backups

```bash
# Daily backup
docker exec music-postgres pg_dump -U musicuser musicdb > backup_$(date +%Y%m%d).sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
docker exec music-postgres pg_dump -U musicuser musicdb | gzip > "$BACKUP_DIR/backup_$DATE.sql.gz"
```

#### Volume Backups

```bash
# Backup data volumes
docker run --rm -v music-platform_postgres-data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_data.tar.gz -C /data .
docker run --rm -v music-platform_navidrome-data:/data -v $(pwd):/backup alpine tar czf /backup/navidrome_data.tar.gz -C /data .
```

### 7. Performance Optimization

#### Database Optimization

- Monitor slow queries
- Optimize indexes
- Tune connection pool settings
- Regular VACUUM and ANALYZE

#### Caching

- Redis is configured for session storage
- Application-level caching for GET requests (5-minute TTL)
- Consider CDN for static assets

### 8. Scaling Considerations

#### Horizontal Scaling

- Use external Redis for session storage
- Load balancer for multiple backend instances
- Database read replicas for read-heavy workloads

#### Resource Requirements

Minimum production specs:
- **Backend**: 2 CPU, 4GB RAM
- **PostgreSQL**: 2 CPU, 4GB RAM, 50GB SSD
- **Redis**: 1 CPU, 2GB RAM
- **Navidrome**: 1 CPU, 2GB RAM

### 9. Troubleshooting

#### Common Issues

1. **Database Connection Errors**
   ```bash
   docker logs music-backend
   docker logs music-postgres
   ```

2. **High Memory Usage**
   ```bash
   docker stats
   ```

3. **Rate Limiting Issues**
   - Check `RATE_LIMIT_PER_MINUTE` setting
   - Monitor logs for rate limit warnings

#### Log Analysis

```bash
# Filter error logs
docker logs music-backend | grep "ERROR"

# Monitor response times
docker logs music-backend | grep "request_processed" | jq '.duration_ms'
```

### 10. Security Best Practices

- Regular security updates
- Monitor for vulnerabilities
- Use secrets management
- Implement backup encryption
- Regular security audits
- Network segmentation
- Firewall configuration

### 11. Rollback Procedure

```bash
# Stop current deployment
docker compose -f docker-compose.yml down

# Restore database backup
docker exec -i music-postgres psql -U musicuser musicdb < backup.sql

# Start previous version
docker compose -f docker-compose.yml up -d

# Verify health
curl https://yourdomain.com/health
```
