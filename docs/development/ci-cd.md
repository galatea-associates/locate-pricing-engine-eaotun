# CI/CD Pipeline Documentation

This document provides comprehensive documentation for the Continuous Integration and Continuous Deployment (CI/CD) pipeline of the Borrow Rate & Locate Fee Pricing Engine. The pipeline automates the build, test, and deployment processes to ensure consistent, reliable, and secure releases across all environments.

## Purpose and Benefits

The CI/CD pipeline serves several critical purposes:

- **Automation**: Eliminates manual steps in the build and deployment process
- **Consistency**: Ensures the same process is followed for every code change
- **Quality Assurance**: Enforces code quality standards and test coverage requirements
- **Security**: Integrates security scanning at multiple stages
- **Traceability**: Provides a complete audit trail of all changes and deployments
- **Reliability**: Implements safe deployment strategies with automated validation and rollback

By following this CI/CD approach, we achieve faster, more reliable releases while maintaining high quality and security standards for this critical financial system.

# CI/CD Architecture

## Overview

The CI/CD pipeline is built on GitHub Actions and integrates with AWS services to provide a complete workflow from code commit to production deployment. The pipeline is designed to support multiple environments with appropriate controls and validations at each stage.

## Key Components

- **Source Control**: GitHub repositories with branch protection rules
- **CI/CD Platform**: GitHub Actions for workflow automation
- **Container Registry**: Amazon ECR for storing Docker images
- **Orchestration**: Amazon EKS (Kubernetes) for container orchestration
- **Configuration Management**: Kubernetes manifests and Helm charts
- **Secret Management**: AWS Secrets Manager and Kubernetes Secrets
- **Monitoring**: AWS CloudWatch, Prometheus, and Grafana

## Environment Structure

The pipeline supports three distinct environments:

1. **Development**: Automatic deployment from feature branches and develop branch
2. **Staging**: Automatic deployment from main branch after tests pass
3. **Production**: Manual approval-based deployment with canary strategy

## Workflow Stages

1. **Build**: Compile code, run tests, build container images
2. **Validation**: Code quality checks, security scanning, test coverage verification
3. **Deployment**: Environment-specific deployment with appropriate strategies
4. **Verification**: Post-deployment testing and validation
5. **Monitoring**: Ongoing monitoring of deployed services

## CI/CD Pipeline Diagram

```
Code Commit → Build → Test → Security Scan → Container Build → Development Deployment → Integration Tests → Staging Deployment → E2E Tests → Manual Approval → Production Deployment (Canary) → Production Verification → Full Production Release
```

# Build Pipeline

## Overview

The build pipeline is implemented in `.github/workflows/build.yml` and is triggered on every push to feature branches, develop branch, and main branch, as well as on pull requests to develop and main branches.

## Pipeline Stages

### 1. Code Quality

This stage performs static code analysis and formatting checks:

- **Linting**: Uses flake8 to check for code style issues
- **Formatting**: Verifies code formatting with black and isort
- **Type Checking**: Validates type annotations with mypy

### 2. Unit Tests

This stage runs unit tests and verifies code coverage:

- **Test Execution**: Runs pytest with pytest-cov for coverage reporting
- **Coverage Verification**: Ensures code coverage meets the 90% threshold
- **Test Report**: Generates and uploads test reports as artifacts

### 3. Security Scan

This stage scans the code and dependencies for security vulnerabilities:

- **Dependency Scanning**: Uses Snyk to check for vulnerabilities in Python dependencies
- **Severity Threshold**: Fails the build on high or critical vulnerabilities

### 4. Container Build

This stage builds and pushes Docker container images:

- **Build Setup**: Configures Docker Buildx for efficient builds
- **Metadata Extraction**: Generates image tags based on Git commit SHA
- **Build and Push**: Builds the container image and pushes to Amazon ECR
- **Image Scanning**: Scans the built image for vulnerabilities

## Quality Gates

The build pipeline enforces several quality gates that must be passed before proceeding:

1. All linting and formatting checks must pass
2. All unit tests must pass
3. Code coverage must be at least 90%
4. No high or critical security vulnerabilities in dependencies
5. Container image must pass security scanning

## Configuration

The build pipeline uses the following key configurations:

- **Python Version**: 3.11
- **Docker Registry**: Amazon ECR
- **Image Naming**: borrow-rate-engine:[git-sha]
- **Caching**: Dependency and Docker layer caching for performance

## Outputs

The build pipeline produces the following outputs that are used by downstream workflows:

- **Container Image**: Tagged Docker image in Amazon ECR
- **Image Digest**: SHA256 digest of the built image
- **Test Reports**: Coverage reports and test results

## Example Usage

```yaml
# Trigger the build workflow manually
name: Build and Test
on:
  workflow_dispatch:

# Reference the build workflow from another workflow
jobs:
  deploy:
    needs: [build-image]
    runs-on: ubuntu-latest
    steps:
      - name: Deploy image
        run: echo "Deploying image ${{ needs.build-image.outputs.image }}"
```

# Deployment Pipelines

## Development Environment

### Overview

The development deployment pipeline (`.github/workflows/deploy-dev.yml`) automatically deploys code changes to the development environment. It is triggered on pushes to the develop branch and feature branches, as well as manually via workflow dispatch.

### Key Features

- **Automatic Deployment**: No manual approval required
- **Deployment Strategy**: Rolling update with zero downtime
- **Database Migrations**: Automatically runs migrations after deployment
- **Smoke Tests**: Verifies basic functionality after deployment
- **Notification**: Updates PR with deployment status

### Configuration

- **Kubernetes Namespace**: borrow-rate-engine-dev
- **Resource Limits**: Lower resource allocations for cost optimization
- **Replicas**: Minimum 2 replicas for basic availability

## Staging Environment

### Overview

The staging deployment pipeline (`.github/workflows/deploy-staging.yml`) deploys code changes to the staging environment, which mirrors the production configuration. It is triggered on pushes to the main branch and manually via workflow dispatch.

### Key Features

- **Automatic Deployment**: Triggered after successful merge to main
- **Deployment Strategy**: Rolling update with zero downtime
- **Database Backup**: Takes a database snapshot before deployment
- **Integration Tests**: Runs comprehensive integration tests after deployment
- **E2E Tests**: Executes end-to-end tests to verify functionality
- **Deployment Record**: Creates a GitHub deployment record for tracking

### Configuration

- **Kubernetes Namespace**: borrow-rate-engine-staging
- **Resource Limits**: Production-like resource allocations
- **Replicas**: Minimum 3 replicas for high availability

## Production Environment

### Overview

The production deployment pipeline (`.github/workflows/deploy-prod.yml`) deploys code changes to the production environment with strict controls and validation. It is triggered only manually via workflow dispatch with required approval information.

### Key Features

- **Manual Approval**: Requires explicit approval with approver name
- **Pre-deployment Validation**: Verifies all prerequisites are met
- **Database Backup**: Creates a full database snapshot before deployment
- **Canary Deployment**: Gradually rolls out changes with traffic shifting
- **Health Monitoring**: Continuously monitors the canary deployment
- **Automated Rollback**: Automatically rolls back on detected issues
- **Post-deployment Monitoring**: Extended monitoring after deployment

### Configuration

- **Kubernetes Namespace**: borrow-rate-engine-prod
- **Resource Limits**: Full production resource allocations
- **Replicas**: Minimum 3 replicas across multiple availability zones
- **Canary Strategy**: Initial 10% traffic, increasing to 30%, then 100%

## Common Features

All deployment pipelines share these common features:

- **Kubernetes Integration**: Uses kubectl and kustomize for deployments
- **AWS Authentication**: Configures AWS credentials for EKS access
- **Image Tagging**: Uses Git SHA or specified version tag
- **Deployment Verification**: Waits for successful rollout
- **Notification**: Sends deployment status notifications

## Deployment Configuration

Deployments are configured using Kubernetes manifests and Helm charts:

- **Base Configuration**: `infrastructure/kubernetes/base/`
- **Environment Overlays**: `infrastructure/kubernetes/overlays/{env}/`
- **Helm Values**: `infrastructure/helm/{service}/values.yaml`

# Environment Promotion Workflow

## Overview

The environment promotion workflow defines how code changes progress from development to production. This controlled process ensures that only thoroughly tested and validated changes reach production.

## Promotion Stages

### 1. Feature Development

- Developer creates a feature branch from develop
- Changes are committed and pushed to the feature branch
- Build workflow runs tests and quality checks
- Automatic deployment to development environment
- Developer tests changes in development environment

### 2. Integration

- Developer creates a pull request to the develop branch
- Code review is performed by team members
- Build workflow runs on the PR to verify compatibility
- After approval, PR is merged to develop
- Automatic deployment to development environment
- Integration testing in development environment

### 3. Staging Promotion

- Developer creates a PR from develop to main
- Code review is performed by team members
- Build workflow runs on the PR to verify compatibility
- After approval, PR is merged to main
- Automatic deployment to staging environment
- Full test suite runs in staging environment
- Performance and security testing in staging

### 4. Production Release

- Release manager initiates production deployment via workflow dispatch
- Required approvals are documented in the deployment trigger
- Pre-deployment validation verifies all prerequisites
- Canary deployment to production with gradual traffic shifting
- Monitoring and verification throughout the deployment
- Full production release after successful validation

## Approval Requirements

| Environment | Approval Required | Approver Role |
|-------------|-------------------|---------------|
| Development | No                | N/A           |
| Staging     | No                | N/A           |
| Production  | Yes               | Release Manager or Engineering Manager |

## Promotion Criteria

| From → To          | Criteria |
|--------------------|----------|
| Feature → Develop  | - All tests pass<br>- Code review approval<br>- No security vulnerabilities |
| Develop → Main     | - All tests pass<br>- Code review approval<br>- No security vulnerabilities<br>- Feature acceptance by product owner |
| Main → Production  | - Successful staging deployment<br>- All integration and E2E tests pass<br>- Performance tests within thresholds<br>- Security approval<br>- Business approval |

## Hotfix Process

For urgent production issues, a modified workflow is available:

1. Create hotfix branch directly from main
2. Implement and test the fix
3. Create PR directly to main with detailed justification
4. After approval and merge, deploy to staging for validation
5. Deploy to production with optional skip-canary parameter for critical fixes

## Rollback Process

If issues are detected after promotion:

1. For development and staging: Revert the commit and let the automatic deployment process deploy the previous version
2. For production: Use the rollback job in the production deployment workflow, which restores the previous version and database state if necessary

# Deployment Strategies

## Overview

The Borrow Rate & Locate Fee Pricing Engine uses different deployment strategies for each environment to balance between development agility and production stability. This document explains the strategies used and their implementation details.

## Rolling Update Strategy

### Used In: Development and Staging Environments

Rolling updates gradually replace instances of the previous version with new instances, ensuring zero downtime during deployments.

### Implementation Details

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

- **maxSurge**: Allows creating at most one pod above the desired replica count
- **maxUnavailable**: Ensures no pods are unavailable during the update

### Benefits

- Zero downtime deployments
- Simple implementation and rollback
- Suitable for frequent deployments in development and staging

### Limitations

- All instances receive the update at once (no gradual traffic shifting)
- Potential for subtle issues that only appear under production load

## Canary Deployment Strategy

### Used In: Production Environment

Canary deployments involve deploying the new version to a small subset of instances first, then gradually increasing traffic to the new version while monitoring for issues.

### Implementation Details

1. **Initial Canary Deployment (10% traffic)**
   ```yaml
   # Deploy canary version
   kubectl apply -k $KUSTOMIZE_PATH -l canary=true
   
   # Configure traffic split
   kubectl apply -f - <<EOF
   apiVersion: split.smi-spec.io/v1alpha1
   kind: TrafficSplit
   metadata:
     name: api-gateway-split
   spec:
     service: api-gateway
     backends:
     - service: api-gateway-stable
       weight: 90
     - service: api-gateway-canary
       weight: 10
   EOF
   ```

2. **Increase Traffic (30% traffic)**
   ```yaml
   # Update traffic split
   kubectl apply -f - <<EOF
   apiVersion: split.smi-spec.io/v1alpha1
   kind: TrafficSplit
   metadata:
     name: api-gateway-split
   spec:
     service: api-gateway
     backends:
     - service: api-gateway-stable
       weight: 70
     - service: api-gateway-canary
       weight: 30
   EOF
   ```

3. **Full Deployment (100% traffic)**
   ```yaml
   # Deploy to all instances
   kubectl apply -k $KUSTOMIZE_PATH
   ```

### Benefits

- Gradual exposure of new version to users
- Early detection of issues with minimal impact
- Ability to abort deployment if issues are detected
- Reduced risk for critical financial system

### Limitations

- More complex implementation
- Longer deployment time
- Requires additional monitoring

## Blue-Green Deployment

### Used In: Database Migrations (When Needed)

For major database changes, a blue-green approach may be used where a completely new environment is created alongside the existing one, then traffic is switched over once ready.

### Implementation Details

1. Create new database instance from snapshot
2. Apply migrations to new instance
3. Verify migrations and data integrity
4. Update application configuration to point to new database
5. Deploy application with updated configuration
6. Verify functionality with new database
7. Decommission old database after successful verification

### Benefits

- Complete isolation between old and new database schema
- Ability to fully test migrations before affecting production
- Simple rollback by reverting configuration change

### Limitations

- Resource intensive (requires duplicate database)
- More complex coordination
- Only used for major database changes

## Deployment Verification

All deployment strategies include verification steps:

```yaml
# Verify deployment completion
kubectl rollout status deployment/api-gateway -n $NAMESPACE --timeout=300s

# Run smoke tests
src/test/scripts/run_smoke_tests.sh --environment production
```

## Rollback Procedures

Each strategy has corresponding rollback procedures:

- **Rolling Update**: `kubectl rollout undo deployment/api-gateway`
- **Canary**: Adjust traffic split to 100% stable, then remove canary
- **Blue-Green**: Revert configuration to point to original database

# Quality Gates

## Overview

Quality gates are checkpoints in the CI/CD pipeline that enforce quality standards and prevent substandard code from progressing to the next stage. The Borrow Rate & Locate Fee Pricing Engine implements multiple quality gates throughout the pipeline.

## Build Pipeline Quality Gates

### 1. Code Quality Gate

**Purpose**: Ensure code adheres to style guidelines and best practices

**Checks**:
- Linting with flake8
- Formatting with black and isort
- Type checking with mypy

**Passing Criteria**:
- Zero linting errors
- Code formatting matches standards
- Type annotations are valid

**Implementation**:
```yaml
run_linting:
  run: flake8 src/backend

check_formatting:
  run: black --check src/backend && isort --check src/backend

run_type_checking:
  run: mypy src/backend
```

### 2. Unit Test Gate

**Purpose**: Verify code functionality and prevent regressions

**Checks**:
- Unit test execution
- Code coverage measurement

**Passing Criteria**:
- All unit tests pass
- Code coverage ≥ 90% overall
- Core calculation logic has 100% coverage

**Implementation**:
```yaml
run_unit_tests:
  run: pytest src/backend/tests --cov=src/backend --cov-report=xml

check_coverage_thresholds:
  run: |
    python -c "import xml.etree.ElementTree as ET; 
    root = ET.parse('coverage.xml').getroot(); 
    coverage = float(root.get('line-rate')) * 100; 
    exit(1 if coverage < 90 else 0)"
```

### 3. Security Gate

**Purpose**: Identify and prevent security vulnerabilities

**Checks**:
- Dependency scanning with Snyk
- Container image scanning

**Passing Criteria**:
- No high or critical vulnerabilities in dependencies
- No high or critical vulnerabilities in container images

**Implementation**:
```yaml
run_snyk_to_check_for_vulnerabilities:
  uses: snyk/actions/python@v0.4.0
  with:
    command: test
    args: --severity-threshold=high

run_snyk_to_check_docker_image:
  uses: snyk/actions/docker@v0.4.0
  with:
    image: ${{ steps.meta.outputs.tags }}
    args: --severity-threshold=high
```

## Deployment Pipeline Quality Gates

### 4. Integration Test Gate

**Purpose**: Verify system components work together correctly

**Checks**:
- Integration test execution in staging environment

**Passing Criteria**:
- All integration tests pass
- API endpoints return expected responses
- External service integrations function correctly

**Implementation**:
```yaml
run_integration_tests:
  run: src/test/scripts/run_integration_tests.sh --environment staging --junit-report
```

### 5. End-to-End Test Gate

**Purpose**: Verify complete system functionality from user perspective

**Checks**:
- E2E test execution in staging and production environments

**Passing Criteria**:
- All critical path E2E tests pass
- System functions correctly end-to-end

**Implementation**:
```yaml
run_e2e_tests:
  run: src/test/scripts/run_e2e_tests.sh --environment staging --subset critical
```

### 6. Performance Gate

**Purpose**: Ensure system meets performance requirements

**Checks**:
- API response time
- Throughput under load
- Resource utilization

**Passing Criteria**:
- API response time <100ms (p95)
- Supports 1000+ requests per second during peak periods
- Resource utilization within expected ranges

**Implementation**:
```yaml
monitor_staging_metrics:
  run: src/test/scripts/monitor_deployment.sh --environment staging --duration 1800 --threshold 0.5
```

### 7. Production Approval Gate

**Purpose**: Ensure proper authorization for production deployments

**Checks**:
- Manual approval with approver name
- Verification of staging deployment success
- Security scan results verification

**Passing Criteria**:
- Approved by authorized personnel
- Successfully deployed to staging
- No critical security vulnerabilities

**Implementation**:
```yaml
verify_approval:
  run: echo "Deployment to production approved by ${{ github.event.inputs.approved_by }}"

verify_staging_deployment:
  run: aws ssm get-parameter --name /borrow-rate-engine/staging/deployed-versions --query "Parameter.Value" --output text | grep -q "${{ github.event.inputs.version }}"

check_security_scan_results:
  run: aws ecr describe-image-scan-findings --repository-name borrow-rate-engine --image-id imageTag=${{ github.event.inputs.version }} --query 'imageScanFindings.findings[?severity==`CRITICAL`]' --output json | jq -e 'length == 0'
```

## Quality Gate Enforcement

Quality gates are enforced through GitHub Actions workflow configurations:

1. **Sequential Jobs**: Each quality gate is a separate job with dependencies
2. **Required Checks**: Branch protection rules require passing checks before merging
3. **Fail Fast**: Pipelines fail immediately when a quality gate is not passed
4. **Detailed Reporting**: Test results and coverage reports are published as artifacts

## Quality Metrics Tracking

Quality metrics are tracked over time to identify trends and improvements:

- Code coverage history
- Test success rates
- Security vulnerability counts
- Performance metrics

These metrics are available in the CI/CD dashboards and are reviewed regularly as part of the development process.

# Infrastructure as Code

## Overview

The Borrow Rate & Locate Fee Pricing Engine uses an Infrastructure as Code (IaC) approach to manage all deployment environments. This ensures consistency, reproducibility, and version control for infrastructure changes.

## Technologies

### Kubernetes Manifests

Kubernetes resources are defined using YAML manifests organized in a kustomize structure:

```
infrastructure/kubernetes/
├── base/                 # Base resources common to all environments
│   ├── namespace.yaml
│   ├── api-gateway-deployment.yaml
│   ├── api-gateway-service.yaml
│   ├── calculation-service-deployment.yaml
│   └── ...
└── overlays/            # Environment-specific overrides
    ├── dev/
    │   ├── kustomization.yaml
    │   └── configmap-patch.yaml
    ├── staging/
    │   ├── kustomization.yaml
    │   └── configmap-patch.yaml
    └── prod/
        ├── kustomization.yaml
        ├── configmap-patch.yaml
        └── hpa-patch.yaml
```

### Helm Charts

Helm charts provide templating and packaging for more complex deployments:

```
infrastructure/helm/
├── api-gateway/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
├── calculation-service/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
└── ...
```

### Terraform

AWS infrastructure is managed using Terraform:

```
src/backend/infrastructure/
├── vpc.ts
├── security_groups.ts
├── eks.ts
├── rds.ts
├── redis.ts
└── ...
```

## Environment Configuration

### Base Configuration

The base configuration defines the core resources needed for all environments:

- Namespace definitions
- Deployment specifications
- Service definitions
- ConfigMap and Secret templates
- Ingress rules
- Horizontal Pod Autoscalers
- Pod Disruption Budgets

### Environment Overlays

Environment-specific configurations override or extend the base configuration:

**Development**:
- Lower resource limits
- Development-specific configuration values
- Relaxed security constraints for debugging

**Staging**:
- Production-like resource configuration
- Staging-specific endpoints and credentials
- Full monitoring and logging

**Production**:
- Maximum resource limits and replicas
- Strict security constraints
- Production credentials and endpoints
- Enhanced monitoring and alerting

## Deployment Configuration

### API Gateway Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: borrow-rate-engine
      component: api-gateway
  template:
    spec:
      containers:
      - name: api-gateway
        image: ${ECR_REPO}/borrow-rate-engine-api:${VERSION}
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
```

### Helm Values Example

```yaml
replicaCount: 3

image:
  repository: {{ .Values.global.registry }}/borrow-rate-engine-api
  pullPolicy: IfNotPresent
  tag: {{ .Values.global.imageTag | default .Chart.AppVersion }}

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 500m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

## Infrastructure Management Workflow

### Infrastructure Changes

1. Create a feature branch for infrastructure changes
2. Modify the relevant IaC files
3. Submit a PR with detailed description of changes
4. Review changes for security, cost, and performance implications
5. Apply changes to development environment first
6. Verify functionality in development
7. Promote changes to staging and production following the standard workflow

### Secrets Management

Sensitive configuration is managed using AWS Secrets Manager and Kubernetes Secrets:

- Database credentials
- API keys for external services
- TLS certificates
- JWT signing keys

Secrets are referenced in deployments but never stored in the repository:

```yaml
env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: database-credentials
        key: url
```

## Infrastructure Validation

Infrastructure changes are validated through:

1. **Linting**: Kubernetes manifests and Terraform configurations are linted
2. **Dry Runs**: Changes are applied with `--dry-run` flag before actual deployment
3. **Drift Detection**: Regular checks for manual changes outside of IaC
4. **Security Scanning**: Infrastructure configurations are scanned for security issues

## Best Practices

1. **Version Control**: All infrastructure code is version controlled
2. **Immutable Infrastructure**: Resources are replaced rather than modified
3. **Environment Parity**: Development, staging, and production environments use the same base configuration
4. **Least Privilege**: Resources are configured with minimal required permissions
5. **Documentation**: Infrastructure changes include documentation updates
6. **Testing**: Infrastructure changes are tested in lower environments first

# Monitoring and Observability

## Overview

The CI/CD pipeline integrates monitoring and observability practices to ensure successful deployments and detect issues early. This section describes the monitoring approaches used during and after deployments.

## Deployment Monitoring

### Deployment Verification

Each deployment includes verification steps to confirm successful rollout:

```yaml
verify_deployment:
  run: kubectl rollout status deployment/api-gateway -n ${{ env.NAMESPACE }} --timeout=300s
```

This command waits for the deployment to complete successfully or times out after 5 minutes, failing the pipeline if the deployment doesn't complete properly.

### Health Checks

After deployment, health checks verify that the application is functioning correctly:

```yaml
run_smoke_tests:
  run: src/test/scripts/run_smoke_tests.sh --environment staging
```

Smoke tests perform basic functionality checks to verify that the application is operational.

### Database Migration Verification

For deployments that include database migrations, additional verification is performed:

```yaml
run_database_migrations:
  run: kubectl exec -n ${{ env.NAMESPACE }} deploy/api-gateway -- python -m scripts.run_migrations --command upgrade
```

## Post-Deployment Monitoring

### Canary Monitoring

For production deployments using the canary strategy, dedicated monitoring is implemented:

```yaml
monitor_canary_health:
  run: |\
    kubectl logs -l app=api-gateway-canary -n ${{ env.NAMESPACE }} --tail=100
    kubectl exec -n ${{ env.NAMESPACE }} deploy/api-gateway-canary -- curl -s http://localhost:8080/health | grep -q 'UP'
```

This monitors the canary deployment for errors and ensures it's responding correctly before increasing traffic.

### Extended Monitoring

After full deployment, extended monitoring continues to watch for issues:

```yaml
monitor_production_metrics:
  run: |\
    kubectl get pods -n ${{ env.NAMESPACE }}
    kubectl top pods -n ${{ env.NAMESPACE }}
    kubectl exec -n ${{ env.NAMESPACE }} deploy/api-gateway -- curl -s http://localhost:8080/metrics
```

This collects metrics about pod status, resource usage, and application-specific metrics.

### Deployment Reports

Deployment reports are generated to provide a comprehensive view of the deployment:

```yaml
generate_deployment_report:
  run: python src/test/scripts/generate_test_report.py --type deployment --environment production --version ${{ github.event.inputs.version }}

upload_deployment_report:
  uses: actions/upload-artifact@v3
  with:
    name: production-deployment-report
    path: src/test/reports/deployment-report-${{ github.event.inputs.version }}.html
```

These reports include deployment details, test results, and metrics collected during and after deployment.

## Observability Integration

### Prometheus Metrics

All services expose Prometheus metrics that are collected during and after deployment:

```yaml
podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

These metrics provide insights into application performance, error rates, and resource usage.

### Logging

Logs are collected and analyzed during deployment:

```yaml
kubectl logs -l app=api-gateway -n ${{ env.NAMESPACE }} --tail=100
```

Logs are checked for error patterns or unexpected behavior.

### Tracing

Distributed tracing is enabled for all services, allowing end-to-end visibility of request flows across services:

```yaml
env:
  - name: ENABLE_TRACING
    value: "true"
```

## Alerting Integration

### Deployment Notifications

Deployment status is communicated through multiple channels:

```yaml
notify_deployment_success:
  uses: slackapi/slack-github-action@v1.23.0
  with:
    channel-id: ${{ secrets.SLACK_PROD_CHANNEL_ID }}
    payload: '{"text":"✅ Production deployment of version ${{ github.event.inputs.version }} completed successfully."}'
```

### GitHub Deployment Status

Deployment status is recorded in GitHub:

```yaml
update_deployment_status:
  uses: actions/github-script@v6
  with:
    script: |\
      github.rest.repos.createDeploymentStatus({\
        owner: context.repo.owner,\
        repo: context.repo.repo,\
        deployment_id: ${{ steps.create-deployment.outputs.result }},\
        state: 'success',\
        environment_url: 'https://api.borrow-rate-engine.example.com',\
        description: 'Production deployment completed successfully'\
      });
```

## Monitoring Dashboards

Deployment metrics are visualized in dashboards that show:

- Deployment frequency and success rate
- Deployment duration
- Post-deployment error rates
- Resource utilization changes after deployment

These dashboards help identify trends and potential improvements to the CI/CD process.

## Continuous Improvement

Monitoring data is used to continuously improve the CI/CD pipeline:

1. Identify common failure patterns
2. Optimize deployment strategies based on performance impact
3. Refine monitoring thresholds and alerts
4. Improve rollback procedures based on incident data

Regular reviews of deployment metrics help ensure the CI/CD pipeline remains effective and reliable.

# Rollback Procedures

## Overview

Despite thorough testing and validation, issues may still occur after deployment. The Borrow Rate & Locate Fee Pricing Engine implements comprehensive rollback procedures to quickly restore service in case of problems.

## Automated Rollback Triggers

The following conditions can trigger automated rollbacks:

1. Failed Deployment: If the Kubernetes deployment doesn't complete successfully
2. Failed Health Checks: If post-deployment health checks fail
3. High Error Rate: If error rates exceed thresholds after deployment
4. Performance Degradation: If response times increase significantly

## Environment-Specific Rollback Procedures

### Development Environment

For development, rollbacks are simple and straightforward:

```yaml
# Revert to previous version
kubectl rollout undo deployment/api-gateway -n borrow-rate-engine-dev
```

Since the development environment doesn't require high availability, rollbacks can be performed quickly without extensive validation.

### Staging Environment

Staging rollbacks include database restoration if needed:

```yaml
# Revert deployment
kubectl rollout undo deployment/api-gateway -n borrow-rate-engine-staging

# Restore database if needed
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier borrow-rate-engine-staging \
  --db-snapshot-identifier $SNAPSHOT_ID
```

Before each staging deployment, a database snapshot is created that can be used for rollback if necessary.

### Production Environment

Production rollbacks are more controlled and include multiple steps:

```yaml
# Get previous version
PREV_VERSION=$(aws ssm get-parameter \
  --name /borrow-rate-engine/production/deployed-version \
  --query 'Parameter.Value' --output text)

# Rollback deployment
kubectl rollout undo deployment/api-gateway -n borrow-rate-engine-prod

# Verify rollback
kubectl rollout status deployment/api-gateway -n borrow-rate-engine-prod --timeout=300s

# Update deployment status
github.rest.repos.createDeploymentStatus({
  owner: context.repo.owner,
  repo: context.repo.repo,
  deployment_id: ${{ needs.pre-deployment-validation.outputs.deployment_id }},
  state: 'failure',
  description: 'Production deployment failed and was rolled back to version $PREV_VERSION'
})

# Notify rollback
slackapi/slack-github-action@v1.23.0
  payload: '{"text":"⚠️ Production deployment of version $VERSION failed and was rolled back to version $PREV_VERSION."}'
```

For canary deployments, rollback is even simpler - just adjust the traffic split back to 100% for the stable version, then remove the canary.

## Database Rollback

For deployments that include database changes, rollback is more complex:

1. **Snapshot-based Rollback**: Restore from the pre-deployment snapshot
   ```yaml
   aws rds restore-db-instance-from-db-snapshot \
     --db-instance-identifier borrow-rate-engine-prod \
     --db-snapshot-identifier $SNAPSHOT_ID
   ```

2. **Migration-based Rollback**: Run downgrade migrations
   ```yaml
   kubectl exec -n $NAMESPACE deploy/api-gateway -- \
     python -m scripts.run_migrations --command downgrade --version $PREVIOUS_VERSION
   ```

The appropriate method depends on the nature of the database changes and is determined during the rollback process.

## Rollback Decision Tree

```
Issue Detected
|
+-- Is it in Development?
|   |
|   +-- Yes --> Simple rollback, no database restore
|   |
|   +-- No --> Continue
|
+-- Is it in Staging?
|   |
|   +-- Yes --> Rollback deployment, restore database if needed
|   |
|   +-- No --> Continue
|
+-- Is it in Production?
|   |
|   +-- Yes --> Is it a Canary deployment?
|       |
|       +-- Yes --> Adjust traffic split to 0% canary
|       |
|       +-- No --> Full rollback procedure