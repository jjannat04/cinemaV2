# Deployment Guide

## Option 1: Poridhi VM (Recommended)

### Prerequisites
- Poridhi lab credentials
- Git installed
- Docker and Docker Compose installed on VM

### Steps

1. **Prepare Your Repository**
```bash
cd cinemaseat
git init
git add .
git commit -m "Initial commit - CinemaSeat booking system"

# Create GitHub repository and push
gh repo create cinemaseat --public --source=. --remote=origin
git push -u origin main
```

2. **Launch Poridhi Lab**
- Start your lab at the beginning of the event (9:00 AM)
- Note your lab credentials (IP, username, password)

3. **Deploy to VM**
```bash
# SSH into your Poridhi VM
ssh username@your-lab-ip

# Clone repository
git clone https://github.com/YOUR_USERNAME/cinemaseat.git
cd cinemaseat

# Start the application
docker-compose up -d

# Verify it's running
curl http://localhost:8000/health
```

4. **Configure Security**
```bash
# Allow traffic on port 8000 (if using firewall)
sudo ufw allow 8000
sudo ufw allow 5432  # Only if needed for external access
```

5. **Get Your Public URL**
```bash
# Your VM's public IP is your deployed URL
# Example: http://YOUR_VM_PUBLIC_IP:8000
```

6. **Test Deployment**
```bash
# From your local machine
curl http://YOUR_VM_PUBLIC_IP:8000/health
curl http://YOUR_VM_PUBLIC_IP:8000/movies
```

## Option 2: AWS (Bonus - Harder)

### Prerequisites
- AWS credentials from your lab
- AWS CLI installed
- Docker and Docker Compose

### Steps

1. **Create EC2 Instance**
```bash
# Using AWS CLI
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.micro \
  --key-name YOUR_KEY_PAIR \
  --security-group-ids sg-xxxxxxxx \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=CinemaSeat}]"
```

2. **Configure Security Group**
- Allow inbound HTTP on port 8000
- Allow inbound SSH on port 22
- Allow PostgreSQL only from internal (if needed)

3. **Deploy to EC2**
```bash
# SSH into EC2
ssh -i YOUR_KEY.pem ubuntu@YOUR_EC2_PUBLIC_IP

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone and deploy
git clone https://github.com/YOUR_USERNAME/cinemaseat.git
cd cinemaseat
docker-compose up -d
```

4. **Set Up Load Balancer (Optional)**
```bash
# Using Application Load Balancer
aws elbv2 create-load-balancer \
  --name cinemaseat-lb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups sg-xxxxxxxx

# Configure target group and listeners
```

## Environment Variables

### Production Settings
Create `.env.production`:

```env
DATABASE_URL=postgresql://postgres:STRONG_PASSWORD@db:5432/cinemaseat
GATEWAY_URL=http://gateway:9000
HOLD_TTL_SECONDS=300
APP_PORT=8000
SECRET_KEY=CHANGE_THIS_TO_RANDOM_STRING
```

### Security Notes
- Change default passwords
- Use strong SECRET_KEY
- Don't commit .env files
- Use environment-specific configs

## Monitoring

### Health Checks
```bash
# Application health
curl http://YOUR_URL/health

# Gateway health
curl http://YOUR_URL:9000/health

# Database health
docker-compose exec db pg_isready -U postgres
```

### Logs
```bash
# Application logs
docker-compose logs -f app

# Gateway logs
docker-compose logs -f gateway

# Database logs
docker-compose logs -f db
```

## Troubleshooting

### Issue: Containers won't start
```bash
# Check logs
docker-compose logs

# Rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Issue: Database connection failed
```bash
# Check if database is ready
docker-compose exec db pg_isready -U postgres

# Restart database
docker-compose restart db
```

### Issue: Gateway callbacks not arriving
```bash
# Check gateway debug
curl http://localhost:9000/debug/deliveries

# Verify callback URL uses service name
# Should be http://app:8000/bookings/callback
# NOT http://localhost:8000/bookings/callback
```

## Backup and Recovery

### Database Backup
```bash
# Backup
docker-compose exec db pg_dump -U postgres cinemaseat > backup.sql

# Restore
docker-compose exec -T db psql -U postgres cinemaseat < backup.sql
```

### Application Backup
```bash
# Backup entire directory
tar -czf cinemaseat-backup.tar.gz cinemaseat/
```

## Scaling

### Horizontal Scaling
```bash
# Run multiple app instances
docker-compose up -d --scale app=3

# Configure load balancer to distribute traffic
```

### Database Scaling
- Use managed PostgreSQL (RDS) for production
- Configure read replicas for read-heavy workloads
- Use connection pooling (PgBouncer)

## Rollback

### Quick Rollback
```bash
# Revert to previous commit
git checkout PREVIOUS_COMMIT_HASH
docker-compose down
docker-compose up -d --build
```

### Database Rollback
```bash
# Restore from backup
docker-compose exec -T db psql -U postgres cinemaseat < backup.sql
```

## Clean Up

### Remove All Resources
```bash
# Stop and remove containers
docker-compose down -v

# Remove images
docker rmi cinemaseat-app

# On AWS, terminate EC2 instances
aws ec2 terminate-instances --instance-ids i-xxxxxxxx
```

## Verification Checklist

Before submission, verify:

- [ ] `docker compose up` works from clean clone
- [ ] Health check returns 200 in under 1 second
- [ ] HOLD_TTL_SECONDS read from environment
- [ ] No double-booking under load (Scenario A)
- [ ] Hold expiration works (Scenario B)
- [ ] Payment gateway integration works
- [ ] Frontend functional
- [ ] Deployed and reachable
- [ ] GitHub repository is public
- [ ] README.md contains deployed URL
- [ ] DECISIONS.md exists
- [ ] ARCHITECTURE.md exists