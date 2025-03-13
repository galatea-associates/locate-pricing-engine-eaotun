/**
 * CloudWatch monitoring infrastructure for the Borrow Rate & Locate Fee Pricing Engine.
 * This module provides functions for creating CloudWatch alarms, metrics, dashboards,
 * and log groups with standardized configurations to monitor system health, performance,
 * and compliance with SLAs.
 */

import * as aws from '@pulumi/aws'; // @pulumi/aws v5.0.0
import * as pulumi from '@pulumi/pulumi'; // @pulumi/pulumi v3.0.0
import { configureAwsProvider, getResourceName, getDefaultTags, AwsResourceOptions } from './aws';

// Global configuration and constants
const config = new pulumi.Config();
const stackName = pulumi.getStack();
const monitoringConfig = new pulumi.Config('monitoring');
const defaultAlarmSnsTopicArn = monitoringConfig.get('alarmSnsTopicArn');
const defaultEvaluationPeriods = 3;
const defaultDatapointsToAlarm = 2;
const tags = getDefaultTags({ Component: 'Monitoring' });

/**
 * Interface defining options for CloudWatch alarm creation
 */
export interface AlarmOptions extends AwsResourceOptions {
    namespace?: string;
    metricName?: string;
    dimensions?: { [key: string]: string };
    comparisonOperator?: string;
    threshold?: number;
    evaluationPeriods?: number;
    datapointsToAlarm?: number;
    statistic?: string;
    period?: number;
    alarmDescription?: string;
    alarmActions?: string[];
    okActions?: string[];
    insufficientDataActions?: string[];
    treatMissingData?: string;
    tags?: { [key: string]: string };
    createComposite?: boolean;
}

/**
 * Interface defining options for CloudWatch metric configuration
 */
export interface MetricOptions {
    namespace?: string;
    metricName?: string;
    dimensions?: { [key: string]: string };
    statistic?: string;
    period?: number;
}

/**
 * Interface defining options for CloudWatch dashboard creation
 */
export interface DashboardOptions extends AwsResourceOptions {
    dashboardName?: string;
    dashboardBody?: string;
    widgets?: WidgetOptions[];
    periodOverride?: string;
    tags?: { [key: string]: string };
}

/**
 * Interface defining options for CloudWatch log group creation
 */
export interface LogGroupOptions extends AwsResourceOptions {
    retentionInDays?: number;
    kmsKeyId?: string;
    tags?: { [key: string]: string };
}

/**
 * Interface defining options for CloudWatch metric filter creation
 */
export interface MetricFilterOptions extends AwsResourceOptions {
    metricTransformations?: MetricTransformation[];
    filterName?: string;
}

/**
 * Interface defining a metric transformation for CloudWatch metric filters
 */
export interface MetricTransformation {
    metricName: string;
    metricNamespace: string;
    metricValue: string;
    dimensions?: { [key: string]: string };
    unit?: string;
    defaultValue?: number;
}

/**
 * Interface defining options for CloudWatch dashboard widgets
 */
export interface WidgetOptions {
    type: string;
    width: number;
    height: number;
    properties: any;
    x?: number;
    y?: number;
}

/**
 * Creates a CloudWatch alarm with standardized configuration
 * 
 * @param name Name of the alarm
 * @param options Alarm configuration options
 * @returns Created CloudWatch alarm resource
 */
export function createCloudWatchAlarm(
    name: string,
    options: AlarmOptions = {}
): aws.cloudwatch.MetricAlarm {
    // Generate a standardized resource name
    const alarmName = getResourceName('alarm', name, { includeStackName: true });
    
    // Extract alarm configuration from options with defaults
    const namespace = options.namespace || 'AWS/Lambda';
    const metricName = options.metricName || 'Errors';
    const dimensions = options.dimensions || {};
    
    // Configure alarm comparison and threshold settings
    const comparisonOperator = options.comparisonOperator || 'GreaterThanThreshold';
    const threshold = options.threshold !== undefined ? options.threshold : 0;
    
    // Set up evaluation periods and datapoints to alarm
    const evaluationPeriods = options.evaluationPeriods || defaultEvaluationPeriods;
    const datapointsToAlarm = options.datapointsToAlarm || defaultDatapointsToAlarm;
    
    // Configure alarm actions using provided SNS topics or default
    const alarmActions = options.alarmActions || (defaultAlarmSnsTopicArn ? [defaultAlarmSnsTopicArn] : []);
    const okActions = options.okActions || [];
    const insufficientDataActions = options.insufficientDataActions || [];
    
    // Create CloudWatch metric alarm with provided configuration
    return new aws.cloudwatch.MetricAlarm(alarmName, {
        alarmName,
        namespace,
        metricName,
        dimensions,
        comparisonOperator,
        threshold,
        evaluationPeriods,
        datapointsToAlarm,
        statistic: options.statistic || 'Sum',
        period: options.period || 60,
        alarmDescription: options.alarmDescription || `Alarm for ${name}`,
        alarmActions,
        okActions,
        insufficientDataActions,
        treatMissingData: options.treatMissingData || 'missing',
        tags: { ...tags, ...(options.tags || {}) }
    });
}

/**
 * Creates a CloudWatch composite alarm that combines multiple alarms with logical operators
 * 
 * @param name Name of the composite alarm
 * @param alarmRuleComponents Array of alarm ARNs and logical operators to build the alarm rule
 * @param options Additional configuration options
 * @returns Created CloudWatch composite alarm resource
 */
export function createCompositeAlarm(
    name: string,
    alarmRuleComponents: string[],
    options: AlarmOptions = {}
): aws.cloudwatch.CompositeAlarm {
    // Generate a standardized resource name
    const alarmName = getResourceName('composite-alarm', name, { includeStackName: true });
    
    // Build alarm rule expression by joining the components
    const alarmRule = alarmRuleComponents.join(' ');
    
    // Configure alarm actions using provided SNS topics or default
    const alarmActions = options.alarmActions || (defaultAlarmSnsTopicArn ? [defaultAlarmSnsTopicArn] : []);
    const okActions = options.okActions || [];
    const insufficientDataActions = options.insufficientDataActions || [];
    
    // Create CloudWatch composite alarm with provided configuration
    return new aws.cloudwatch.CompositeAlarm(alarmName, {
        alarmName,
        alarmRule,
        alarmDescription: options.alarmDescription || `Composite alarm for ${name}`,
        alarmActions,
        okActions,
        insufficientDataActions,
        tags: { ...tags, ...(options.tags || {}) }
    });
}

/**
 * Creates a set of related CloudWatch alarms with consistent configuration
 * 
 * @param baseName Base name for the alarm set
 * @param metricConfigs Array of metric configurations for individual alarms
 * @param options Shared alarm configuration options
 * @returns Object containing all created alarm resources
 */
export function createAlarmSet(
    baseName: string,
    metricConfigs: Array<{
        name: string;
        metricName: string;
        threshold: number;
        comparisonOperator?: string;
        dimensions?: { [key: string]: string };
    }>,
    options: AlarmOptions = {}
): { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } {
    const alarms: { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } = {};
    
    // Create individual alarms for each metric configuration
    metricConfigs.forEach(metricConfig => {
        const alarmName = `${baseName}-${metricConfig.name}`;
        
        // Create the alarm with shared and specific configuration
        alarms[metricConfig.name] = createCloudWatchAlarm(alarmName, {
            ...options,
            metricName: metricConfig.metricName,
            threshold: metricConfig.threshold,
            comparisonOperator: metricConfig.comparisonOperator || options.comparisonOperator,
            dimensions: metricConfig.dimensions || options.dimensions,
            alarmDescription: `${options.alarmDescription || baseName} - ${metricConfig.name}`
        });
    });
    
    // Optionally create a composite alarm that combines all individual alarms
    if (options.createComposite) {
        const alarmArns = Object.values(alarms).map(alarm => pulumi.interpolate`${alarm.arn}`);
        const alarmRuleComponents = alarmArns.map(arn => `ALARM(${arn})`).join(' OR ');
        
        alarms['composite'] = createCompositeAlarm(`${baseName}-composite`, [alarmRuleComponents], options);
    }
    
    return alarms;
}

/**
 * Creates a CloudWatch alarm based on a metric filter applied to log groups
 * 
 * @param name Name of the alarm
 * @param logGroupName Name of the log group to apply the filter to
 * @param filterPattern Pattern to match in the logs
 * @param options Additional configuration options
 * @returns Object containing metric filter and alarm resources
 */
export function createLogMetricAlarm(
    name: string,
    logGroupName: string,
    filterPattern: string,
    options: AlarmOptions & {
        metricName?: string;
        metricNamespace?: string;
        metricValue?: string;
    } = {}
): { metricFilter: aws.cloudwatch.LogMetricFilter; alarm: aws.cloudwatch.MetricAlarm } {
    // Generate standardized resource names
    const filterName = getResourceName('metric-filter', name, { includeStackName: true });
    const metricName = options.metricName || `${name.replace(/[^a-zA-Z0-9]/g, '')}Count`;
    const metricNamespace = options.metricNamespace || 'LogMetrics';
    
    // Create the metric filter to extract metrics from logs
    const metricFilter = new aws.cloudwatch.LogMetricFilter(filterName, {
        logGroupName,
        name: filterName,
        pattern: filterPattern,
        metricTransformation: {
            name: metricName,
            namespace: metricNamespace,
            value: options.metricValue || '1',
        },
    });
    
    // Create an alarm that monitors the resulting metric
    const alarm = createCloudWatchAlarm(name, {
        ...options,
        namespace: metricNamespace,
        metricName,
        threshold: options.threshold || 1,
        comparisonOperator: options.comparisonOperator || 'GreaterThanThreshold',
        evaluationPeriods: options.evaluationPeriods || 1,
        alarmDescription: options.alarmDescription || `Alarm triggered by log pattern: ${filterPattern}`,
    });
    
    return { metricFilter, alarm };
}

/**
 * Creates a CloudWatch dashboard with visualizations for system metrics
 * 
 * @param name Name of the dashboard
 * @param options Dashboard configuration options
 * @returns Created CloudWatch dashboard resource
 */
export function createDashboard(
    name: string,
    options: DashboardOptions = {}
): aws.cloudwatch.Dashboard {
    // Generate a standardized resource name
    const dashboardName = options.dashboardName || getResourceName('dashboard', name, { includeStackName: true });
    
    // Build dashboard body with widgets
    const dashboardBody = options.dashboardBody || buildDashboardBody(options.widgets || []);
    
    // Create CloudWatch dashboard with the configured body
    return new aws.cloudwatch.Dashboard(dashboardName, {
        dashboardName,
        dashboardBody,
        tags: { ...tags, ...(options.tags || {}) }
    });
}

/**
 * Builds a dashboard body JSON from an array of widgets
 * 
 * @param widgets Array of dashboard widgets
 * @returns Dashboard body as a JSON string
 */
function buildDashboardBody(widgets: WidgetOptions[]): string {
    const dashboardObj = {
        widgets: widgets.map(widget => ({
            type: widget.type,
            x: widget.x,
            y: widget.y,
            width: widget.width,
            height: widget.height,
            properties: widget.properties,
        })),
    };
    
    return JSON.stringify(dashboardObj);
}

/**
 * Creates a CloudWatch log group with standardized configuration
 * 
 * @param name Name of the log group
 * @param options Log group configuration options
 * @returns Created CloudWatch log group resource
 */
export function createLogGroup(
    name: string,
    options: LogGroupOptions = {}
): aws.cloudwatch.LogGroup {
    // Generate a standardized resource name
    const logGroupName = getResourceName('log-group', name, { includeStackName: true });
    
    // Create CloudWatch log group with provided configuration
    return new aws.cloudwatch.LogGroup(logGroupName, {
        name: logGroupName,
        retentionInDays: options.retentionInDays || 30,
        kmsKeyId: options.kmsKeyId,
        tags: { ...tags, ...(options.tags || {}) }
    });
}

/**
 * Creates a CloudWatch metric filter for extracting metrics from log data
 * 
 * @param name Name of the metric filter
 * @param logGroupName Name of the log group to apply the filter to
 * @param filterPattern Pattern to match in the logs
 * @param options Additional configuration options
 * @returns Created CloudWatch metric filter resource
 */
export function createMetricFilter(
    name: string,
    logGroupName: string,
    filterPattern: string,
    options: MetricFilterOptions = {}
): aws.cloudwatch.LogMetricFilter {
    // Generate a standardized resource name
    const filterName = options.filterName || getResourceName('metric-filter', name, { includeStackName: true });
    
    // Create CloudWatch metric filter with provided configuration
    return new aws.cloudwatch.LogMetricFilter(filterName, {
        name: filterName,
        logGroupName,
        pattern: filterPattern,
        metricTransformations: options.metricTransformations || [],
    });
}

/**
 * Creates a CloudWatch dashboard focused on a specific service
 * 
 * @param serviceName Name of the service to monitor
 * @param options Dashboard configuration options
 * @returns Created CloudWatch dashboard resource
 */
export function createServiceDashboard(
    serviceName: string,
    options: DashboardOptions = {}
): aws.cloudwatch.Dashboard {
    // Generate service-specific dashboard widgets
    const widgets: WidgetOptions[] = [
        // Service health widget
        {
            type: 'metric',
            width: 12,
            height: 6,
            properties: {
                title: `${serviceName} - Health`,
                view: 'timeSeries',
                region: aws.config.region || 'us-east-1',
                metrics: [
                    [`AWS/ApiGateway`, `5XXError`, `ApiName`, serviceName],
                    [`AWS/ApiGateway`, `4XXError`, `ApiName`, serviceName],
                    [`AWS/ApiGateway`, `Count`, `ApiName`, serviceName],
                ],
                period: 300,
                stat: 'Sum',
                yAxis: { left: { min: 0 } },
            },
        },
        // Performance widget
        {
            type: 'metric',
            width: 12,
            height: 6,
            properties: {
                title: `${serviceName} - Response Time`,
                view: 'timeSeries',
                region: aws.config.region || 'us-east-1',
                metrics: [
                    [`AWS/ApiGateway`, `Latency`, `ApiName`, serviceName, { stat: 'p50' }],
                    [`AWS/ApiGateway`, `Latency`, `ApiName`, serviceName, { stat: 'p90' }],
                    [`AWS/ApiGateway`, `Latency`, `ApiName`, serviceName, { stat: 'p99' }],
                ],
                period: 300,
                yAxis: { left: { min: 0 } },
            },
        },
        // Resource usage widget
        {
            type: 'metric',
            width: 12,
            height: 6,
            properties: {
                title: `${serviceName} - Resource Usage`,
                view: 'timeSeries',
                region: aws.config.region || 'us-east-1',
                metrics: [
                    [`AWS/ECS`, `CPUUtilization`, `ServiceName`, serviceName],
                    [`AWS/ECS`, `MemoryUtilization`, `ServiceName`, serviceName],
                ],
                period: 300,
                stat: 'Average',
                yAxis: { left: { min: 0, max: 100 } },
            },
        },
    ];
    
    // Create dashboard with service-specific widgets
    return createDashboard(`${serviceName}-dashboard`, {
        ...options,
        widgets,
    });
}

/**
 * Creates a CloudWatch dashboard with system-wide metrics and health indicators
 * 
 * @param options Dashboard configuration options
 * @returns Created CloudWatch dashboard resource
 */
export function createSystemDashboard(
    options: DashboardOptions = {}
): aws.cloudwatch.Dashboard {
    // Generate system-wide dashboard widgets for pricing engine
    const widgets: WidgetOptions[] = [
        // System health overview widget
        {
            type: 'text',
            width: 24,
            height: 2,
            properties: {
                markdown: '# Borrow Rate & Locate Fee Pricing Engine - System Dashboard\nMonitoring system health, performance, and SLA compliance for the pricing engine.',
            },
        },
        // API Gateway metrics widget
        {
            type: 'metric',
            width: 12,
            height: 6,
            properties: {
                title: 'API Gateway - Request Volume and Errors',
                view: 'timeSeries',
                region: aws.config.region || 'us-east-1',
                metrics: [
                    [`AWS/ApiGateway`, `Count`, `ApiName`, 'pricing-engine-api'],
                    [`AWS/ApiGateway`, `5XXError`, `ApiName`, 'pricing-engine-api'],
                    [`AWS/ApiGateway`, `4XXError`, `ApiName`, 'pricing-engine-api'],
                ],
                period: 300,
                stat: 'Sum',
                yAxis: { left: { min: 0 } },
            },
        },
        // Calculation Service metrics widget
        {
            type: 'metric',
            width: 12,
            height: 6,
            properties: {
                title: 'Calculation Service - Performance',
                view: 'timeSeries',
                region: aws.config.region || 'us-east-1',
                metrics: [
                    [`BorrowRatePricingEngine`, `CalculationTime`, `Service`, 'CalculationService', { stat: 'Average' }],
                    [`BorrowRatePricingEngine`, `CalculationTime`, `Service`, 'CalculationService', { stat: 'p95' }],
                    [`BorrowRatePricingEngine`, `CalculationsPerSecond`, `Service`, 'CalculationService'],
                ],
                period: 300,
                yAxis: { left: { min: 0 } },
            },
        },
        // External API metrics widget
        {
            type: 'metric',
            width: 12,
            height: 6,
            properties: {
                title: 'External APIs - Response Time and Success Rate',
                view: 'timeSeries',
                region: aws.config.region || 'us-east-1',
                metrics: [
                    [`BorrowRatePricingEngine`, `ApiLatency`, `ApiName`, 'SecLend', { stat: 'Average' }],
                    [`BorrowRatePricingEngine`, `ApiLatency`, `ApiName`, 'MarketData', { stat: 'Average' }],
                    [`BorrowRatePricingEngine`, `ApiSuccessRate`, `ApiName`, 'SecLend'],
                    [`BorrowRatePricingEngine`, `ApiSuccessRate`, `ApiName`, 'MarketData'],
                ],
                period: 300,
                yAxis: { left: { min: 0 } },
            },
        },
        // Database metrics widget
        {
            type: 'metric',
            width: 12,
            height: 6,
            properties: {
                title: 'Database - Performance and Connections',
                view: 'timeSeries',
                region: aws.config.region || 'us-east-1',
                metrics: [
                    [`AWS/RDS`, `CPUUtilization`, `DBInstanceIdentifier`, 'pricing-engine-db'],
                    [`AWS/RDS`, `DatabaseConnections`, `DBInstanceIdentifier`, 'pricing-engine-db'],
                    [`AWS/RDS`, `ReadLatency`, `DBInstanceIdentifier`, 'pricing-engine-db'],
                    [`AWS/RDS`, `WriteLatency`, `DBInstanceIdentifier`, 'pricing-engine-db'],
                ],
                period: 300,
                stat: 'Average',
                yAxis: { left: { min: 0 } },
            },
        },
        // SLA compliance widget
        {
            type: 'metric',
            width: 24,
            height: 6,
            properties: {
                title: 'SLA Compliance',
                view: 'timeSeries',
                region: aws.config.region || 'us-east-1',
                metrics: [
                    [`BorrowRatePricingEngine`, `ApiResponseTime`, { stat: 'p95', label: 'API Response Time (p95) - Target: <100ms' }],
                    [`BorrowRatePricingEngine`, `CalculationAccuracy`, { label: 'Calculation Accuracy - Target: 100%' }],
                    [`BorrowRatePricingEngine`, `Availability`, { label: 'System Availability - Target: 99.95%' }],
                    [`BorrowRatePricingEngine`, `CacheHitRate`, { label: 'Cache Hit Rate - Target: >95%' }],
                ],
                period: 3600,
                annotations: {
                    horizontal: [
                        { value: 100, label: 'API Response Time Threshold (100ms)', color: '#ff9900' },
                        { value: 95, label: 'Cache Hit Rate Threshold (95%)', color: '#ff9900' },
                    ],
                },
            },
        },
    ];
    
    // Create system dashboard with generated widgets
    return createDashboard('system-dashboard', {
        ...options,
        widgets,
    });
}

/**
 * Creates a CloudWatch dashboard focused on business metrics
 * 
 * @param options Dashboard configuration options
 * @returns Created CloudWatch dashboard resource
 */
export function createBusinessDashboard(
    options: DashboardOptions = {}
): aws.cloudwatch.Dashboard {
    // Generate business metrics dashboard widgets for pricing engine
    const widgets: WidgetOptions[] = [
        // Business metrics overview widget
        {
            type: 'text',
            width: 24,
            height: 2,
            properties: {
                markdown: '# Borrow Rate & Locate Fee Pricing Engine - Business Metrics\nKey business metrics for monitoring the performance and usage of the pricing engine.',
            },
        },
        // Fee calculation metrics widget
        {
            type: 'metric',
            width: 12,
            height: 6,
            properties: {
                title: 'Fee Calculations - Volume and Distribution',
                view: 'timeSeries',
                region: aws.config.region || 'us-east-1',
                metrics: [
                    [`BorrowRatePricingEngine`, `TotalCalculations`, { stat: 'SampleCount' }],
                    [`BorrowRatePricingEngine`, `AvgFeeAmount`, { stat: 'Average' }],
                    [`BorrowRatePricingEngine`, `MaxFeeAmount`, { stat: 'Maximum' }],
                ],
                period: 3600,
                yAxis: { left: { min: 0 } },
            },
        },
        // Borrow rate metrics widget
        {
            type: 'metric',
            width: 12,
            height: 6,
            properties: {
                title: 'Borrow Rates - Average by Security Type',
                view: 'timeSeries',
                region: aws.config.region || 'us-east-1',
                metrics: [
                    [`BorrowRatePricingEngine`, `AvgBorrowRate`, `SecurityType`, 'EASY', { stat: 'Average' }],
                    [`BorrowRatePricingEngine`, `AvgBorrowRate`, `SecurityType`, 'MEDIUM', { stat: 'Average' }],
                    [`BorrowRatePricingEngine`, `AvgBorrowRate`, `SecurityType`, 'HARD', { stat: 'Average' }],
                ],
                period: 86400,
                yAxis: { left: { min: 0 } },
            },
        },
        // Client usage metrics widget
        {
            type: 'metric',
            width: 12,
            height: 6,
            properties: {
                title: 'Client Usage - Top 5 Clients',
                view: 'timeSeries',
                region: aws.config.region || 'us-east-1',
                metrics: [
                    [`BorrowRatePricingEngine`, `ClientRequests`, `ClientID`, 'client1'],
                    [`BorrowRatePricingEngine`, `ClientRequests`, `ClientID`, 'client2'],
                    [`BorrowRatePricingEngine`, `ClientRequests`, `ClientID`, 'client3'],
                    [`BorrowRatePricingEngine`, `ClientRequests`, `ClientID`, 'client4'],
                    [`BorrowRatePricingEngine`, `ClientRequests`, `ClientID`, 'client5'],
                ],
                period: 86400,
                stat: 'Sum',
                yAxis: { left: { min: 0 } },
            },
        },
        // Revenue impact metrics widget
        {
            type: 'metric',
            width: 12,
            height: 6,
            properties: {
                title: 'Revenue Impact - Estimated Daily Revenue',
                view: 'timeSeries',
                region: aws.config.region || 'us-east-1',
                metrics: [
                    [`BorrowRatePricingEngine`, `EstimatedRevenue`, { stat: 'Sum' }],
                ],
                period: 86400,
                yAxis: { left: { min: 0 } },
            },
        },
    ];
    
    // Create business dashboard with generated widgets
    return createDashboard('business-dashboard', {
        ...options,
        widgets,
    });
}