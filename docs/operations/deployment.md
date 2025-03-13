# Deployment Guide for Borrow Rate & Locate Fee Pricing Engine

## Deployment Overview

This document provides comprehensive guidance for deploying the Borrow Rate & Locate Fee Pricing Engine to development, staging, and production environments. It covers the deployment architecture, procedures, configuration management, and operational considerations.

The Borrow Rate & Locate Fee Pricing Engine is deployed as a set of microservices in Kubernetes, with supporting infrastructure managed through Terraform. The deployment process is automated through CI/CD pipelines with appropriate controls for each environment.

### Deployment Architecture

The system is deployed using the following architecture:

```mermaid
flowchart TD
    subgraph "AWS Cloud"
        subgraph "VPC"
            subgraph "Public Subnets"
                ALB[Application Load Balancer]
                NAT[NAT Gateway]
                BASTION[Bastion Host]
            end
            
            subgraph "Private Subnets - Application Tier"
                EKS[EKS Nodes]
            end
            
            subgraph "Private Subnets - Data Tier"
                RDS[RDS PostgreSQL]
                REDIS[ElastiCache Redis]
            end
        end
        
        subgraph "AWS Services"
            ECR[Elastic Container Registry]
            S3[S3 Buckets]
            SM[Secrets Manager]
            CW[CloudWatch]
        end
    end
    
    CLIENT[Client Applications] --> ALB
    ALB --> EKS
    EKS --> RDS
    EKS --> REDIS
    EKS --> ECR
    EKS --> S3
    EKS --> SM
    EKS --> CW
    
    EKS --> NAT
    NAT --> Internet
    BASTION --> EKS
```

This architecture provides a secure, scalable foundation for the pricing engine with appropriate network isolation and service integration.

### Deployment Environments

The system is deployed to three distinct environments:

| Environment | Purpose | Access Control | Scaling |
|------------|---------|----------------|----------|
| Development | Feature development and testing | Developer access | Minimal resources, cost optimization |
| Staging | Pre-production validation | Limited team access | Production-like with reduced scale |
| Production | Live system serving clients | Restricted access | Full high-availability configuration |

Each environment is isolated with separate infrastructure and configuration to prevent cross-environment impacts.

### Deployment Strategy

The deployment strategy varies by environment:

- **Development**: Continuous deployment from feature branches
- **Staging**: Automated deployment from main branch after tests pass
- **Production**: Controlled deployment with manual approval and canary testing

Production deployments use a canary approach to minimize risk:
1. Deploy new version to a small subset of pods (10% of traffic)
2. Monitor for errors and performance issues
3. Gradually increase traffic to the new version
4. Complete the rollout when stability is confirmed

This approach allows for early detection of issues while minimizing customer impact.

### Deployment Components

The deployment includes the following components:

1. **Microservices**:
   - API Gateway
   - Calculation Service
   - Data Service
   - Cache Service
   - Audit Service

2. **Infrastructure**:
   - Amazon EKS (Kubernetes)
   - Amazon RDS for PostgreSQL
   - Amazon ElastiCache for Redis
   - Application Load Balancer
   - VPC networking components

3. **Supporting Services**:
   - Amazon ECR for container images
   - AWS Secrets Manager for credentials
   - Amazon S3 for storage
   - CloudWatch for monitoring

All components are deployed and managed through infrastructure as code and CI/CD pipelines.

## Prerequisites

Before deploying the Borrow Rate & Locate Fee Pricing Engine, ensure the following prerequisites are met.

### Required Tools

The following tools are required for deployment operations:

| Tool | Version | Purpose |
|------|---------|----------|
| AWS CLI | 2.13.0+ | AWS resource management |
| kubectl | 1.28.0+ | Kubernetes management |
| Terraform | 1.6.0+ | Infrastructure provisioning |
| Helm | 3.12.0+ | Kubernetes application deployment |
| Docker | 24.0.0+ | Container management |
| Git | 2.40.0+ | Source code management |

Ensure these tools are installed and properly configured before proceeding with deployment operations.

### Access Requirements

The following access is required for deployment operations:

1. **AWS Account Access**:
   - IAM credentials with appropriate permissions
   - Access to the relevant AWS accounts (dev, staging, prod)
   - MFA enabled for production access

2. **Kubernetes Access**:
   - kubeconfig for each environment's EKS cluster
   - Appropriate RBAC permissions

3. **CI/CD Access**:
   - GitHub repository access
   - CI/CD pipeline permissions

4. **Container Registry Access**:
   - ECR repository access for pushing/pulling images

Access should be granted following the principle of least privilege, with elevated access provided only as needed for specific operations.

### Infrastructure Requirements

The following infrastructure must be provisioned before deployment:

1. **AWS Resources**:
   - VPC with appropriate subnets
   - EKS cluster
   - RDS PostgreSQL instance
   - ElastiCache Redis cluster
   - Load balancer and target groups
   - S3 buckets for storage
   - Secrets Manager for credentials

2. **Kubernetes Resources**:
   - Namespaces for each environment
   - Service accounts with appropriate permissions
   - Storage classes for persistent volumes
   - Ingress controller

3. **Monitoring Infrastructure**:
   - Prometheus and Grafana
   - Loki for log aggregation
   - Tempo for distributed tracing
   - Alertmanager for notifications

The infrastructure is provisioned using Terraform scripts in the `infrastructure/` directory.

### Security Requirements

The following security requirements must be met before deployment:

1. **Network Security**:
   - VPC security groups configured
   - Network ACLs in place
   - Private subnets for sensitive components
   - VPN or bastion host for secure access

2. **Authentication and Authorization**:
   - IAM roles and policies configured
   - Kubernetes RBAC policies defined
   - Service account permissions set
   - Secrets management configured

3. **Data Protection**:
   - Encryption at rest enabled for databases
   - TLS certificates for in-transit encryption
   - Sensitive data identified and protected
   - Backup and recovery procedures in place

4. **Compliance**:
   - Audit logging enabled
   - Compliance controls verified
   - Security scanning integrated into pipeline

All security requirements must be validated before production deployment.

## Infrastructure Provisioning

This section covers the provisioning of infrastructure required for the Borrow Rate & Locate Fee Pricing Engine.

### Terraform Configuration

Infrastructure is provisioned using Terraform with configurations in the `src/backend/infrastructure/` directory:

```bash
# Initialize Terraform
cd src/backend/infrastructure
terraform init -backend-config=environments/${ENV}/backend.tfvars

# Plan infrastructure changes
terraform plan -var-file=environments/${ENV}/terraform.tfvars -out=tfplan

# Apply infrastructure changes
terraform apply tfplan
```

The Terraform configuration is organized into modules:
- `vpc.ts`: Network infrastructure
- `security_groups.ts`: Security group definitions
- `eks.ts`: Kubernetes cluster configuration
- `rds.ts`: Database configuration
- `redis.ts`: Cache configuration
- `cloudwatch.ts`: Monitoring configuration

Environment-specific variables are stored in `environments/${ENV}/terraform.tfvars`.

### AWS Resources

The following AWS resources are provisioned for each environment:

1. **Networking**:
   - VPC with CIDR block 10.0.0.0/16
   - Public and private subnets across 3 availability zones
   - NAT gateways for outbound connectivity
   - Internet gateway for inbound traffic
   - Route tables and network ACLs

2. **Compute**:
   - EKS cluster with managed node groups
   - EC2 instances for Kubernetes nodes
   - Auto Scaling groups for node management

3. **Database**:
   - RDS PostgreSQL with Multi-AZ deployment
   - Parameter groups for database configuration
   - Subnet groups for network placement
   - Security groups for access control

4. **Caching**:
   - ElastiCache Redis cluster
   - Parameter groups for Redis configuration
   - Subnet groups for network placement
   - Security groups for access control

5. **Supporting Services**:
   - ECR repositories for container images
   - S3 buckets for storage and logs
   - CloudWatch log groups and metrics
   - Secrets Manager for credential storage

Resource sizing varies by environment, with production sized for high availability and performance.

### Kubernetes Setup

After provisioning the EKS cluster, additional Kubernetes resources are configured:

```bash
# Configure kubectl for the EKS cluster
aws eks update-kubeconfig --name borrow-rate-engine-${ENV} --region us-east-1

# Create namespaces
kubectl apply -f infrastructure/kubernetes/base/namespace.yaml

# Deploy core infrastructure components
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts

# Install monitoring stack
helm install prometheus prometheus-community/prometheus -n monitoring -f infrastructure/monitoring/prometheus-values.yaml
helm install grafana grafana/grafana -n monitoring -f infrastructure/monitoring/grafana-values.yaml
```

The Kubernetes setup includes:
- Namespaces for application and monitoring
- RBAC configurations for service accounts
- Storage classes for persistent volumes
- Ingress controller for external access
- Monitoring stack (Prometheus, Grafana, Loki, Tempo)

These resources provide the foundation for deploying the application services.

### Database Initialization

After provisioning the RDS instance, the database is initialized:

```bash
# Run database migrations
kubectl run -it --rm db-init --image=${ECR_REPO}/borrow-rate-engine:${VERSION} --restart=Never -- python -m scripts.run_migrations --command upgrade

# Seed initial data
kubectl run -it --rm db-seed --image=${ECR_REPO}/borrow-rate-engine:${VERSION} --restart=Never -- python -m scripts.seed_data
```

The initialization process includes:
1. Creating database schema using migrations
2. Seeding reference data (stock metadata, broker configurations)
3. Setting up database users and permissions
4. Configuring database parameters for optimal performance

Database initialization is performed once per environment, with subsequent deployments using migrations for schema updates.

### Secrets Management

Sensitive configuration is managed using AWS Secrets Manager and Kubernetes Secrets:

```bash
# Create secrets in AWS Secrets Manager
aws secretsmanager create-secret --name borrow-rate-engine/${ENV}/database-credentials --secret-string '{"username":"admin","password":"REDACTED","host":"db.example.com","port":5432,"database":"borrow_rate_engine"}'

# Create Kubernetes secrets from AWS Secrets Manager
kubectl create secret generic database-credentials --from-literal=url="postgresql://admin:REDACTED@db.example.com:5432/borrow_rate_engine"
```

Secrets management includes:
1. Storing credentials in AWS Secrets Manager
2. Creating Kubernetes secrets for application access
3. Configuring service accounts with appropriate permissions
4. Rotating credentials according to security policies

All sensitive information is encrypted at rest and in transit, with access limited to authorized services and users.

## Application Deployment

This section covers the deployment of the Borrow Rate & Locate Fee Pricing Engine application components.

### Container Image Building

Container images are built and pushed to Amazon ECR:

```bash
# Login to Amazon ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

# Build container image
docker build -t borrow-rate-engine:${VERSION} -f src/backend/Dockerfile src/backend/

# Tag and push to ECR
docker tag borrow-rate-engine:${VERSION} ${ECR_REPO}/borrow-rate-engine:${VERSION}
docker push ${ECR_REPO}/borrow-rate-engine:${VERSION}
```

The container build process:
1. Uses multi-stage builds for efficiency
2. Installs only production dependencies
3. Runs as a non-root user for security
4. Includes health check endpoints
5. Optimizes layer caching

Images are tagged with semantic versions (e.g., 1.2.3) and the git commit SHA for traceability.

### Kubernetes Deployment

Application services are deployed to Kubernetes using Kustomize:

```bash
# Update kustomization.yaml with image tag
cd infrastructure/kubernetes/overlays/${ENV}
sed -i "s|image: .*|image: ${ECR_REPO}/borrow-rate-engine:${VERSION}|g" kustomization.yaml

# Apply Kubernetes manifests
kubectl apply -k infrastructure/kubernetes/overlays/${ENV}

# Verify deployment
kubectl rollout status deployment/api-gateway -n borrow-rate-engine-${ENV}
kubectl rollout status deployment/calculation-service -n borrow-rate-engine-${ENV}
kubectl rollout status deployment/data-service -n borrow-rate-engine-${ENV}
kubectl rollout status deployment/cache-service -n borrow-rate-engine-${ENV}
kubectl rollout status deployment/audit-service -n borrow-rate-engine-${ENV}
```

The deployment includes:
1. API Gateway service
2. Calculation Service
3. Data Service
4. Cache Service
5. Audit Service

Each service is configured with appropriate resource requests/limits, health checks, and scaling parameters.

### Configuration Management

Application configuration is managed through Kubernetes ConfigMaps:

```bash
# View current configuration
kubectl get configmap api-gateway-config -n borrow-rate-engine-${ENV} -o yaml

# Update configuration
kubectl apply -f infrastructure/kubernetes/overlays/${ENV}/configmap-patch.yaml
```

Configuration management includes:
1. Base configuration in `infrastructure/kubernetes/base/configmap.yaml`
2. Environment-specific overrides in overlay directories
3. Sensitive configuration in Kubernetes Secrets
4. Runtime configuration via environment variables

Configuration changes follow the same deployment process as code changes, ensuring consistency and traceability.

### Database Migrations

Database schema changes are applied using migrations:

```bash
# Run database migrations
kubectl exec -it deployment/api-gateway -n borrow-rate-engine-${ENV} -- python -m scripts.run_migrations --command upgrade

# Verify migration status
kubectl exec -it deployment/api-gateway -n borrow-rate-engine-${ENV} -- python -m scripts.run_migrations --command status
```

The migration process:
1. Creates a database backup before migration
2. Applies schema changes using Alembic
3. Verifies migration success
4. Includes rollback capability if needed

Migrations are versioned and tracked in source control, ensuring consistent database schema across environments.

### Canary Deployment

Production deployments use a canary approach to minimize risk:

```bash
# Deploy canary version (10% of traffic)
kubectl apply -f - <<EOF
apiVersion: split.smi-spec.io/v1alpha1
kind: TrafficSplit
metadata:
  name: api-gateway-split
  namespace: borrow-rate-engine-prod
spec:
  service: api-gateway
  backends:
  - service: api-gateway-stable
    weight: 90
  - service: api-gateway-canary
    weight: 10
EOF

# Monitor canary health
kubectl logs -l app=api-gateway-canary -n borrow-rate-engine-prod --tail=100

# Increase canary traffic (30%)
kubectl apply -f - <<EOF
apiVersion: split.smi-spec.io/v1alpha1
kind: TrafficSplit
metadata:
  name: api-gateway-split
  namespace: borrow-rate-engine-prod
spec:
  service: api-gateway
  backends:
  - service: api-gateway-stable
    weight: 70
  - service: api-gateway-canary
    weight: 30
EOF
```

The canary deployment process:
1. Deploy new version to canary pods
2. Route a small percentage of traffic to canary
3. Monitor for errors and performance issues
4. Gradually increase traffic if stable
5. Complete rollout when confidence is high

Canary deployments are used only in production; development and staging use standard rolling updates.

### Post-Deployment Validation

After deployment, validation tests verify system functionality:

```bash
# Run smoke tests
src/test/scripts/run_smoke_tests.sh --environment ${ENV}

# Run integration tests (staging/prod only)
src/test/scripts/run_integration_tests.sh --environment ${ENV} --subset critical

# Verify external API connectivity
kubectl exec -it deployment/data-service -n borrow-rate-engine-${ENV} -- curl -s http://localhost:8000/health/external
```

Validation includes:
1. Smoke tests for basic functionality
2. Integration tests for critical flows
3. Health check verification
4. External API connectivity tests
5. Performance validation

Failed validation triggers automatic rollback in staging and production environments.

## Deployment Automation

This section covers the automated deployment pipelines for the Borrow Rate & Locate Fee Pricing Engine.

### CI/CD Pipeline Overview

Deployments are automated through GitHub Actions workflows:

```mermaid
flowchart TD
    A[Code Push] --> B{Branch Type?}
    B -->|Feature Branch| C[Build & Unit Test]
    B -->|Main Branch| D[Build & Full Test Suite]
    
    C --> E[Deploy to Development]
    D --> F[Deploy to Staging]
    
    F --> G[Integration Tests]
    G -->|Pass| H[Manual Approval]
    G -->|Fail| I[Create Issue]
    
    H -->|Approved| J[Deploy to Production]
    
    J --> K[Post-Deployment Monitoring]
```

The CI/CD pipeline includes:
1. Automated testing on all code changes
2. Automatic deployment to development for feature branches
3. Automatic deployment to staging for main branch
4. Manual approval for production deployment
5. Canary deployment for production
6. Automated rollback for failed deployments

### Development Deployment

Development deployments are triggered automatically for feature branches:

```yaml
# .github/workflows/deploy-dev.yml
name: Deploy to Development

on:
  push:
    branches:
      - 'feature/**'

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and test
        run: |
          # Build and test steps
          
  deploy-to-dev:
    needs: build-and-test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Deploy to development
        run: |
          # Deployment steps
```

Development deployments:
1. Are triggered on push to feature branches
2. Run unit tests before deployment
3. Deploy to the development environment
4. Use rolling updates for deployment
5. Do not require manual approval

### Staging Deployment

Staging deployments are triggered automatically for the main branch:

```yaml
# .github/workflows/deploy-staging.yml
name: Deploy to Staging

on:
  push:
    branches:
      - main

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and test
        run: |
          # Build and test steps
          
  deploy-to-staging:
    needs: build-and-test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Deploy to staging
        run: |
          # Deployment steps
          
  integration-tests:
    needs: deploy-to-staging
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run integration tests
        run: |
          # Integration test steps
```

Staging deployments:
1. Are triggered on push to main branch
2. Run full test suite before deployment
3. Deploy to the staging environment
4. Run integration tests after deployment
5. Automatically roll back on test failure
6. Serve as validation for production readiness

### Production Deployment

Production deployments require manual approval and use a canary approach:

```yaml
# .github/workflows/deploy-prod.yml
name: Deploy to Production

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version tag to deploy'
        required: true
      approved_by:
        description: 'Name of person who approved the deployment'
        required: true

jobs:
  approval-check:
    runs-on: ubuntu-latest
    steps:
      - name: Verify approval
        run: echo "Deployment to production approved by ${{ github.event.inputs.approved_by }}"
        
  pre-deployment-validation:
    needs: approval-check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Verify image exists
        run: |
          # Verification steps
          
  database-backup:
    needs: pre-deployment-validation
    runs-on: ubuntu-latest
    steps:
      - name: Create database snapshot
        run: |
          # Backup steps
          
  deploy-canary:
    needs: database-backup
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy canary (10% traffic)
        run: |
          # Canary deployment steps
          
  deploy-full:
    needs: deploy-canary
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Complete deployment
        run: |
          # Full deployment steps
```

Production deployments:
1. Are triggered manually with version and approver
2. Require pre-deployment validation
3. Create database backup before deployment
4. Use canary deployment approach
5. Include post-deployment monitoring
6. Have automated rollback capability

### Rollback Procedures

Automated rollback is implemented for failed deployments:

```yaml
# Rollback job in deploy-prod.yml
rollback:
  runs-on: ubuntu-latest
  needs: [deploy-full, database-backup]
  if: failure()
  steps:
    - uses: actions/checkout@v3
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    - name: Get previous version
      id: prev-version
      run: |
        PREV_VERSION=$(aws ssm get-parameter --name /borrow-rate-engine/production/deployed-version --query 'Parameter.Value' --output text)
        echo "::set-output name=version::$PREV_VERSION"
    - name: Rollback deployment
      run: |
        kubectl rollout undo deployment/api-gateway -n borrow-rate-engine-prod
        kubectl rollout undo deployment/calculation-service -n borrow-rate-engine-prod
        kubectl rollout undo deployment/data-service -n borrow-rate-engine-prod
        kubectl rollout undo deployment/cache-service -n borrow-rate-engine-prod
        kubectl rollout undo deployment/audit-service -n borrow-rate-engine-prod
```

Rollback procedures:
1. Are triggered automatically on deployment failure
2. Revert to the previous stable version
3. Restore database if necessary
4. Verify system functionality after rollback
5. Notify stakeholders of rollback

Manual rollback can also be initiated if issues are detected after deployment.

### Deployment Notifications

Deployment status is communicated through notifications:

```yaml
# Notification steps in deploy-prod.yml
- name: Notify Deployment Success
  if: success()
  uses: slackapi/slack-github-action@v1.23.0
  with:
    channel-id: "${{ secrets.SLACK_PROD_CHANNEL_ID }}"
    payload: '{"text":"✅ Production deployment of version ${{ github.event.inputs.version }} completed successfully."}'  
  env:
    SLACK_BOT_TOKEN: "${{ secrets.SLACK_BOT_TOKEN }}"
    
- name: Notify Deployment Failure
  if: failure()
  uses: slackapi/slack-github-action@v1.23.0
  with:
    channel-id: "${{ secrets.SLACK_PROD_CHANNEL_ID }}"
    payload: '{"text":"❌ Production deployment of version ${{ github.event.inputs.version }} failed. <https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}|View details>"}'  
  env:
    SLACK_BOT_TOKEN: "${{ secrets.SLACK_BOT_TOKEN }}"
```

Deployment notifications:
1. Are sent to Slack channels for team visibility
2. Include deployment version and status
3. Provide links to detailed logs
4. Alert on-call personnel for failures
5. Update deployment status in monitoring systems

## Scaling Configuration

This section covers the scaling configuration for the Borrow Rate & Locate Fee Pricing Engine.

### Horizontal Pod Autoscaling

Services are configured with Horizontal Pod Autoscalers (HPAs) for automatic scaling:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

HPA configurations:
- API Gateway: CPU-based scaling, 3-10 replicas
- Calculation Service: Custom metric (requests/sec) and CPU, 3-20 replicas
- Data Service: CPU-based scaling, 3-10 replicas
- Cache Service: Memory-based scaling, 3-5 replicas
- Audit Service: CPU-based scaling, 2-5 replicas

These scaling configurations ensure the system can handle varying load levels while maintaining performance and cost efficiency.

### Resource Allocation

Services are configured with appropriate resource requests and limits:

```yaml
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 4Gi
```

Resource allocations:
- API Gateway: 500m-2000m CPU, 1Gi-4Gi memory
- Calculation Service: 1000m-4000m CPU, 2Gi-8Gi memory
- Data Service: 500m-2000m CPU, 1.5Gi-6Gi memory
- Cache Service: 1000m-4000m CPU, 4Gi-16Gi memory
- Audit Service: 500m-1000m CPU, 1Gi-2Gi memory

These allocations are based on performance testing and production load analysis. They provide sufficient resources for normal operation while allowing for bursts of activity without disruption.

### Cluster Autoscaler

The Kubernetes Cluster Autoscaler is configured to automatically adjust the number of nodes:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-autoscaler-config
data:
  config: |
    {
      "min-nodes": 3,
      "max-nodes": 20,
      "scale-down-unneeded-time": "10m",
      "scale-down-delay-after-add": "10m",
      "scale-down-utilization-threshold": 0.5
    }
```

Cluster Autoscaler configuration:
- Development: 2-5 nodes
- Staging: 3-10 nodes
- Production: 3-20 nodes

The autoscaler ensures sufficient nodes are available to schedule all pods while avoiding over-provisioning. It scales up quickly when needed and scales down conservatively to minimize disruption.

### Database Scaling

The PostgreSQL database is scaled using AWS RDS features:

1. **Vertical Scaling**:
   - Development: db.t3.medium (2 vCPU, 4 GiB RAM)
   - Staging: db.r5.large (2 vCPU, 16 GiB RAM)
   - Production: db.r5.xlarge (4 vCPU, 32 GiB RAM)

2. **Read Replicas**:
   - Development: None
   - Staging: 1 replica
   - Production: 2 replicas across AZs

3. **Connection Pooling**:
   - PgBouncer deployed for connection management
   - Connection limits configured based on environment

Database scaling operations are performed during maintenance windows to minimize impact. For scaling procedures, refer to AWS RDS documentation and internal runbooks for detailed steps.

### Cache Scaling

The Redis cache is scaled using AWS ElastiCache features:

1. **Vertical Scaling**:
   - Development: cache.t3.small (2 vCPU, 1.5 GiB RAM)
   - Staging: cache.m5.large (2 vCPU, 6.4 GiB RAM)
   - Production: cache.m5.xlarge (4 vCPU, 12.9 GiB RAM)

2. **Replication**:
   - Development: Single node
   - Staging: 1 primary, 1 replica
   - Production: 1 primary, 2 replicas across AZs

3. **Cluster Mode**:
   - Disabled for development and staging
   - Enabled for production with 3 shards

Cache scaling is managed through Terraform configuration changes. The cache is designed to handle high throughput and low latency requirements for the pricing engine with appropriate redundancy in production.

## Monitoring and Alerting

This section covers the monitoring and alerting configuration for the Borrow Rate & Locate Fee Pricing Engine.

### Monitoring Stack

The monitoring stack includes:

1. **Prometheus**: Collects and stores time-series metrics
2. **Grafana**: Provides visualization through dashboards
3. **Loki**: Aggregates and indexes logs from all services
4. **Tempo**: Stores and analyzes distributed traces
5. **Alertmanager**: Routes alerts to appropriate channels

The monitoring stack is deployed in the `monitoring` namespace using Helm charts. This comprehensive monitoring infrastructure provides visibility into system performance, availability, and business metrics.

### Health Checks

All services implement health check endpoints:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 20
  timeoutSeconds: 5
  failureThreshold: 3
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 3
  failureThreshold: 2
```

Health checks include:
- Basic health check: `/health`
- Detailed health check: `/health/details`
- External dependency check: `/health/external`

Kubernetes uses these health checks to determine pod readiness and liveness.

### Metrics Collection

Services expose metrics for collection by Prometheus:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

Key metrics include:
- Request rate, latency, and error rate
- Resource utilization (CPU, memory)
- Business metrics (calculation volume, fee amounts)
- External API performance
- Cache hit rates

These metrics are visualized in Grafana dashboards and used for alerting.

### Log Aggregation

Logs are collected using Fluent Bit and stored in Loki:

```yaml
# Fluent Bit configuration
[INPUT]
    Name tail
    Path /var/log/containers/*.log
    Parser docker
    Tag kube.*

[OUTPUT]
    Name loki
    Match kube.*
    Host loki.monitoring.svc.cluster.local
    Port 3100
    Labels {job="fluentbit"}
    Label_keys $kubernetes['namespace_name'],$kubernetes['pod_name'],$kubernetes['container_name']
```

Log levels are configured based on environment:
- Development: DEBUG
- Staging: INFO
- Production: INFO (with DEBUG available on demand)

Logs are retained according to the data retention policy.

### Alerting Configuration

Alerts are configured in Prometheus and routed through Alertmanager:

```yaml
groups:
- name: api-gateway
  rules:
  - alert: HighErrorRate
    expr: sum(rate(http_requests_total{job="api-gateway",status=~"5.."}[5m])) / sum(rate(http_requests_total{job="api-gateway"}[5m])) > 0.01
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: High error rate on API Gateway
      description: Error rate is above 1% for 5 minutes
```

Alert severity levels:
- P1 (Critical): Immediate response required
- P2 (High): Response within 30 minutes
- P3 (Medium): Response within 2 hours
- P4 (Low): Response during business hours

Alerts are routed to appropriate channels based on severity and type.

### Dashboards

Grafana dashboards provide visibility into system performance:

1. **Executive Dashboard**: High-level system health and business metrics
2. **Operational Dashboard**: Real-time monitoring for operations teams
3. **Technical Dashboard**: Detailed metrics for engineering teams
4. **Service-Specific Dashboards**: Focused views of individual services

Dashboards are provisioned through configuration and stored as code in the repository.

## Maintenance Procedures

This section covers maintenance procedures for the Borrow Rate & Locate Fee Pricing Engine.

### Routine Maintenance

Routine maintenance tasks include:

1. **OS Patching**:
   - Performed monthly during maintenance window
   - Rolling updates to minimize impact
   - Scheduled 48 hours in advance

2. **Database Maintenance**:
   - Performed quarterly during maintenance window
   - Includes index optimization and vacuum operations
   - May require 5-10 minutes of downtime

3. **Kubernetes Upgrades**:
   - Performed quarterly during maintenance window
   - Control plane upgraded first, then node groups
   - Rolling updates to minimize impact

4. **Certificate Rotation**:
   - TLS certificates renewed 30 days before expiration
   - Automated through cert-manager
   - Zero-downtime rotation

Maintenance windows:
- Development: Weekdays 10:00-14:00 EST
- Staging: Weekdays 22:00-02:00 EST
- Production: Weekends 01:00-05:00 EST

### Backup and Recovery

Backup and recovery procedures include:

1. **Database Backups**:
   - Automated daily snapshots with 30-day retention
   - Point-in-time recovery enabled
   - Manual snapshots before major changes
   - Monthly recovery testing

2. **Configuration Backups**:
   - Infrastructure as code in version control
   - Kubernetes manifests in version control
   - Secrets backed up in AWS Secrets Manager
   - Regular validation of backup integrity

3. **Recovery Procedures**:
   - RTO (Recovery Time Objective): <15 minutes
   - RPO (Recovery Point Objective): <5 minutes
   - Documented recovery playbooks
   - Regular disaster recovery drills

To restore from backup:

```bash
# Restore database from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier borrow-rate-engine-${ENV}-restored \
  --db-snapshot-identifier ${SNAPSHOT_ID}

# Update database connection in Kubernetes
kubectl create secret generic database-credentials \
  --from-literal=url="postgresql://admin:password@borrow-rate-engine-${ENV}-restored.example.com:5432/borrow_rate_engine" \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart services to use new database
kubectl rollout restart deployment -n borrow-rate-engine-${ENV}
```

### Scaling Operations

Manual scaling operations may be required for anticipated load increases:

1. **Horizontal Scaling**:
   - Adjust HPA min/max replicas
   - Increase node group size if needed
   - Monitor resource utilization during scaling

```bash
# Update HPA configuration
kubectl patch hpa calculation-service-hpa -n borrow-rate-engine-${ENV} \
  --patch '{"spec":{"minReplicas":5,"maxReplicas":30}}'

# Scale node group
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name ${NODE_GROUP_NAME} \
  --min-size 5 --max-size 30
```

2. **Vertical Scaling**:
   - Database instance type changes
   - Cache instance type changes
   - Resource request/limit adjustments

```bash
# Update database instance type
aws rds modify-db-instance \
  --db-instance-identifier borrow-rate-engine-${ENV} \
  --db-instance-class db.r5.2xlarge \
  --apply-immediately
```

Detailed scaling procedures are documented in the operations runbooks for each component.

### Troubleshooting

Common troubleshooting procedures include:

1. **Service Issues**:
   - Check pod status and logs
   - Verify health check endpoints
   - Examine resource utilization
   - Check for recent changes

```bash
# Check pod status
kubectl get pods -n borrow-rate-engine-${ENV}

# View logs
kubectl logs deployment/api-gateway -n borrow-rate-engine-${ENV}

# Check health endpoint
kubectl exec -it deployment/api-gateway -n borrow-rate-engine-${ENV} -- curl -s http://localhost:8000/health
```

2. **Database Issues**:
   - Check connection pool status
   - Examine slow query logs
   - Verify replication status
   - Check for resource constraints

```bash
# Check database connections
kubectl exec -it deployment/api-gateway -n borrow-rate-engine-${ENV} -- python -c "import psycopg2; conn = psycopg2.connect('postgresql://admin:password@db.example.com:5432/borrow_rate_engine'); cur = conn.cursor(); cur.execute('SELECT count(*) FROM pg_stat_activity'); print(cur.fetchone()[0])"
```

3. **External API Issues**:
   - Check API status and logs
   - Verify credentials and rate limits
   - Examine circuit breaker status
   - Test direct API connectivity

```bash
# Check external API status
kubectl exec -it deployment/data-service -n borrow-rate-engine-${ENV} -- curl -s http://localhost:8000/health/external
```

Detailed troubleshooting guides are available in the runbooks directory.

### Version Management

Version management procedures include:

1. **Version Tracking**:
   - Semantic versioning (MAJOR.MINOR.PATCH)
   - Git tags for release versions
   - Version history in release notes
   - Deployment history in parameter store

```bash
# Get current deployed version
aws ssm get-parameter --name /borrow-rate-engine/${ENV}/deployed-version --query 'Parameter.Value' --output text

# Update deployed version
aws ssm put-parameter --name /borrow-rate-engine/${ENV}/deployed-version --value "${VERSION}" --type String --overwrite
```

2. **Rollback Planning**:
   - Identify compatible versions for rollback
   - Verify database schema compatibility
   - Test rollback procedures regularly
   - Document rollback decision criteria

3. **Hotfix Process**:
   - Create hotfix branch from production tag
   - Apply minimal fix with thorough testing
   - Deploy through standard pipeline with expedited approval
   - Merge changes back to main branch

Version management ensures traceability and supports reliable rollback when needed.

## Security Considerations

This section covers security considerations for deploying the Borrow Rate & Locate Fee Pricing Engine.

### Network Security

Network security measures include:

1. **VPC Configuration**:
   - Private subnets for application and data tiers
   - Public subnets only for load balancers and NAT gateways
   - Network ACLs for subnet-level filtering
   - Security groups for instance-level access control

2. **Access Controls**:
   - Bastion host for secure administrative access
   - VPN for remote access to internal resources
   - Jump server for database access
   - No direct internet access from application tier

3. **Traffic Encryption**:
   - TLS 1.2+ for all external traffic
   - TLS for internal service communication
   - VPC endpoint for AWS service access
   - Encryption for all cross-AZ traffic

Network security is implemented through Terraform and verified through regular security assessments.

### Authentication and Authorization

Authentication and authorization measures include:

1. **API Security**:
   - API key authentication for client access
   - JWT tokens for session management
   - Role-based access control for API endpoints
   - Rate limiting to prevent abuse

2. **Kubernetes Security**:
   - RBAC for Kubernetes access control
   - Service accounts with minimal permissions
   - Pod security policies
   - Network policies for pod-to-pod communication

3. **AWS Security**:
   - IAM roles with least privilege
   - MFA for human users
   - Temporary credentials for automated processes
   - Regular access reviews

Authentication and authorization are configured through infrastructure as code and regularly audited.

### Data Protection

Data protection measures include:

1. **Encryption at Rest**:
   - RDS encryption using AWS KMS
   - ElastiCache encryption using AWS KMS
   - S3 bucket encryption
   - EBS volume encryption

2. **Encryption in Transit**:
   - TLS for all API communication
   - TLS for database connections
   - TLS for cache connections
   - VPC encryption for internal traffic

3. **Sensitive Data Handling**:
   - Secrets management using AWS Secrets Manager
   - Kubernetes Secrets for application credentials
   - Data classification and handling procedures
   - Secure logging practices (masking sensitive data)

Data protection is implemented through infrastructure configuration and application design.

### Vulnerability Management

Vulnerability management procedures include:

1. **Container Security**:
   - Image scanning in CI/CD pipeline
   - Regular base image updates
   - Minimal container images
   - Non-root container execution

2. **Dependency Management**:
   - Automated dependency scanning
   - Regular dependency updates
   - Vulnerability tracking and remediation
   - Software bill of materials (SBOM) generation

3. **Patch Management**:
   - Regular OS patching
   - Automated security updates
   - Critical vulnerability expedited patching
   - Patch compliance monitoring

Vulnerability management is integrated into the development and deployment lifecycle.

### Compliance Controls

Compliance controls include:

1. **Audit Logging**:
   - Comprehensive audit trails
   - Immutable log storage
   - Access logging for all systems
   - Regular log reviews

2. **Access Reviews**:
   - Quarterly access reviews
   - Privilege management
   - Separation of duties
   - Just-in-time access for administrative functions

3. **Change Management**:
   - Documented change procedures
   - Change approval process
   - Change impact assessment
   - Post-change verification

Compliance controls are documented and regularly validated through internal and external audits.

## References

Additional resources for deployment information.

### Internal Documentation

- [Architecture Overview](../architecture/overview.md)
- [API Design](../architecture/api-design.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [Backup and Recovery](./backup-recovery.md)

### External Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Terraform Documentation](https://www.terraform.io/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

### Contact Information

For deployment assistance, contact:

- DevOps Team: devops@example.com
- On-call Engineer: +1-555-123-4567
- Slack Channel: #deployment-support