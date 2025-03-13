## Introduction

This document outlines the backup and recovery procedures for the Borrow Rate & Locate Fee Pricing Engine. It provides comprehensive guidance for maintaining data integrity, ensuring business continuity, and recovering from various failure scenarios.

As a financial system handling critical pricing calculations, robust backup and recovery processes are essential to meet regulatory requirements, maintain data integrity, and ensure system availability. This guide serves as the authoritative reference for all backup and recovery operations.

### Purpose and Scope

The purpose of this backup and recovery guide is to:

- Document the backup strategy for all system components
- Define recovery procedures for various failure scenarios
- Establish disaster recovery protocols
- Outline testing and verification procedures
- Ensure compliance with regulatory requirements

This guide covers all production environments of the Borrow Rate & Locate Fee Pricing Engine, including its database, application services, configuration, and supporting infrastructure.

### Recovery Objectives

The Borrow Rate & Locate Fee Pricing Engine has the following recovery objectives:

| Metric | Target | Description |
|--------|--------|-------------|
| Recovery Point Objective (RPO) | <5 minutes | Maximum acceptable data loss in a recovery scenario |
| Recovery Time Objective (RTO) | <15 minutes | Maximum acceptable time to restore service |
| Backup Success Rate | >99.9% | Percentage of successful backup operations |
| Recovery Success Rate | 100% | All recovery operations must be successful |

These objectives are designed to meet the business requirements for this financial system while balancing operational complexity and cost considerations.

### Roles and Responsibilities

The following roles are involved in backup and recovery operations:

- **Database Administrator**: Responsible for database backup configuration, monitoring, and recovery operations
- **Infrastructure Engineer**: Responsible for infrastructure-level backups, storage management, and system recovery
- **DevOps Engineer**: Responsible for application deployment, configuration management, and application recovery
- **Site Reliability Engineer**: Responsible for monitoring backup operations, testing recovery procedures, and improving reliability
- **Security Engineer**: Responsible for ensuring backup security, encryption, and access controls

All team members should be familiar with these procedures, but specific recovery operations should be performed by personnel with appropriate training and access.

## Backup Strategy

The backup strategy for the Borrow Rate & Locate Fee Pricing Engine is designed to ensure data integrity, minimize data loss, and support rapid recovery. It employs a multi-layered approach with different backup types and retention periods for various components.

### Database Backup Strategy

PostgreSQL database backups are critical for preserving transactional data and ensuring recoverability. The following backup strategy is implemented:

| Backup Type | Frequency | Retention | Storage | Purpose |
|-------------|-----------|-----------|---------|----------|
| Full Database | Daily | 30 days | Encrypted S3 Bucket | Complete point-in-time recovery |
| Incremental | Hourly | 7 days | Encrypted S3 Bucket | Minimize data loss between full backups |
| Transaction Logs | Continuous | 7 days | Encrypted S3 Bucket | Point-in-time recovery to any moment |
| Schema Backup | On Change | 90 days | Version Control System | Track schema evolution |

All database backups are encrypted at rest using AWS KMS with the following configuration:

- KMS key rotation: Every 90 days
- Access control: Limited to database administrators and automated recovery systems
- Backup validation: Automated integrity checks after backup completion

Database backups are configured using the AWS RDS automated backup feature with Multi-AZ deployment to ensure backup operations do not impact production performance.

```
# Example AWS CLI command to create a manual database snapshot
aws rds create-db-snapshot \
  --db-instance-identifier borrow-rate-engine-db \
  --db-snapshot-identifier manual-backup-$(date +%Y-%m-%d-%H-%M) \
  --tags Key=Purpose,Value=ManualBackup Key=Environment,Value=Production
```

### Application State Backup

While the application is primarily stateless, certain components require backup:

| Component | Backup Method | Frequency | Retention | Storage |
|-----------|--------------|-----------|-----------|----------|
| Kubernetes Config | GitOps Repository | On Change | Indefinite | Git Repository |
| Secrets | AWS Secrets Manager | Daily | 30 days | AWS Secrets Manager |
| ConfigMaps | GitOps Repository | On Change | Indefinite | Git Repository |
| Helm Values | GitOps Repository | On Change | Indefinite | Git Repository |

Application configuration is managed through infrastructure as code and stored in version control, providing an implicit backup mechanism. Critical secrets are backed up separately using AWS Secrets Manager with versioning enabled.

```
# Example command to backup Kubernetes secrets
kubectl get secret -n borrow-rate-engine -o yaml > k8s-secrets-backup-$(date +%Y-%m-%d).yaml

# Example command to backup Kubernetes configmaps
kubectl get configmap -n borrow-rate-engine -o yaml > k8s-configmaps-backup-$(date +%Y-%m-%d).yaml
```

### Cache Backup Strategy

Redis cache data is considered ephemeral but is backed up to minimize recovery time:

| Backup Type | Frequency | Retention | Storage | Purpose |
|-------------|-----------|-----------|---------|----------|
| RDB Snapshot | Hourly | 24 hours | Encrypted S3 Bucket | Rapid cache restoration |
| AOF Log | Continuous | 24 hours | Local Storage | Point-in-time recovery |

Cache backups are primarily used to speed up recovery rather than for data preservation, as all cache data can be regenerated from the primary database if necessary. The Redis cache is configured with the following persistence options:

- RDB: Snapshot every hour if at least 1 key changed
- AOF: Enabled with fsync every second
- AOF rewrite: Automatic when log grows by 100%

```
# Example Redis configuration for persistence
save 3600 1
appendonly yes
appendfsync everysec
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Example command to trigger manual Redis backup
redis-cli -h redis-master BGSAVE
```

### Audit Log Backup

Audit logs are critical for regulatory compliance and must be preserved with special care:

| Backup Type | Frequency | Retention | Storage | Purpose |
|-------------|-----------|-----------|---------|----------|
| Database Audit Logs | Daily | 7 years | Encrypted S3 Bucket (Glacier) | Regulatory compliance |
| Application Audit Logs | Daily | 7 years | Encrypted S3 Bucket (Glacier) | Regulatory compliance |
| System Audit Logs | Daily | 2 years | Encrypted S3 Bucket (Glacier) | Security analysis |

Audit logs are backed up with the following security measures:

- Immutable storage with write-once-read-many (WORM) configuration
- Encryption with dedicated KMS keys
- Access limited to security and compliance personnel
- Tamper-evident logging with hash chaining

Audit log backups are subject to regular compliance verification to ensure they meet regulatory requirements.

```
# Example AWS CLI command to configure S3 bucket for WORM storage
aws s3api put-bucket-versioning \
  --bucket borrow-rate-engine-audit-logs \
  --versioning-configuration Status=Enabled

aws s3api put-object-lock-configuration \
  --bucket borrow-rate-engine-audit-logs \
  --object-lock-configuration '{"ObjectLockEnabled":"Enabled","Rule":{"DefaultRetention":{"Mode":"COMPLIANCE","Years":7}}}'
```

### Infrastructure Backup

Infrastructure configuration is backed up to enable complete system reconstruction if needed:

| Component | Backup Method | Frequency | Retention | Storage |
|-----------|--------------|-----------|-----------|----------|
| Terraform State | Versioned S3 Bucket | On Change | Indefinite | S3 with Versioning |
| CloudFormation Stacks | AWS Backup | Weekly | 90 days | AWS Backup |
| IAM Policies | Git Repository | On Change | Indefinite | Git Repository |
| Network Configuration | AWS Config | Continuous | 90 days | AWS Config |

Infrastructure configuration is primarily managed through infrastructure as code (IaC) using Terraform and stored in version control. The Terraform state is stored in an S3 bucket with versioning enabled to allow rollback to previous states if needed.

```
# Example Terraform backend configuration for state backup
terraform {
  backend "s3" {
    bucket         = "borrow-rate-engine-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
```

## Recovery Procedures

This section outlines the procedures for recovering system components in various failure scenarios. These procedures should be followed in the order presented, adapting as necessary to the specific failure scenario.

### Database Recovery

Database recovery procedures vary based on the failure scenario:

### Complete Database Failure

1. **Assessment**:
   - Determine the cause of failure (hardware, corruption, etc.)
   - Verify if automatic failover to standby has occurred
   - Determine the appropriate recovery method

2. **Recovery from Automated Backup**:
   - Identify the most recent viable backup point
   - Initiate RDS point-in-time recovery:
     ```
     aws rds restore-db-instance-to-point-in-time \
       --source-db-instance-identifier borrow-rate-engine-db \
       --target-db-instance-identifier borrow-rate-engine-db-restored \
       --use-latest-restorable-time
     ```
   - Monitor restoration progress
   - Verify data integrity after restoration
   - Update connection strings to point to restored instance

3. **Recovery from Manual Snapshot**:
   - Identify the appropriate snapshot
   - Restore from snapshot:
     ```
     aws rds restore-db-instance-from-db-snapshot \
       --db-instance-identifier borrow-rate-engine-db-restored \
       --db-snapshot-identifier snapshot-identifier
     ```
   - Apply transaction logs if available
   - Verify data integrity
   - Update connection strings

4. **Verification**:
   - Run integrity checks on restored database
   - Verify application connectivity
   - Validate critical data (recent transactions, configurations)
   - Monitor performance metrics

### Partial Data Corruption

1. **Assessment**:
   - Identify affected tables or data
   - Determine extent of corruption
   - Isolate affected components if possible

2. **Table-Level Recovery**:
   - Create temporary database from backup
   - Extract specific tables or data
   - Import into production database

3. **Verification**:
   - Validate recovered data
   - Check referential integrity
   - Verify application functionality

### Multi-AZ Failover

In most cases, Multi-AZ failover occurs automatically, but manual intervention may be required:

1. **Forced Failover**:
   ```
   aws rds reboot-db-instance \
     --db-instance-identifier borrow-rate-engine-db \
     --force-failover
   ```

2. **Post-Failover Actions**:
   - Verify database connectivity
   - Check replication status
   - Monitor performance metrics
   - Investigate root cause of failover

```
# Example script to verify database integrity after recovery
#!/bin/bash

echo "Running database integrity checks..."

# Connect to database and run checks
psql -h $DB_HOST -U $DB_USER -d $DB_NAME << EOF
-- Check for invalid indexes
SELECT pg_class.relname, pg_index.indisvalid
FROM pg_index, pg_class
WHERE pg_index.indexrelid = pg_class.oid AND pg_index.indisvalid = false;

-- Check for bloated tables
SELECT schemaname, relname, n_dead_tup, last_vacuum, last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 10;

-- Run ANALYZE to update statistics
ANALYZE;
EOF

echo "Integrity check complete."
```

### Application Recovery

Application recovery procedures focus on restoring service with minimal downtime:

### Complete Application Failure

1. **Assessment**:
   - Determine the cause of failure (deployment, configuration, infrastructure)
   - Check Kubernetes cluster status
   - Verify external dependencies

2. **Recovery Steps**:
   - If caused by recent deployment, rollback to last known good state:
     ```
     kubectl rollout undo deployment/api-gateway -n borrow-rate-engine
     kubectl rollout undo deployment/calculation-service -n borrow-rate-engine
     kubectl rollout undo deployment/data-service -n borrow-rate-engine
     kubectl rollout undo deployment/cache-service -n borrow-rate-engine
     ```
   - If caused by configuration, restore from GitOps repository:
     ```
     kubectl apply -f infrastructure/kubernetes/base/configmap.yaml -n borrow-rate-engine
     ```
   - If caused by infrastructure, restore Kubernetes nodes or recreate cluster from IaC

3. **Service Restoration Order**:
   1. Database and Redis (if affected)
   2. Data Service
   3. Cache Service
   4. Calculation Service
   5. API Gateway

4. **Verification**:
   - Check pod status and logs
   - Verify service connectivity
   - Run health checks
   - Test end-to-end functionality

### Partial Application Failure

1. **Assessment**:
   - Identify affected components
   - Check pod status and logs
   - Verify resource utilization

2. **Recovery Steps**:
   - Restart affected services:
     ```
     kubectl rollout restart deployment/affected-service -n borrow-rate-engine
     ```
   - Scale up if resource constrained:
     ```
     kubectl scale deployment/affected-service -n borrow-rate-engine --replicas=5
     ```
   - Check for configuration issues and correct if needed

3. **Verification**:
   - Monitor service recovery
   - Check logs for error resolution
   - Verify functionality

### Configuration Recovery

1. **Assessment**:
   - Identify misconfigured components
   - Determine correct configuration

2. **Recovery Steps**:
   - Restore ConfigMaps from GitOps repository
   - Restore Secrets from backup or AWS Secrets Manager
   - Apply configuration changes
   - Restart affected services to apply changes

3. **Verification**:
   - Verify configuration is applied
   - Check service behavior with new configuration
   - Monitor for any issues

```
# Example script to verify application health after recovery
#!/bin/bash

echo "Checking application health..."

# Check pod status
kubectl get pods -n borrow-rate-engine

# Check service endpoints
for service in api-gateway calculation-service data-service cache-service; do
  echo "Checking $service health endpoint..."
  kubectl exec -it deploy/$service -n borrow-rate-engine -- curl -s http://localhost:8000/health | jq
done

# Test API functionality
echo "Testing API functionality..."
API_URL=$(kubectl get ingress -n borrow-rate-engine -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}')
curl -s -H "X-API-Key: $TEST_API_KEY" "https://$API_URL/api/v1/rates/AAPL" | jq

echo "Health check complete."
```

### Cache Recovery

Cache recovery is typically less critical as cache data can be rebuilt, but recovery procedures can minimize performance impact:

### Redis Cache Failure

1. **Assessment**:
   - Determine the cause of failure
   - Check if automatic failover occurred
   - Verify data loss extent

2. **Recovery from RDB Snapshot**:
   - Identify most recent snapshot
   - Restore Redis from snapshot:
     ```
     # Copy RDB file to Redis server
     scp redis-backup.rdb redis-server:/var/lib/redis/
     
     # Stop Redis, replace RDB, restart
     ssh redis-server "sudo systemctl stop redis && sudo mv /var/lib/redis/redis-backup.rdb /var/lib/redis/dump.rdb && sudo chown redis:redis /var/lib/redis/dump.rdb && sudo systemctl start redis"
     ```

3. **Recovery from AOF**:
   - If RDB snapshot is too old, use AOF recovery:
     ```
     # Copy AOF file to Redis server
     scp appendonly.aof redis-server:/var/lib/redis/
     
     # Stop Redis, replace AOF, restart
     ssh redis-server "sudo systemctl stop redis && sudo mv /var/lib/redis/appendonly.aof /var/lib/redis/appendonly.aof && sudo chown redis:redis /var/lib/redis/appendonly.aof && sudo systemctl start redis"
     ```

4. **Cache Warming**:
   - If recovery from backup isn't possible or practical, implement cache warming:
     ```
     # Execute cache warming script
     kubectl exec -it deploy/cache-service -n borrow-rate-engine -- python /app/scripts/warm_cache.py
     ```

5. **Verification**:
   - Check Redis connectivity
   - Verify cache hit rates
   - Monitor application performance

### ElastiCache Recovery

For AWS ElastiCache, recovery procedures are simplified:

1. **Automatic Failover**:
   - ElastiCache will automatically fail over to a replica if the primary node fails
   - Monitor the failover process in AWS Console or via AWS CLI

2. **Manual Recovery**:
   - If automatic failover fails, create a new cache cluster from the latest backup:
     ```
     aws elasticache create-cache-cluster \
       --cache-cluster-id borrow-rate-engine-redis-new \
       --snapshot-name automatic.2023-10-15-00-00 \
       --num-cache-nodes 1 \
       --cache-node-type cache.m5.large \
       --engine redis
     ```

3. **Update Connection Information**:
   - Update the application to use the new cache endpoint
   - This may require updating Kubernetes secrets and restarting services

```
# Example cache warming script (warm_cache.py)
#!/usr/bin/env python

import redis
import requests
import time
import os

# Connect to Redis
r = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis-master'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    password=os.environ.get('REDIS_PASSWORD', None)
)

# Get list of common tickers
print("Warming cache for common tickers...")
tickers = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'FB', 'TSLA', 'BRK.A', 'JPM', 'JNJ', 'V']

# Warm cache by requesting borrow rates
for ticker in tickers:
    print(f"Warming cache for {ticker}...")
    try:
        # Call internal API to populate cache
        response = requests.get(f"http://data-service:8000/internal/rates/{ticker}")
        if response.status_code == 200:
            print(f"Successfully warmed cache for {ticker}")
        else:
            print(f"Failed to warm cache for {ticker}: {response.status_code}")
    except Exception as e:
        print(f"Error warming cache for {ticker}: {e}")
    time.sleep(0.5)  # Avoid overwhelming the API

print("Cache warming complete.")
```

### Disaster Recovery

Disaster recovery procedures address catastrophic failures affecting the entire system:

### Complete System Failure

1. **Assessment**:
   - Determine the scope and cause of the disaster
   - Activate the disaster recovery team
   - Declare disaster recovery status to stakeholders

2. **Recovery Steps**:
   - Follow the disaster recovery plan in this order:
     1. Restore infrastructure from IaC (Terraform/CloudFormation)
     2. Restore database from latest backup
     3. Restore application configuration
     4. Deploy application services
     5. Verify system functionality
     6. Redirect traffic to recovered system

3. **Communication**:
   - Provide regular updates to stakeholders
   - Document all recovery actions
   - Report on data loss assessment

### Region Failure

For AWS region failure, follow these steps:

1. **Activate Secondary Region**:
   - If using multi-region deployment, promote secondary region to primary
   - If not, provision infrastructure in alternate region using IaC

2. **Database Recovery**:
   - If using cross-region replication, promote replica to primary
   - If not, restore from latest cross-region backup

3. **Application Deployment**:
   - Deploy application services in new region
   - Configure with appropriate environment settings

4. **DNS Failover**:
   - Update Route 53 to direct traffic to new region
   - Monitor DNS propagation

5. **Verification**:
   - Verify system functionality in new region
   - Validate data consistency
   - Monitor performance metrics

### Data Center Evacuation

If advance warning is available for data center issues:

1. **Proactive Backup**:
   - Trigger additional database backups
   - Ensure all configuration is committed to version control
   - Document current system state

2. **Controlled Migration**:
   - Provision resources in alternate location
   - Perform controlled database migration
   - Redirect traffic with minimal disruption

3. **Verification**:
   - Verify complete migration
   - Validate system functionality
   - Ensure no data loss occurred

```
# Example disaster recovery automation script
#!/bin/bash

set -e

echo "Starting disaster recovery process..."

# Step 1: Restore infrastructure
echo "Restoring infrastructure..."
cd infrastructure/terraform
terraform init
terraform apply -var-file=dr.tfvars -auto-approve

# Step 2: Restore database
echo "Restoring database from backup..."
LATEST_SNAPSHOT=$(aws rds describe-db-snapshots \
  --db-instance-identifier borrow-rate-engine-db \
  --snapshot-type automated \
  --query "sort_by(DBSnapshots, &SnapshotCreateTime)[-1].DBSnapshotIdentifier" \
  --output text)

aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier borrow-rate-engine-db-dr \
  --db-snapshot-identifier $LATEST_SNAPSHOT \
  --db-subnet-group-name borrow-rate-engine-db-subnet-dr

# Step 3: Wait for database to be available
echo "Waiting for database to be available..."
aws rds wait db-instance-available --db-instance-identifier borrow-rate-engine-db-dr

# Step 4: Deploy application
echo "Deploying application services..."
kubectl apply -k infrastructure/kubernetes/overlays/dr

# Step 5: Verify deployment
echo "Verifying deployment..."
kubectl wait --for=condition=available --timeout=300s -n borrow-rate-engine deployment/api-gateway
kubectl wait --for=condition=available --timeout=300s -n borrow-rate-engine deployment/calculation-service
kubectl wait --for=condition=available --timeout=300s -n borrow-rate-engine deployment/data-service
kubectl wait --for=condition=available --timeout=300s -n borrow-rate-engine deployment/cache-service

echo "Disaster recovery process completed successfully."
```

### Data Recovery

These procedures address scenarios where specific data needs to be recovered:

### Accidental Data Deletion

1. **Assessment**:
   - Identify the scope of deleted data
   - Determine when the deletion occurred
   - Evaluate impact on system functionality

2. **Recovery Options**:
   - **Point-in-Time Recovery**:
     ```
     aws rds restore-db-instance-to-point-in-time \
       --source-db-instance-identifier borrow-rate-engine-db \
       --target-db-instance-identifier borrow-rate-engine-db-recovery \
       --restore-time "2023-10-15T14:30:00Z"
     ```
   - **Table-Level Recovery**:
     - Create temporary database from backup
     - Extract specific tables
     - Import into production database
   - **Row-Level Recovery**:
     - For small amounts of data, manually reconstruct from backup

3. **Verification**:
   - Validate recovered data
   - Check data consistency
   - Verify application functionality with recovered data

### Data Corruption

1. **Assessment**:
   - Identify corrupted data
   - Determine extent of corruption
   - Isolate affected components

2. **Recovery Steps**:
   - If corruption is limited, restore specific tables or data
   - If widespread, perform full database recovery
   - Implement data validation checks

3. **Root Cause Analysis**:
   - Investigate cause of corruption
   - Implement preventive measures
   - Update validation procedures

### Audit Log Recovery

Audit logs require special handling due to compliance requirements:

1. **Assessment**:
   - Identify missing or corrupted audit logs
   - Determine compliance impact

2. **Recovery Steps**:
   - Restore audit logs from immutable backup
   - Verify integrity using hash chains
   - Document recovery process for compliance

3. **Reporting**:
   - Document any gaps in audit trail
   - Report to compliance team
   - Implement additional controls if needed

```
# Example script for table-level recovery
#!/bin/bash

# Set variables
SOURCE_DB_HOST="borrow-rate-engine-db-recovery.example.com"
SOURCE_DB_NAME="borrow_rate_engine"
SOURCE_DB_USER="recovery_user"
SOURCE_DB_PASSWORD="recovery_password"

TARGET_DB_HOST="borrow-rate-engine-db.example.com"
TARGET_DB_NAME="borrow_rate_engine"
TARGET_DB_USER="admin_user"
TARGET_DB_PASSWORD="admin_password"

TABLE_NAME="stocks"
TEMP_FILE="/tmp/${TABLE_NAME}_recovery.sql"

echo "Exporting table ${TABLE_NAME} from recovery database..."
PGPASSWORD="${SOURCE_DB_PASSWORD}" pg_dump -h "${SOURCE_DB_HOST}" -U "${SOURCE_DB_USER}" \
  -d "${SOURCE_DB_NAME}" -t "${TABLE_NAME}" --data-only > "${TEMP_FILE}"

echo "Importing table ${TABLE_NAME} to production database..."
PGPASSWORD="${TARGET_DB_PASSWORD}" psql -h "${TARGET_DB_HOST}" -U "${TARGET_DB_USER}" \
  -d "${TARGET_DB_NAME}" -f "${TEMP_FILE}"

echo "Verifying row count..."
SOURCE_COUNT=$(PGPASSWORD="${SOURCE_DB_PASSWORD}" psql -h "${SOURCE_DB_HOST}" -U "${SOURCE_DB_USER}" \
  -d "${SOURCE_DB_NAME}" -t -c "SELECT COUNT(*) FROM ${TABLE_NAME};" | tr -d ' ')

TARGET_COUNT=$(PGPASSWORD="${TARGET_DB_PASSWORD}" psql -h "${TARGET_DB_HOST}" -U "${TARGET_DB_USER}" \
  -d "${TARGET_DB_NAME}" -t -c "SELECT COUNT(*) FROM ${TABLE_NAME};" | tr -d ' ')

echo "Source count: ${SOURCE_COUNT}, Target count: ${TARGET_COUNT}"

if [ "${SOURCE_COUNT}" = "${TARGET_COUNT}" ]; then
  echo "Recovery successful!"
else
  echo "Recovery verification failed! Row counts do not match."
  exit 1
fi

# Clean up
rm "${TEMP_FILE}"
```

## Backup Monitoring and Verification

Regular monitoring and verification of backups is essential to ensure they will be viable when needed for recovery.

### Backup Monitoring

Implement comprehensive monitoring of backup processes:

### Monitoring Metrics

| Metric | Description | Alert Threshold | Action |
|--------|-------------|-----------------|--------|
| Backup Success Rate | Percentage of successful backups | <99% | Investigate failed backups |
| Backup Duration | Time taken to complete backups | >120% of baseline | Optimize backup process |
| Backup Size | Storage used by backups | >120% of baseline | Review data growth, optimize storage |
| Backup Age | Time since last successful backup | >125% of schedule | Investigate backup failures |

### Monitoring Implementation

1. **CloudWatch Alarms**:
   - Configure alarms for RDS backup status
   - Monitor S3 bucket metrics for backup storage
   - Alert on backup job failures

2. **Custom Metrics**:
   - Implement custom metrics for application-specific backups
   - Track backup verification results
   - Monitor recovery time objectives

3. **Dashboard**:
   - Create a backup status dashboard in Grafana
   - Include all critical backup metrics
   - Visualize backup history and trends

4. **Alerting**:
   - Configure alerts for backup failures
   - Implement escalation for persistent issues
   - Document alert response procedures

```
# Example CloudWatch alarm for backup failure
{
  "AlarmName": "RDSBackupFailure",
  "AlarmDescription": "Alarm when RDS backup fails",
  "ActionsEnabled": true,
  "OKActions": [],
  "AlarmActions": ["arn:aws:sns:us-east-1:123456789012:backup-alerts"],
  "InsufficientDataActions": [],
  "MetricName": "SnapshotFailure",
  "Namespace": "AWS/RDS",
  "Statistic": "Maximum",
  "Dimensions": [
    {
      "Name": "DBInstanceIdentifier",
      "Value": "borrow-rate-engine-db"
    }
  ],
  "Period": 300,
  "EvaluationPeriods": 1,
  "Threshold": 1,
  "ComparisonOperator": "GreaterThanOrEqualToThreshold"
}
```

### Backup Verification

Regular verification ensures backups are viable for recovery:

### Verification Procedures

1. **Database Backup Verification**:
   - Weekly: Restore database to test environment
   - Monthly: Perform application-level validation
   - Quarterly: Complete recovery test with timing

2. **Verification Tests**:
   - **Integrity Check**: Verify backup files are not corrupted
   - **Restoration Test**: Restore backup to test environment
   - **Application Test**: Verify application works with restored data
   - **Performance Test**: Measure time to restore and compare to RTO

3. **Documentation**:
   - Record all verification activities
   - Document any issues found
   - Track verification metrics over time

### Automated Verification

Implement automated verification where possible:

1. **Scheduled Jobs**:
   - Weekly integrity checks
   - Monthly restoration tests
   - Quarterly full recovery tests

2. **Verification Scripts**:
   - Automate database restoration
   - Implement data validation checks
   - Measure and report recovery times

```
# Example backup verification script
#!/bin/bash

set -e

echo "Starting backup verification process..."

# Step 1: Create test environment
echo "Creating test environment..."
TEST_DB_INSTANCE="borrow-rate-engine-db-test-$(date +%Y%m%d)"

# Step 2: Restore from latest backup
echo "Restoring from latest backup..."
LATEST_SNAPSHOT=$(aws rds describe-db-snapshots \
  --db-instance-identifier borrow-rate-engine-db \
  --snapshot-type automated \
  --query "sort_by(DBSnapshots, &SnapshotCreateTime)[-1].DBSnapshotIdentifier" \
  --output text)

START_TIME=$(date +%s)

aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier $TEST_DB_INSTANCE \
  --db-snapshot-identifier $LATEST_SNAPSHOT \
  --db-subnet-group-name borrow-rate-engine-db-subnet \
  --no-multi-az \
  --db-instance-class db.t3.medium

echo "Waiting for database to be available..."
aws rds wait db-instance-available --db-instance-identifier $TEST_DB_INSTANCE

END_TIME=$(date +%s)
RESTORE_DURATION=$((END_TIME - START_TIME))

echo "Restore completed in $RESTORE_DURATION seconds"

# Step 3: Run validation checks
echo "Running validation checks..."
DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier $TEST_DB_INSTANCE \
  --query "DBInstances[0].Endpoint.Address" \
  --output text)

# Run basic validation queries
psql -h $DB_ENDPOINT -U $DB_USER -d $DB_NAME << EOF
-- Check row counts in critical tables
SELECT 'stocks' as table_name, COUNT(*) as row_count FROM stocks
UNION ALL
SELECT 'brokers' as table_name, COUNT(*) as row_count FROM brokers
UNION ALL
SELECT 'volatility' as table_name, COUNT(*) as row_count FROM volatility
UNION ALL
SELECT 'api_keys' as table_name, COUNT(*) as row_count FROM api_keys;

-- Check for any invalid indexes
SELECT pg_class.relname, pg_index.indisvalid
FROM pg_index, pg_class
WHERE pg_index.indexrelid = pg_class.oid AND pg_index.indisvalid = false;
EOF

# Step 4: Clean up test environment
echo "Cleaning up test environment..."
aws rds delete-db-instance \
  --db-instance-identifier $TEST_DB_INSTANCE \
  --skip-final-snapshot \
  --delete-automated-backups

# Step 5: Report results
echo "Verification complete. Restore time: $RESTORE_DURATION seconds"
if [ $RESTORE_DURATION -gt 900 ]; then
  echo "WARNING: Restore time exceeds 15 minutes (RTO threshold)"
fi

echo "Sending verification report..."
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:123456789012:backup-verification \
  --subject "Backup Verification Report - $(date +%Y-%m-%d)" \
  --message "Backup verification completed.\nSnapshot: $LATEST_SNAPSHOT\nRestore time: $RESTORE_DURATION seconds\nStatus: Success"

echo "Backup verification process completed."
```

### Recovery Testing

Regular recovery testing ensures the team is prepared for actual recovery scenarios:

### Recovery Test Types

1. **Tabletop Exercises**:
   - Scenario-based discussion exercises
   - Walk through recovery procedures
   - Identify gaps in documentation or procedures
   - Quarterly frequency

2. **Functional Tests**:
   - Restore specific components in isolation
   - Verify component functionality
   - Measure recovery time
   - Monthly frequency

3. **Full Recovery Tests**:
   - Simulate complete system failure
   - Execute full recovery procedures
   - Verify end-to-end functionality
   - Measure against RTO/RPO
   - Semi-annual frequency

### Recovery Test Documentation

For each recovery test, document:

1. **Test Plan**:
   - Scope and objectives
   - Resources required
   - Success criteria
   - Test schedule

2. **Test Results**:
   - Actual recovery time
   - Issues encountered
   - Deviations from procedures
   - Success evaluation

3. **Improvement Actions**:
   - Identified gaps
   - Procedure updates
   - Training needs
   - Follow-up testing