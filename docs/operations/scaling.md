# Scaling Guide for Borrow Rate & Locate Fee Pricing Engine

## Scaling Overview

This document provides comprehensive guidance for scaling the Borrow Rate & Locate Fee Pricing Engine to handle varying load conditions. It covers horizontal and vertical scaling strategies, auto-scaling configuration, resource management, and best practices for maintaining performance under different load scenarios.

The Borrow Rate & Locate Fee Pricing Engine is designed to scale efficiently to meet its performance requirements, including <100ms response time for API requests and support for 1000+ requests per second during peak periods.

### Scaling Principles

The scaling strategy for the Borrow Rate & Locate Fee Pricing Engine is guided by the following principles:

1. **Horizontal Scaling for Stateless Services**: API Gateway, Calculation Service, and Data Service scale horizontally to handle increased request volume.

2. **Vertical Scaling for Stateful Components**: Database and cache components primarily scale vertically, with read replicas for horizontal read scaling.

3. **Proactive Scaling**: Auto-scaling is configured to scale up proactively before performance degrades.

4. **Resource Efficiency**: Scaling is balanced with resource efficiency to optimize cost without compromising performance.

5. **Service-Specific Scaling**: Each service has tailored scaling parameters based on its resource requirements and usage patterns.

6. **Resilience During Scaling**: The system maintains availability and performance during scaling operations.

These principles ensure that the system can handle varying load conditions while maintaining its performance SLAs.

### Scaling Dimensions

The system can scale along multiple dimensions:

1. **Request Volume Scaling**: Handling increased API request volume through horizontal pod scaling.

2. **Calculation Complexity Scaling**: Managing complex calculations that require more CPU resources.

3. **Data Volume Scaling**: Handling increased data storage and retrieval requirements.

4. **Client Scaling**: Supporting growth in the number of clients and client-specific configurations.

5. **Geographic Scaling**: Future capability to deploy across multiple regions for global coverage.

This document focuses primarily on request volume scaling, which is the most common scaling dimension for the system.

### Scaling Metrics

The following metrics are used to drive scaling decisions:

| Metric | Description | Target | Scaling Trigger |
|--------|-------------|--------|----------------|
| CPU Utilization | Average CPU usage across pods | <70% | >70% for scale-out, <40% for scale-in |
| Memory Utilization | Average memory usage across pods | <80% | >80% for scale-out, <50% for scale-in |
| Requests Per Second | API request rate | Varies by service | Service-specific thresholds |
| Response Time | API response latency (p95) | <100ms | >150ms for manual intervention |
| Database Connections | Connection pool utilization | <80% | >80% for Data Service scaling |

These metrics are monitored continuously, with auto-scaling configured to respond automatically to changes in CPU utilization and requests per second.

### Scaling Responsibilities

Scaling responsibilities are distributed as follows:

1. **Automatic Scaling**: Handled by Kubernetes HPA and Cluster Autoscaler for:
   - API Gateway scaling based on CPU and request rate
   - Calculation Service scaling based on CPU and calculation rate
   - Data Service scaling based on CPU and database connections
   - Node group scaling based on pod resource requests

2. **Manual Scaling**: Performed by operations team for:
   - Database instance type changes
   - Cache instance type changes
   - Adjustments to auto-scaling parameters
   - Proactive scaling for planned load increases

3. **Monitoring and Oversight**: DevOps team responsibilities:
   - Regular review of scaling effectiveness
   - Optimization of scaling parameters
   - Capacity planning for future growth
   - Performance testing to validate scaling

Clear responsibilities ensure that scaling operations are performed correctly and in a timely manner.

## Horizontal Scaling

Horizontal scaling involves adding more instances of a service to distribute load. This is the primary scaling mechanism for the stateless services in the Borrow Rate & Locate Fee Pricing Engine.

### Kubernetes Deployments

The following services are deployed as Kubernetes Deployments, which support horizontal scaling:

1. **API Gateway**: Routes requests and handles authentication
2. **Calculation Service**: Performs fee calculations
3. **Data Service**: Manages data access and external API integration
4. **Cache Service**: Provides caching functionality
5. **Audit Service**: Records audit logs

Each deployment is configured with appropriate resource requests and limits, readiness/liveness probes, and pod disruption budgets to ensure reliable scaling.

```yaml
# Example Deployment configuration
apiVersion: apps/v1
kind: Deployment
metadata:
  name: calculation-service
spec:
  replicas: 3  # Initial replica count
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: calculation-service
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
```

These deployments can be scaled manually or automatically through Horizontal Pod Autoscalers.

### Horizontal Pod Autoscaler (HPA)

Horizontal Pod Autoscalers automatically adjust the number of pods based on observed metrics:

1. **API Gateway HPA**:
   - Metrics: CPU utilization, requests per second
   - Min Replicas: 3 (ensures high availability across zones)
   - Max Replicas: 10 (development/staging), 20 (production)
   - Target CPU Utilization: 70%
   - Target Request Rate: 800 requests/second per pod

2. **Calculation Service HPA**:
   - Metrics: CPU utilization, calculations per second
   - Min Replicas: 3 (ensures high availability across zones)
   - Max Replicas: 20 (development/staging), 30 (production)
   - Target CPU Utilization: 80%
   - Target Calculation Rate: 700 calculations/second per pod

3. **Data Service HPA**:
   - Metrics: CPU utilization, database connections percentage
   - Min Replicas: 3 (ensures high availability across zones)
   - Max Replicas: 10 (development/staging), 15 (production)
   - Target CPU Utilization: 70%
   - Target DB Connection Percentage: 80%

```yaml
# Example HPA configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: calculation-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: calculation-service
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: requests_per_second
      target:
        type: AverageValue
        averageValue: 700
```

HPAs are configured with appropriate stabilization windows to prevent thrashing (rapid scaling up and down).

### Manual Horizontal Scaling

Manual horizontal scaling may be required in certain scenarios:

1. **Proactive Scaling**: Scaling in advance of expected load increases
2. **HPA Override**: Temporarily overriding HPA settings
3. **Testing**: Validating system behavior at different scales
4. **Emergency Scaling**: Rapid scaling during unexpected load

To manually scale a deployment:

```bash
# Scale a deployment to a specific number of replicas
kubectl scale deployment calculation-service -n borrow-rate-engine-${ENV} --replicas=10

# Verify the scaling operation
kubectl get deployment calculation-service -n borrow-rate-engine-${ENV}
```

Manual scaling should be documented and, if persistent, incorporated into the HPA configuration.

### Node Group Scaling

Kubernetes nodes are managed by the Cluster Autoscaler, which automatically adjusts the number of nodes based on pod resource requests:

1. **Application Node Group**:
   - Purpose: Runs application workloads
   - Instance Types: m5.xlarge (4 vCPU, 16 GiB RAM)
   - Min Nodes: 3 (development/staging), 3 (production)
   - Max Nodes: 10 (development/staging), 20 (production)
   - Scaling Trigger: Insufficient resources to schedule pods

2. **System Node Group**:
   - Purpose: Runs system workloads (monitoring, logging)
   - Instance Types: t3.large (2 vCPU, 8 GiB RAM)
   - Min Nodes: 2 (all environments)
   - Max Nodes: 5 (all environments)
   - Scaling Trigger: Insufficient resources to schedule pods

To manually adjust node group scaling parameters:

```bash
# Update node group scaling configuration
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name ${NODE_GROUP_NAME} \
  --min-size 5 --max-size 30

# Verify the update
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names ${NODE_GROUP_NAME}
```

Node group scaling ensures sufficient infrastructure capacity for pod scaling.

### Horizontal Scaling Best Practices

Follow these best practices for effective horizontal scaling:

1. **Resource Requests and Limits**:
   - Set accurate resource requests based on actual usage
   - Configure appropriate resource limits to prevent resource starvation
   - Regularly review and adjust based on observed usage

2. **Readiness Probes**:
   - Implement robust readiness probes to ensure traffic only routes to ready pods
   - Configure appropriate initial delay and timeout values
   - Ensure probes accurately reflect service health

3. **Pod Disruption Budgets**:
   - Configure PDBs to maintain minimum availability during scaling
   - Ensure PDBs align with high availability requirements
   - Test voluntary disruptions to validate PDB effectiveness

4. **Anti-Affinity Rules**:
   - Use pod anti-affinity to distribute replicas across nodes and zones
   - Ensure critical services have hard anti-affinity rules
   - Balance anti-affinity with efficient resource usage

5. **Scaling Thresholds**:
   - Set scale-out thresholds to trigger before performance degrades
   - Configure scale-in thresholds to prevent resource waste
   - Use appropriate stabilization windows to prevent thrashing

Following these practices ensures reliable and efficient horizontal scaling.

## Vertical Scaling

Vertical scaling involves increasing the resources allocated to individual instances. This is primarily used for stateful components like databases and caches.

### Database Scaling

The PostgreSQL database can be scaled vertically using AWS RDS features:

1. **Instance Type Scaling**:
   - Development: db.t3.medium (2 vCPU, 4 GiB RAM)
   - Staging: db.r5.large (2 vCPU, 16 GiB RAM)
   - Production: db.r5.xlarge (4 vCPU, 32 GiB RAM)
   - Scaling Path: db.r5.xlarge → db.r5.2xlarge → db.r5.4xlarge

2. **Storage Scaling**:
   - Development: 50 GB gp2
   - Staging: 100 GB gp3
   - Production: 500 GB gp3 with provisioned IOPS
   - Auto-scaling: Enabled with 10% free threshold

3. **Read Scaling**:
   - Development: No read replicas
   - Staging: 1 read replica
   - Production: 2 read replicas across AZs

To scale the database instance type:

```bash
# Create a snapshot before scaling
aws rds create-db-snapshot \
  --db-snapshot-identifier borrow-rate-engine-${ENV}-pre-scaling-$(date +%Y%m%d) \
  --db-instance-identifier borrow-rate-engine-${ENV}

# Modify the instance type
aws rds modify-db-instance \
  --db-instance-identifier borrow-rate-engine-${ENV} \
  --db-instance-class db.r5.2xlarge \
  --apply-immediately
```

Database scaling operations typically require a maintenance window and may cause a brief downtime.

### Cache Scaling

The Redis cache can be scaled vertically using AWS ElastiCache features:

1. **Instance Type Scaling**:
   - Development: cache.t3.small (2 vCPU, 1.5 GiB RAM)
   - Staging: cache.m5.large (2 vCPU, 6.4 GiB RAM)
   - Production: cache.m5.xlarge (4 vCPU, 12.9 GiB RAM)
   - Scaling Path: cache.m5.xlarge → cache.m5.2xlarge → cache.m5.4xlarge

2. **Replication Scaling**:
   - Development: Single node
   - Staging: 1 primary, 1 replica
   - Production: 1 primary, 2 replicas across AZs

3. **Cluster Mode**:
   - Development: Disabled
   - Staging: Disabled
   - Production: Enabled with 3 shards (production only)

To scale the cache instance type:

```bash
# Modify the cache cluster
aws elasticache modify-replication-group \
  --replication-group-id borrow-rate-engine-${ENV} \
  --cache-node-type cache.m5.2xlarge \
  --apply-immediately
```

Cache scaling operations may cause a brief performance impact but typically do not cause downtime due to the replication architecture.

### Container Resource Allocation

Container resource allocations can be adjusted to provide vertical scaling within Kubernetes:

1. **API Gateway**:
   - Default: 500m CPU, 1Gi memory
   - Maximum: 2000m CPU, 4Gi memory
   - Scaling Trigger: Consistently high CPU utilization

2. **Calculation Service**:
   - Default: 1000m CPU, 2Gi memory
   - Maximum: 4000m CPU, 8Gi memory
   - Scaling Trigger: Calculation latency or high CPU utilization

3. **Data Service**:
   - Default: 500m CPU, 1.5Gi memory
   - Maximum: 2000m CPU, 6Gi memory
   - Scaling Trigger: Query latency or high memory usage

4. **Cache Service**:
   - Default: 1000m CPU, 4Gi memory
   - Maximum: 4000m CPU, 16Gi memory
   - Scaling Trigger: Cache latency or high memory usage

To adjust container resource allocation:

```bash
# Update deployment with new resource requests/limits
kubectl patch deployment calculation-service -n borrow-rate-engine-${ENV} --patch '{"spec":{"template":{"spec":{"containers":[{"name":"calculation-service","resources":{"requests":{"cpu":"2000m","memory":"4Gi"},"limits":{"cpu":"4000m","memory":"8Gi"}}}]}}}}'
```

Resource allocation changes trigger a rolling update of the deployment.

### Vertical Scaling Best Practices

Follow these best practices for effective vertical scaling:

1. **Performance Testing**:
   - Test different resource allocations to identify optimal configurations
   - Measure performance improvements from vertical scaling
   - Identify diminishing returns thresholds

2. **Incremental Scaling**:
   - Scale in increments rather than large jumps
   - Monitor performance after each scaling operation
   - Allow stabilization time between changes

3. **Maintenance Windows**:
   - Schedule database scaling during defined maintenance windows
   - Communicate expected impact to stakeholders
   - Prepare rollback plans for unsuccessful scaling

4. **Cost-Benefit Analysis**:
   - Compare costs of vertical vs. horizontal scaling
   - Consider reserved instances for predictable workloads
   - Evaluate performance gains against cost increases

5. **Monitoring During Scaling**:
   - Closely monitor system during scaling operations
   - Watch for unexpected performance impacts
   - Be prepared to roll back if necessary

Vertical scaling is particularly valuable for components with state or licensing constraints.

## Auto-Scaling Configuration

Auto-scaling enables the system to automatically adjust capacity based on load. This section covers the configuration and management of auto-scaling components.

### Horizontal Pod Autoscaler Configuration

Horizontal Pod Autoscalers (HPAs) are configured with the following parameters:

1. **Metrics Selection**:
   - CPU Utilization: Primary metric for all services
   - Custom Metrics: Service-specific metrics (requests/sec, calculations/sec)
   - Memory Utilization: Secondary metric for memory-intensive services

2. **Scaling Policies**:
   - Scale Up: Aggressive to handle traffic increases quickly
   - Scale Down: Conservative to prevent premature scale-down
   - Stabilization Windows: Prevent thrashing during fluctuating load

3. **Environment-Specific Settings**:
   - Development: Optimized for cost (smaller min/max ranges)
   - Staging: Similar to production but with lower maximums
   - Production: Optimized for performance and reliability

Example HPA configuration with behavior policies:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: calculation-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: calculation-service
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: requests_per_second
      target:
        type: AverageValue
        averageValue: 700
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Pods
        value: 3
        periodSeconds: 60
      - type: Percent
        value: 50
        periodSeconds: 60
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Pods
        value: 1
        periodSeconds: 60
      - type: Percent
        value: 20
        periodSeconds: 60
      selectPolicy: Min
```

This configuration allows scaling up by either 3 pods or 50% every 60 seconds (whichever is greater) and scaling down by either 1 pod or 20% every 60 seconds (whichever is less).

### Cluster Autoscaler Configuration

The Kubernetes Cluster Autoscaler automatically adjusts the number of nodes based on pod resource requests:

1. **Scaling Parameters**:
   - Scan Interval: 10 seconds
   - Scale-Down Delay: 10 minutes after scale-up
   - Scale-Down Unneeded Time: 10 minutes
   - Scale-Down Utilization Threshold: 0.5 (50%)

2. **Node Group Configuration**:
   - Application Nodes: 3-20 nodes (production)
   - System Nodes: 2-5 nodes (all environments)
   - Spot Nodes: 0-10 nodes (development/staging)

3. **Expander Strategy**:
   - Least-Waste: Choose node group that would have the least idle CPU after scale-up

Example Cluster Autoscaler configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-autoscaler-config
data:
  config: |
    {
      "scan-interval": "10s",
      "scale-down-delay-after-add": "10m",
      "scale-down-unneeded-time": "10m",
      "scale-down-utilization-threshold": 0.5,
      "expander": "least-waste"
    }
```

The Cluster Autoscaler ensures sufficient node capacity for pod scaling while minimizing resource waste.

### Custom Metrics Configuration

Custom metrics are used for more precise auto-scaling based on application-specific metrics:

1. **Metrics Collection**:
   - Prometheus Adapter: Exposes Prometheus metrics to Kubernetes
   - Custom Metrics API: Provides metrics to HPA
   - Service Monitors: Define which metrics to collect

2. **Key Custom Metrics**:
   - `http_requests_per_second`: Used for API Gateway scaling
   - `calculation_rate`: Used for Calculation Service scaling
   - `database_connections_percentage`: Used for Data Service scaling
   - `cache_operations_per_second`: Used for Cache Service scaling

3. **Metric Configuration**:
   - Aggregation: How metrics are combined across pods
   - Scope: Which pods/services the metric applies to
   - Scaling Ratio: Relationship between metric and replica count

Example Prometheus Adapter configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-adapter-config
data:
  config.yaml: |
    rules:
    - seriesQuery: 'http_requests_total{namespace="borrow-rate-engine",pod!="",service="api-gateway"}'      
      resources:
        overrides:
          namespace:
            resource: namespace
          pod:
            resource: pod
      name:
        matches: "^(.*)_total$"
        as: "${1}_per_second"
      metricsQuery: 'sum(rate(<<.Series>>{<<.LabelMatchers>>}[2m])) by (<<.GroupBy>>)'
```

Custom metrics provide more application-aware scaling than CPU-based scaling alone.

### Auto-Scaling Testing and Validation

Regular testing ensures that auto-scaling functions correctly:

1. **Load Testing**:
   - Generate synthetic load to trigger scaling
   - Verify scaling occurs at expected thresholds
   - Measure time to scale up and handle load
   - Validate performance during scaling

2. **Scale-Down Testing**:
   - Reduce load to trigger scale-down
   - Verify scale-down respects stabilization windows
   - Ensure no service disruption during scale-down

3. **Failure Testing**:
   - Simulate node failures to test resilience
   - Verify pods reschedule appropriately
   - Ensure service continuity during node replacement

4. **Metrics Validation**:
   - Verify custom metrics are reporting correctly
   - Validate metric aggregation and calculation
   - Ensure metrics reflect actual system load

Regular testing helps identify and address auto-scaling issues before they impact production.

### Auto-Scaling Monitoring

Monitoring auto-scaling activity is essential for optimization:

1. **Scaling Event Monitoring**:
   - Track HPA scaling events
   - Monitor node group scaling
   - Alert on unexpected scaling patterns
   - Record scaling history for analysis

2. **Metrics Monitoring**:
   - Verify metrics driving scaling decisions
   - Track metric trends over time
   - Identify metric anomalies
   - Validate metric collection reliability

3. **Resource Utilization**:
   - Monitor CPU and memory usage across pods
   - Track node resource utilization
   - Identify resource bottlenecks
   - Optimize resource requests/limits

4. **Performance Correlation**:
   - Correlate scaling events with performance metrics
   - Verify scaling improves performance as expected
   - Identify scaling thresholds that maintain SLAs

The Auto-Scaling dashboard provides visibility into scaling activities and their impact on system performance. Utilize Prometheus and Grafana to create dedicated visualizations for scaling metrics, showing both the cause (increased load) and effect (scaling events) together for analysis.

## Scaling for Specific Scenarios

Different scenarios require specific scaling approaches. This section covers scaling strategies for common situations.

### Daily Traffic Patterns

The system experiences predictable daily traffic patterns that can be addressed with proactive scaling:

1. **Market Hours Scaling**:
   - Higher traffic during market hours (9:30 AM - 4:00 PM ET)
   - Pre-market preparation (8:00 AM - 9:30 AM ET)
   - Post-market activity (4:00 PM - 6:00 PM ET)
   - Lower overnight activity

2. **Proactive Scaling Approach**:
   - Increase minimum replicas before market open
   - Maintain higher capacity during market hours
   - Gradually reduce capacity after market close
   - Minimum capacity overnight

3. **Implementation Options**:
   - Scheduled scaling using Kubernetes CronJobs
   - Predictive scaling based on historical patterns
   - HPA with different configurations for market/non-market hours

Example scheduled scaling job:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: market-open-scaling
spec:
  schedule: "0 8 * * 1-5"  # 8:00 AM ET, Monday-Friday
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: kubectl
            image: bitnami/kubectl
            command:
            - /bin/sh
            - -c
            - |
              kubectl patch hpa calculation-service-hpa -n borrow-rate-engine-prod --patch '{"spec":{"minReplicas":10}}'              
          restartPolicy: OnFailure
```

Proactive scaling for daily patterns ensures optimal performance during peak hours while reducing costs during off-hours.

### Market Events and Volatility

Market events and high volatility periods require enhanced scaling capabilities:

1. **High Volatility Indicators**:
   - VIX index above certain thresholds
   - Significant market movements
   - Earnings announcements
   - Economic data releases
   - Unexpected news events

2. **Scaling Response**:
   - Increase minimum replicas during high volatility
   - Lower CPU utilization thresholds to scale more aggressively
   - Increase maximum replicas to handle potential spikes
   - Enhance database and cache capacity

3. **Implementation Approach**:
   - Monitoring of market volatility indicators
   - Automated or manual scaling triggers based on indicators
   - Pre-defined scaling plans for known events
   - Post-event scaling normalization

Example scaling command for high volatility:

```bash
# Increase scaling capacity for high volatility
kubectl patch hpa calculation-service-hpa -n borrow-rate-engine-prod --patch '{"spec":{"minReplicas":15,"maxReplicas":40,"metrics":[{"type":"Resource","resource":{"name":"cpu","target":{"type":"Utilization","averageUtilization":60}}}]}}'
```

Proper scaling during market events ensures system stability during periods of high demand and potential calculation complexity.

### Planned Load Increases

Planned load increases, such as onboarding new clients or launching new features, require coordinated scaling:

1. **Pre-scaling Assessment**:
   - Estimate expected load increase
   - Identify affected components
   - Determine required capacity
   - Plan scaling sequence

2. **Scaling Approach**:
   - Increase capacity ahead of expected load
   - Scale in phases for large increases
   - Monitor performance during scaling
   - Adjust based on actual load

3. **Components to Scale**:
   - Application services (horizontal scaling)
   - Database capacity (vertical scaling)
   - Cache capacity (vertical scaling)
   - Node groups (horizontal scaling)

Example scaling plan for new client onboarding:

```
1. Increase database instance to next tier (T-7 days)
2. Increase cache instance to next tier (T-7 days)
3. Increase minimum replicas for all services by 50% (T-1 day)
4. Increase maximum replicas for all services by 100% (T-1 day)
5. Increase node group capacity by 50% (T-1 day)
6. Monitor during onboarding and adjust as needed
7. Normalize scaling after load stabilizes (T+7 days)
```

Proactive scaling for planned load increases ensures a smooth experience for existing and new clients.

### Unexpected Traffic Spikes

Unexpected traffic spikes require rapid scaling response:

1. **Detection Mechanisms**:
   - Real-time traffic monitoring
   - Anomaly detection alerts
   - Performance degradation indicators
   - External event monitoring

2. **Automated Response**:
   - HPA scales based on CPU and request metrics
   - Cluster Autoscaler adds nodes as needed
   - Circuit breakers protect critical components
   - Rate limiting prevents system overload

3. **Manual Intervention**:
   - Emergency scaling procedures
   - Temporary resource allocation increases
   - Traffic prioritization if needed
   - Stakeholder communication

Emergency scaling command for unexpected spikes:

```bash
# Emergency scaling for traffic spike
kubectl scale deployment calculation-service -n borrow-rate-engine-prod --replicas=30

# Increase node group capacity
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name ${NODE_GROUP_NAME} \
  --desired-capacity 15
```

Rapid response to unexpected traffic spikes helps maintain system stability and performance during unusual conditions.

### Scaling for Maintenance

Maintenance operations may require specific scaling adjustments:

1. **Pre-Maintenance Scaling**:
   - Increase capacity before maintenance
   - Ensure sufficient redundancy during node rotations
   - Adjust PodDisruptionBudgets if needed
   - Prepare for potential performance impact

2. **During Maintenance**:
   - Monitor performance closely
   - Adjust scaling parameters if needed
   - Be prepared for manual intervention
   - Communicate status to stakeholders

3. **Post-Maintenance**:
   - Verify scaling functionality
   - Return to normal scaling parameters
   - Document any issues or learnings
   - Update procedures if needed

Example pre-maintenance scaling:

```bash
# Increase minimum replicas before maintenance
kubectl patch hpa api-gateway-hpa -n borrow-rate-engine-prod --patch '{"spec":{"minReplicas":6}}'
kubectl patch hpa calculation-service-hpa -n borrow-rate-engine-prod --patch '{"spec":{"minReplicas":6}}'
kubectl patch hpa data-service-hpa -n borrow-rate-engine-prod --patch '{"spec":{"minReplicas":6}}'

# Adjust PDB to allow more disruption during maintenance
kubectl patch pdb api-gateway-pdb -n borrow-rate-engine-prod --patch '{"spec":{"minAvailable":"70%"}}'
```

Proper scaling during maintenance ensures minimal impact on system performance and availability.

## Scaling Best Practices

This section provides best practices for scaling the Borrow Rate & Locate Fee Pricing Engine effectively.

### Performance Testing

Regular performance testing is essential for effective scaling:

1. **Load Testing Types**:
   - Baseline testing: Establish normal performance
   - Stress testing: Find breaking points
   - Endurance testing: Verify long-term stability
   - Spike testing: Validate response to sudden load

2. **Testing Methodology**:
   - Use realistic traffic patterns
   - Test all critical paths
   - Measure key performance indicators
   - Validate scaling triggers and responses

3. **Testing Schedule**:
   - Monthly baseline tests
   - Quarterly stress tests
   - Before major releases
   - After significant infrastructure changes

4. **Key Metrics to Measure**:
   - Response time under load
   - Throughput capacity
   - Scaling response time
   - Resource utilization
   - Error rates during scaling

Performance testing helps identify scaling bottlenecks and validate scaling configurations.

### Resource Optimization

Optimizing resource allocation improves scaling efficiency:

1. **Right-Sizing Resources**:
   - Analyze actual resource usage
   - Set requests based on P95 usage
   - Set limits based on peak requirements
   - Regularly review and adjust

2. **Efficient Resource Usage**:
   - Optimize application code for efficiency
   - Implement caching strategically
   - Use connection pooling effectively
   - Minimize resource waste

3. **Cost-Effective Scaling**:
   - Use Spot Instances for non-critical workloads
   - Implement auto-scaling for all components
   - Scale down during off-hours
   - Consider reserved instances for baseline capacity

4. **Resource Quotas and Limits**:
   - Set namespace resource quotas
   - Implement LimitRanges for default values
   - Prevent resource monopolization
   - Ensure fair resource distribution

Resource optimization ensures cost-effective scaling while maintaining performance.

### Monitoring and Alerting

Comprehensive monitoring is critical for effective scaling:

1. **Scaling-Specific Metrics**:
   - HPA metrics and decisions
   - Cluster Autoscaler activities
   - Pod startup and termination events
   - Resource utilization during scaling

2. **Performance Impact Monitoring**:
   - Response time during scaling events
   - Error rates during scaling
   - Database connection patterns
   - Cache hit rates during scaling

3. **Alerting Strategy**:
   - Alert on scaling failures
   - Alert on unexpected scaling patterns
   - Alert on resource constraints
   - Alert on performance degradation during scaling

4. **Scaling Dashboards**:
   - HPA status and history
   - Node group capacity and utilization
   - Scaling event correlation with performance
   - Resource headroom visualization

Effective monitoring ensures scaling issues are detected and addressed promptly. Implement dedicated dashboards to visualize scaling activity alongside performance metrics.

For comprehensive metrics collection:
1. Use Prometheus for time-series metrics storage
2. Configure Grafana dashboards for visualization
3. Set up Alertmanager for notification routing
4. Implement custom metrics exporters where needed

Track scaling-specific metrics including scaling operations per hour, time-to-scale (from trigger to completion), and resource efficiency after scaling events.

### Scaling Governance

Proper governance ensures controlled and effective scaling:

1. **Scaling Policies**:
   - Document scaling parameters for each component
   - Define approval process for scaling changes
   - Establish emergency scaling procedures
   - Maintain scaling configuration history

2. **Change Management**:
   - Test scaling changes in non-production first
   - Document expected impact of scaling changes
   - Implement scaling changes during low-traffic periods
   - Monitor closely after scaling changes

3. **Capacity Planning**:
   - Regular capacity reviews
   - Growth forecasting and planning
   - Proactive infrastructure scaling
   - Budget alignment for scaling needs

4. **Documentation and Knowledge Sharing**:
   - Document scaling procedures
   - Share scaling insights across teams
   - Train team members on scaling operations
   - Maintain runbooks for scaling scenarios

Proper governance ensures scaling is performed consistently and effectively.

### Continuous Improvement

Scaling strategies should evolve based on operational experience:

1. **Scaling Retrospectives**:
   - Review scaling effectiveness after events
   - Identify opportunities for improvement
   - Document lessons learned
   - Update procedures based on experience

2. **Scaling Metrics Analysis**:
   - Analyze scaling patterns over time
   - Identify trends and anomalies
   - Optimize scaling parameters
   - Validate scaling effectiveness

3. **Technology Evolution**:
   - Evaluate new scaling capabilities
   - Test improved scaling mechanisms
   - Adopt best practices from the community
   - Upgrade components to leverage new features

4. **Feedback Loops**:
   - Gather input from operations teams
   - Incorporate developer feedback
   - Address pain points in scaling
   - Streamline scaling operations

Continuous improvement ensures scaling strategies remain effective as the system evolves.

## Troubleshooting Scaling Issues

This section provides guidance for troubleshooting common scaling issues.

### HPA Not Scaling

Troubleshooting steps when HPA is not scaling as expected:

1. **Check HPA Status**:
   ```bash
   kubectl get hpa -n borrow-rate-engine-${ENV}
   kubectl describe hpa calculation-service-hpa -n borrow-rate-engine-${ENV}
   ```
   Look for:
   - Current metrics values
   - Target metric values
   - Last scaling time
   - Events and conditions

2. **Verify Metrics**:
   ```bash
   kubectl get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/borrow-rate-engine-${ENV}/pods" | jq
   ```
   For custom metrics:
   ```bash
   kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1/namespaces/borrow-rate-engine-${ENV}/pods/*/http_requests_per_second" | jq
   ```
   Ensure metrics are being collected correctly.

3. **Check Metrics Server**:
   ```bash
   kubectl get pods -n kube-system | grep metrics-server
   kubectl logs -n kube-system -l k8s-app=metrics-server
   ```
   Verify the metrics server is running and collecting data.

4. **Verify Custom Metrics Adapter**:
   ```bash
   kubectl get pods -n monitoring | grep prometheus-adapter
   kubectl logs -n monitoring -l app=prometheus-adapter
   ```
   Check for errors in the adapter logs.

5. **Common Issues and Solutions**:
   - Metrics not available: Check metrics collection
   - Stabilization window preventing scaling: Wait or adjust window
   - Resource constraints: Check if nodes have capacity
   - HPA misconfiguration: Verify target metrics and thresholds

If HPA is still not scaling, consider manual scaling while investigating the root cause.

### Cluster Autoscaler Issues

Troubleshooting steps for Cluster Autoscaler problems:

1. **Check Autoscaler Status**:
   ```bash
   kubectl -n kube-system logs -l app=cluster-autoscaler
   ```
   Look for:
   - Scale-up/scale-down decisions
   - Node group status
   - Error messages
   - Unschedulable pods

2. **Verify Node Groups**:
   ```bash
   aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names ${NODE_GROUP_NAME}
   ```
   Check:
   - Current capacity
   - Min/max settings
   - Scaling activities
   - Instance health

3. **Check for Unschedulable Pods**:
   ```bash
   kubectl get pods -A | grep Pending
   kubectl describe pod <pending-pod-name> -n <namespace>
   ```
   Look for scheduling errors in the events section.

4. **Verify Node Resources**:
   ```bash
   kubectl describe nodes
   kubectl top nodes
   ```
   Check if nodes are resource-constrained.

5. **Common Issues and Solutions**:
   - ASG limits preventing scaling: Adjust min/max settings
   - Instance type availability: Try different instance types
   - Scaling speed: Adjust warm pool settings
   - Pod resource requests too high: Adjust requests
   - Taints or node selectors: Check pod scheduling constraints

If the Cluster Autoscaler is not functioning correctly, consider manually adjusting the ASG desired capacity while investigating.

### Performance During Scaling

Troubleshooting performance issues during scaling:

1. **Monitor Key Metrics**:
   ```bash
   # Check API response times
   kubectl exec -it -n monitoring prometheus-0 -- curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,sum(rate(http_request_duration_seconds_bucket{namespace="borrow-rate-engine"}[5m]))by(le,service))'
   
   # Check error rates
   kubectl exec -it -n monitoring prometheus-0 -- curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total{namespace="borrow-rate-engine",status=~"5.."}[5m]))by(service)/sum(rate(http_requests_total{namespace="borrow-rate-engine"}[5m]))by(service)'
   ```

2. **Check Pod Startup Times**:
   ```bash
   kubectl get pods -n borrow-rate-engine-${ENV} -o wide --sort-by=.status.startTime
   ```
   Look for pods that are slow to start or stuck in Pending/ContainerCreating.

3. **Verify Readiness Probes**:
   ```bash
   kubectl describe deployment calculation-service -n borrow-rate-engine-${ENV}
   ```
   Check if readiness probe settings are appropriate.

4. **Examine Database Connections**:
   ```bash
   # Check connection count
   kubectl exec -it -n monitoring prometheus-0 -- curl -s 'http://localhost:9090/api/v1/query?query=pg_stat_activity_count{datname="borrow_rate_engine"}'
   ```
   Verify connection pooling is functioning correctly.

5. **Common Issues and Solutions**:
   - Slow pod startup: Optimize container image and startup process
   - Connection pool exhaustion: Adjust pool size or connection handling
   - Resource contention: Adjust resource requests/limits
   - Readiness probe too aggressive: Adjust probe settings
   - Cache warming: Implement cache preloading for new pods

Addressing performance issues during scaling ensures consistent user experience regardless of system scale.

### Database Scaling Issues

Troubleshooting database scaling problems:

1. **Check Database Status**:
   ```bash
   aws rds describe-db-instances --db-instance-identifier borrow-rate-engine-${ENV}
   ```
   Look for:
   - Current status
   - Pending modifications
   - Storage utilization
   - Recent events

2. **Monitor Database Metrics**:
   ```bash
   # Check CPU utilization
   aws cloudwatch get-metric-statistics --namespace AWS/RDS --metric-name CPUUtilization --dimensions Name=DBInstanceIdentifier,Value=borrow-rate-engine-${ENV} --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) --period 300 --statistics Average
   
   # Check connection count
   aws cloudwatch get-metric-statistics --namespace AWS/RDS --metric-name DatabaseConnections --dimensions Name=DBInstanceIdentifier,Value=borrow-rate-engine-${ENV} --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) --period 300 --statistics Average
   ```

3. **Check for Slow Queries**:
   ```sql
   SELECT query, calls, total_time, mean_time, rows
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;
   ```
   Identify queries that might be causing performance issues.

4. **Verify Connection Pooling**:
   ```bash
   kubectl exec -it deployment/data-service -n borrow-rate-engine-${ENV} -- env | grep POOL
   ```
   Check connection pool configuration.

5. **Common Issues and Solutions**:
   - Scaling operation stuck: Check for blocking operations
   - Performance degradation during scaling: Use read replicas
   - Connection limit reached: Adjust max_connections parameter
   - Storage bottleneck: Upgrade to provisioned IOPS
   - Query performance: Optimize indexes and queries

Database scaling issues require careful handling to avoid data loss or extended downtime.

### Cache Scaling Issues

Troubleshooting cache scaling problems:

1. **Check Cache Status**:
   ```bash
   aws elasticache describe-replication-groups --replication-group-id borrow-rate-engine-${ENV}
   ```
   Look for:
   - Current status
   - Pending modifications
   - Node status
   - Recent events

2. **Monitor Cache Metrics**:
   ```bash
   # Check CPU utilization
   aws cloudwatch get-metric-statistics --namespace AWS/ElastiCache --metric-name CPUUtilization --dimensions Name=CacheClusterId,Value=borrow-rate-engine-${ENV}-001 --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) --period 300 --statistics Average
   
   # Check memory usage
   aws cloudwatch get-metric-statistics --namespace AWS/ElastiCache --metric-name DatabaseMemoryUsagePercentage --dimensions Name=CacheClusterId,Value=borrow-rate-engine-${ENV}-001 --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) --period 300 --statistics Average
   ```

3. **Check Cache Performance**:
   ```bash
   # Check hit rate
   kubectl exec -it -n monitoring prometheus-0 -- curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(cache_hits_total[5m]))/(sum(rate(cache_hits_total[5m]))+sum(rate(cache_misses_total[5m])))'
   ```

4. **Verify Cache Client Configuration**:
   ```bash
   kubectl exec -it deployment/cache-service -n borrow-rate-engine-${ENV} -- env | grep REDIS
   ```
   Check Redis client settings.

5. **Common Issues and Solutions**:
   - Scaling operation stuck: Check for cluster events
   - Connection issues during scaling: Implement connection retry logic
   - Memory pressure: Adjust eviction policies
   - Network bandwidth: Monitor network utilization
   - Client configuration: Update endpoints after scaling

Cache scaling issues can impact system performance but typically don't cause data loss due to the nature of caches.

## References

Additional resources for scaling information.

### Internal Documentation

- [Architecture Overview](../architecture/overview.md)
- [Deployment Guide](./deployment.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [Runbooks Directory](./runbooks/)

### External Resources

- [Kubernetes Horizontal Pod Autoscaler](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Kubernetes Cluster Autoscaler](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler)
- [AWS Auto Scaling Documentation](https://docs.aws.amazon.com/autoscaling/)
- [Prometheus Adapter for Kubernetes Metrics](https://github.com/kubernetes-sigs/prometheus-adapter)

### Contact Information

For scaling assistance, contact:

- DevOps Team: devops@example.com
- On-call Engineer: +1-555-123-4567
- Slack Channel: #scaling-support