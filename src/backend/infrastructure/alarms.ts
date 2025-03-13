/**
 * CloudWatch alarm configurations for the Borrow Rate & Locate Fee Pricing Engine.
 * This module provides functions to create standardized alarms for monitoring system components
 * including API performance, calculation accuracy, database health, and external API availability.
 */

import * as aws from '@pulumi/aws'; // @pulumi/aws ^5.0.0
import * as pulumi from '@pulumi/pulumi'; // @pulumi/pulumi ^3.0.0
import { configureAwsProvider, getResourceName, getDefaultTags, AwsResourceOptions } from './aws';
import { createCloudWatchAlarm, createCompositeAlarm, createAlarmSet, createLogMetricAlarm, AlarmOptions } from './cloudwatch';

// Global configuration and constants
const config = new pulumi.Config();
const stackName = pulumi.getStack();
const monitoringConfig = new pulumi.Config('monitoring');
const defaultAlarmSnsTopicArn = monitoringConfig.get('alarmSnsTopicArn');
const pagerDutySnsTopicArn = monitoringConfig.get('pagerDutySnsTopicArn');
const slackSnsTopicArn = monitoringConfig.get('slackSnsTopicArn');
const emailSnsTopicArn = monitoringConfig.get('emailSnsTopicArn');
const tags = getDefaultTags({ Component: 'Monitoring' });

/**
 * Interface defining threshold values for different alarm severities
 */
export interface AlarmThresholds {
    warning?: { 
        threshold: number;
        evaluationPeriods?: number;
    };
    high?: {
        threshold: number;
        evaluationPeriods?: number;
    };
    critical?: {
        threshold: number;
        evaluationPeriods?: number;
    };
}

/**
 * Interface defining options for API Gateway alarm creation
 */
export interface ApiGatewayAlarmOptions extends AwsResourceOptions {
    apiName?: string;
    stage?: string;
    errorRateThresholds?: AlarmThresholds;
    latencyThresholds?: AlarmThresholds;
    alarmActions?: string[];
    okActions?: string[];
    insufficientDataActions?: string[];
}

/**
 * Interface defining options for Calculation Service alarm creation
 */
export interface CalculationServiceAlarmOptions extends AwsResourceOptions {
    namespace?: string;
    dimensions?: { [key: string]: string };
    errorRateThresholds?: AlarmThresholds;
    latencyThresholds?: AlarmThresholds;
    accuracyThresholds?: AlarmThresholds;
    alarmActions?: string[];
    okActions?: string[];
    insufficientDataActions?: string[];
}

/**
 * Interface defining options for database alarm creation
 */
export interface DatabaseAlarmOptions extends AwsResourceOptions {
    cpuThresholds?: AlarmThresholds;
    memoryThresholds?: AlarmThresholds;
    storageThresholds?: AlarmThresholds;
    connectionThresholds?: AlarmThresholds;
    latencyThresholds?: AlarmThresholds;
    alarmActions?: string[];
    okActions?: string[];
    insufficientDataActions?: string[];
}

/**
 * Interface defining options for cache alarm creation
 */
export interface CacheAlarmOptions extends AwsResourceOptions {
    cpuThresholds?: AlarmThresholds;
    memoryThresholds?: AlarmThresholds;
    evictionThresholds?: AlarmThresholds;
    hitRateThresholds?: AlarmThresholds;
    alarmActions?: string[];
    okActions?: string[];
    insufficientDataActions?: string[];
}

/**
 * Interface defining options for external API alarm creation
 */
export interface ExternalApiAlarmOptions extends AwsResourceOptions {
    namespace?: string;
    dimensions?: { [key: string]: string };
    errorRateThresholds?: AlarmThresholds;
    latencyThresholds?: AlarmThresholds;
    availabilityThresholds?: AlarmThresholds;
    alarmActions?: string[];
    okActions?: string[];
    insufficientDataActions?: string[];
}

/**
 * Interface defining options for log-based alarm creation
 */
export interface LogBasedAlarmOptions extends AwsResourceOptions {
    errorPatterns?: string[];
    warningPatterns?: string[];
    criticalPatterns?: string[];
    thresholds?: AlarmThresholds;
    alarmActions?: string[];
    okActions?: string[];
    insufficientDataActions?: string[];
}

/**
 * Interface defining options for business metric alarm creation
 */
export interface BusinessMetricAlarmOptions extends AwsResourceOptions {
    namespace?: string;
    borrowRateThresholds?: AlarmThresholds;
    feeVolumeThresholds?: AlarmThresholds;
    feeAmountThresholds?: AlarmThresholds;
    fallbackUsageThresholds?: AlarmThresholds;
    alarmActions?: string[];
    okActions?: string[];
    insufficientDataActions?: string[];
}

/**
 * Interface defining options for SLA compliance alarm creation
 */
export interface SlaAlarmOptions extends AwsResourceOptions {
    namespace?: string;
    availabilitySlaThreshold?: number;
    responseTimeSlaThreshold?: number;
    accuracySlaThreshold?: number;
    alarmActions?: string[];
    okActions?: string[];
    insufficientDataActions?: string[];
}

/**
 * Creates a set of CloudWatch alarms for monitoring API Gateway performance and availability
 * 
 * @param apiGatewayName Name of the API Gateway
 * @param options Additional configuration options
 * @returns Object containing all created API Gateway alarm resources
 */
export function createApiGatewayAlarms(
    apiGatewayName: string,
    options: ApiGatewayAlarmOptions = {}
): { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } {
    // Configure API Gateway dimensions
    const apiName = options.apiName || apiGatewayName;
    const stage = options.stage || 'prod';
    const dimensions = {
        ApiName: apiName,
        Stage: stage,
    };
    
    // Set default error rate thresholds based on the Alert Threshold Matrix
    const errorRateThresholds = options.errorRateThresholds || {
        warning: { threshold: 0.5, evaluationPeriods: 3 }, // P3: <99.5% success for 5min
        high: { threshold: 1.0, evaluationPeriods: 3 },    // P2: <99% success for 5min
        critical: { threshold: 2.0, evaluationPeriods: 2 }, // P1: <98% success for 2min
    };
    
    // Set default latency thresholds based on the Alert Threshold Matrix
    const latencyThresholds = options.latencyThresholds || {
        warning: { threshold: 150, evaluationPeriods: 3 }, // P3: >150ms for 10min
        high: { threshold: 250, evaluationPeriods: 3 },    // P2: >250ms for 5min
        critical: { threshold: 500, evaluationPeriods: 2 }, // P1: >500ms for 2min
    };
    
    // Configure notification channels
    const criticalAlarmActions = pagerDutySnsTopicArn ? [pagerDutySnsTopicArn] : [];
    const highAlarmActions = slackSnsTopicArn ? [slackSnsTopicArn] : [];
    const warningAlarmActions = emailSnsTopicArn ? [emailSnsTopicArn] : [];
    
    // Alarms object to hold all created alarms
    const alarms: { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } = {};
    
    // Create 4xx error rate alarm - warning severity
    alarms.clientErrors = createCloudWatchAlarm(`${apiGatewayName}-4xx-errors`, {
        namespace: 'AWS/ApiGateway',
        metricName: '4XXError',
        dimensions,
        threshold: errorRateThresholds.warning?.threshold || 0.5,
        evaluationPeriods: errorRateThresholds.warning?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Warning: API Gateway ${apiGatewayName} 4XX error rate exceeded threshold`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    // Create 5xx error rate alarm - high severity
    alarms.serverErrors = createCloudWatchAlarm(`${apiGatewayName}-5xx-errors`, {
        namespace: 'AWS/ApiGateway',
        metricName: '5XXError',
        dimensions,
        threshold: errorRateThresholds.high?.threshold || 1.0,
        evaluationPeriods: errorRateThresholds.high?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `High: API Gateway ${apiGatewayName} 5XX error rate exceeded threshold`,
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    // Create critical error rate alarm that combines 4xx and 5xx at critical levels
    alarms.criticalErrors = createCloudWatchAlarm(`${apiGatewayName}-critical-errors`, {
        namespace: 'AWS/ApiGateway',
        metricName: '5XXError',
        dimensions,
        threshold: errorRateThresholds.critical?.threshold || 2.0,
        evaluationPeriods: errorRateThresholds.critical?.evaluationPeriods || 2,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Critical: API Gateway ${apiGatewayName} error rate exceeded critical threshold`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create p95 latency alarm - warning severity
    alarms.p95Latency = createCloudWatchAlarm(`${apiGatewayName}-p95-latency`, {
        namespace: 'AWS/ApiGateway',
        metricName: 'Latency',
        dimensions,
        threshold: latencyThresholds.warning?.threshold || 150,
        evaluationPeriods: latencyThresholds.warning?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'p95',
        period: 60,
        alarmDescription: `Warning: API Gateway ${apiGatewayName} p95 latency exceeded threshold`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    // Create p99 latency alarm - high severity
    alarms.p99Latency = createCloudWatchAlarm(`${apiGatewayName}-p99-latency`, {
        namespace: 'AWS/ApiGateway',
        metricName: 'Latency',
        dimensions,
        threshold: latencyThresholds.high?.threshold || 250,
        evaluationPeriods: latencyThresholds.high?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'p99',
        period: 60,
        alarmDescription: `High: API Gateway ${apiGatewayName} p99 latency exceeded threshold`,
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    // Create critical latency alarm
    alarms.criticalLatency = createCloudWatchAlarm(`${apiGatewayName}-critical-latency`, {
        namespace: 'AWS/ApiGateway',
        metricName: 'Latency',
        dimensions,
        threshold: latencyThresholds.critical?.threshold || 500,
        evaluationPeriods: latencyThresholds.critical?.evaluationPeriods || 2,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'p99',
        period: 60,
        alarmDescription: `Critical: API Gateway ${apiGatewayName} latency exceeded critical threshold`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create request count alarm for scaling (informational)
    alarms.requestCount = createCloudWatchAlarm(`${apiGatewayName}-request-count`, {
        namespace: 'AWS/ApiGateway',
        metricName: 'Count',
        dimensions,
        threshold: 700, // Based on capacity planning for auto-scaling
        evaluationPeriods: 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Sum',
        period: 60,
        alarmDescription: `Info: API Gateway ${apiGatewayName} request count high, consider scaling`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Info', ...tags },
    });
    
    // Create composite health alarm that combines critical alarms
    const alarmArns = [
        pulumi.interpolate`${alarms.criticalErrors.arn}`,
        pulumi.interpolate`${alarms.criticalLatency.arn}`,
    ];
    
    // Build alarm rule expression for composite alarm
    const alarmRuleComponents = alarmArns.map(arn => `ALARM(${arn})`);
    const alarmRule = alarmRuleComponents.join(' OR ');
    
    // Create composite alarm
    alarms.overallHealth = createCompositeAlarm(`${apiGatewayName}-health`, [alarmRule], {
        alarmDescription: `Critical: API Gateway ${apiGatewayName} health check failure`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    return alarms;
}

/**
 * Creates a set of CloudWatch alarms for monitoring the Calculation Service
 * 
 * @param serviceName Name of the Calculation Service
 * @param options Additional configuration options
 * @returns Object containing all created Calculation Service alarm resources
 */
export function createCalculationServiceAlarms(
    serviceName: string,
    options: CalculationServiceAlarmOptions = {}
): { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } {
    // Configure service dimensions
    const namespace = options.namespace || 'BorrowRatePricingEngine';
    const dimensions = options.dimensions || {
        Service: serviceName,
    };
    
    // Set default error rate thresholds
    const errorRateThresholds = options.errorRateThresholds || {
        warning: { threshold: 0.1, evaluationPeriods: 3 }, // Warning: >0.1% error rate for 15 min
        high: { threshold: 1.0, evaluationPeriods: 2 },    // High: >1% error rate for 5 min
        critical: { threshold: 2.0, evaluationPeriods: 2 }, // Critical: >2% error rate for 2 min
    };
    
    // Set default latency thresholds
    const latencyThresholds = options.latencyThresholds || {
        warning: { threshold: 25, evaluationPeriods: 3 }, // Warning: >25ms avg for 15 min
        high: { threshold: 40, evaluationPeriods: 2 },    // High: >40ms avg for 5 min
        critical: { threshold: 50, evaluationPeriods: 2 }, // Critical: >50ms avg for 2 min
    };
    
    // Set default accuracy thresholds (100% accuracy required)
    const accuracyThresholds = options.accuracyThresholds || {
        warning: { threshold: 99.99, evaluationPeriods: 1 }, // Warning: <99.99% accuracy
        high: { threshold: 99.9, evaluationPeriods: 1 },     // High: <99.9% accuracy
        critical: { threshold: 99.5, evaluationPeriods: 1 },  // Critical: <99.5% accuracy
    };
    
    // Configure notification channels
    const criticalAlarmActions = pagerDutySnsTopicArn ? [pagerDutySnsTopicArn] : [];
    const highAlarmActions = slackSnsTopicArn ? [slackSnsTopicArn] : [];
    const warningAlarmActions = emailSnsTopicArn ? [emailSnsTopicArn] : [];
    
    // Alarms object to hold all created alarms
    const alarms: { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } = {};
    
    // Create error rate alarms
    alarms.warningErrorRate = createCloudWatchAlarm(`${serviceName}-warning-error-rate`, {
        namespace,
        metricName: 'CalculationErrorRate',
        dimensions,
        threshold: errorRateThresholds.warning?.threshold || 0.1,
        evaluationPeriods: errorRateThresholds.warning?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Warning: Calculation Service ${serviceName} error rate exceeded threshold`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.highErrorRate = createCloudWatchAlarm(`${serviceName}-high-error-rate`, {
        namespace,
        metricName: 'CalculationErrorRate',
        dimensions,
        threshold: errorRateThresholds.high?.threshold || 1.0,
        evaluationPeriods: errorRateThresholds.high?.evaluationPeriods || 2,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `High: Calculation Service ${serviceName} error rate exceeded threshold`,
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    alarms.criticalErrorRate = createCloudWatchAlarm(`${serviceName}-critical-error-rate`, {
        namespace,
        metricName: 'CalculationErrorRate',
        dimensions,
        threshold: errorRateThresholds.critical?.threshold || 2.0,
        evaluationPeriods: errorRateThresholds.critical?.evaluationPeriods || 2,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Critical: Calculation Service ${serviceName} error rate exceeded critical threshold`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create latency alarms
    alarms.warningLatency = createCloudWatchAlarm(`${serviceName}-warning-latency`, {
        namespace,
        metricName: 'CalculationTime',
        dimensions,
        threshold: latencyThresholds.warning?.threshold || 25,
        evaluationPeriods: latencyThresholds.warning?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Warning: Calculation Service ${serviceName} latency exceeded threshold`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.highLatency = createCloudWatchAlarm(`${serviceName}-high-latency`, {
        namespace,
        metricName: 'CalculationTime',
        dimensions,
        threshold: latencyThresholds.high?.threshold || 40,
        evaluationPeriods: latencyThresholds.high?.evaluationPeriods || 2,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'p95',
        period: 60,
        alarmDescription: `High: Calculation Service ${serviceName} p95 latency exceeded threshold`,
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    alarms.criticalLatency = createCloudWatchAlarm(`${serviceName}-critical-latency`, {
        namespace,
        metricName: 'CalculationTime',
        dimensions,
        threshold: latencyThresholds.critical?.threshold || 50,
        evaluationPeriods: latencyThresholds.critical?.evaluationPeriods || 2,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'p95',
        period: 60,
        alarmDescription: `Critical: Calculation Service ${serviceName} p95 latency exceeded critical threshold`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create accuracy alarms
    alarms.warningAccuracy = createCloudWatchAlarm(`${serviceName}-warning-accuracy`, {
        namespace,
        metricName: 'CalculationAccuracy',
        dimensions,
        threshold: accuracyThresholds.warning?.threshold || 99.99,
        evaluationPeriods: accuracyThresholds.warning?.evaluationPeriods || 1,
        comparisonOperator: 'LessThanThreshold',
        statistic: 'Average',
        period: 300, // 5 minutes
        alarmDescription: `Warning: Calculation Service ${serviceName} accuracy below threshold`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.criticalAccuracy = createCloudWatchAlarm(`${serviceName}-critical-accuracy`, {
        namespace,
        metricName: 'CalculationAccuracy',
        dimensions,
        threshold: accuracyThresholds.critical?.threshold || 99.5,
        evaluationPeriods: accuracyThresholds.critical?.evaluationPeriods || 1,
        comparisonOperator: 'LessThanThreshold',
        statistic: 'Average',
        period: 300, // 5 minutes
        alarmDescription: `Critical: Calculation Service ${serviceName} accuracy below critical threshold`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create throughput alarm (informational for scaling)
    alarms.throughput = createCloudWatchAlarm(`${serviceName}-throughput`, {
        namespace,
        metricName: 'CalculationsPerSecond',
        dimensions,
        threshold: 600, // Based on capacity planning for auto-scaling
        evaluationPeriods: 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Sum',
        period: 60,
        alarmDescription: `Info: Calculation Service ${serviceName} approaching capacity, consider scaling`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Info', ...tags },
    });
    
    // Create composite health alarm that combines critical alarms
    const alarmArns = [
        pulumi.interpolate`${alarms.criticalErrorRate.arn}`,
        pulumi.interpolate`${alarms.criticalLatency.arn}`,
        pulumi.interpolate`${alarms.criticalAccuracy.arn}`,
    ];
    
    // Build alarm rule expression for composite alarm
    const alarmRuleComponents = alarmArns.map(arn => `ALARM(${arn})`);
    const alarmRule = alarmRuleComponents.join(' OR ');
    
    // Create composite alarm
    alarms.overallHealth = createCompositeAlarm(`${serviceName}-health`, [alarmRule], {
        alarmDescription: `Critical: Calculation Service ${serviceName} health check failure`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    return alarms;
}

/**
 * Creates a set of CloudWatch alarms for monitoring RDS database health and performance
 * 
 * @param dbInstanceIdentifier RDS database instance identifier
 * @param options Additional configuration options
 * @returns Object containing all created database alarm resources
 */
export function createDatabaseAlarms(
    dbInstanceIdentifier: string,
    options: DatabaseAlarmOptions = {}
): { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } {
    // Configure database dimensions
    const dimensions = {
        DBInstanceIdentifier: dbInstanceIdentifier,
    };
    
    // Set default CPU utilization thresholds
    const cpuThresholds = options.cpuThresholds || {
        warning: { threshold: 70, evaluationPeriods: 3 }, // Warning: >70% for 15 min
        high: { threshold: 85, evaluationPeriods: 3 },    // High: >85% for 5 min
        critical: { threshold: 95, evaluationPeriods: 2 }, // Critical: >95% for 2 min
    };
    
    // Set default memory usage thresholds
    const memoryThresholds = options.memoryThresholds || {
        warning: { threshold: 75, evaluationPeriods: 3 }, // Warning: >75% for 15 min
        high: { threshold: 85, evaluationPeriods: 3 },    // High: >85% for 5 min
        critical: { threshold: 95, evaluationPeriods: 2 }, // Critical: >95% for 2 min
    };
    
    // Set default storage space thresholds
    const storageThresholds = options.storageThresholds || {
        warning: { threshold: 75, evaluationPeriods: 3 }, // Warning: >75% for 15 min
        high: { threshold: 85, evaluationPeriods: 3 },    // High: >85% for 5 min
        critical: { threshold: 95, evaluationPeriods: 2 }, // Critical: >95% for 2 min
    };
    
    // Set default connection count thresholds
    const connectionThresholds = options.connectionThresholds || {
        warning: { threshold: 70, evaluationPeriods: 3 }, // Warning: >70% of max for 15 min
        high: { threshold: 85, evaluationPeriods: 3 },    // High: >85% of max for 5 min
        critical: { threshold: 95, evaluationPeriods: 2 }, // Critical: >95% of max for 2 min
    };
    
    // Set default database latency thresholds
    const latencyThresholds = options.latencyThresholds || {
        warning: { threshold: 50, evaluationPeriods: 3 }, // Warning: >50ms for 15 min
        high: { threshold: 100, evaluationPeriods: 3 },   // High: >100ms for 5 min
        critical: { threshold: 200, evaluationPeriods: 2 }, // Critical: >200ms for 2 min
    };
    
    // Configure notification channels
    const criticalAlarmActions = pagerDutySnsTopicArn ? [pagerDutySnsTopicArn] : [];
    const highAlarmActions = slackSnsTopicArn ? [slackSnsTopicArn] : [];
    const warningAlarmActions = emailSnsTopicArn ? [emailSnsTopicArn] : [];
    
    // Alarms object to hold all created alarms
    const alarms: { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } = {};
    
    // Create CPU utilization alarms
    alarms.warningCpu = createCloudWatchAlarm(`${dbInstanceIdentifier}-warning-cpu`, {
        namespace: 'AWS/RDS',
        metricName: 'CPUUtilization',
        dimensions,
        threshold: cpuThresholds.warning?.threshold || 70,
        evaluationPeriods: cpuThresholds.warning?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Warning: Database ${dbInstanceIdentifier} CPU utilization exceeded threshold`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.criticalCpu = createCloudWatchAlarm(`${dbInstanceIdentifier}-critical-cpu`, {
        namespace: 'AWS/RDS',
        metricName: 'CPUUtilization',
        dimensions,
        threshold: cpuThresholds.critical?.threshold || 95,
        evaluationPeriods: cpuThresholds.critical?.evaluationPeriods || 2,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Critical: Database ${dbInstanceIdentifier} CPU utilization exceeded critical threshold`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create memory usage alarms
    alarms.warningMemory = createCloudWatchAlarm(`${dbInstanceIdentifier}-warning-memory`, {
        namespace: 'AWS/RDS',
        metricName: 'FreeableMemory',
        dimensions,
        threshold: 1024 * 1024 * 1024 * (100 - memoryThresholds.warning?.threshold || 75) / 100, // Convert % free to bytes
        evaluationPeriods: memoryThresholds.warning?.evaluationPeriods || 3,
        comparisonOperator: 'LessThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Warning: Database ${dbInstanceIdentifier} freeable memory below threshold`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.criticalMemory = createCloudWatchAlarm(`${dbInstanceIdentifier}-critical-memory`, {
        namespace: 'AWS/RDS',
        metricName: 'FreeableMemory',
        dimensions,
        threshold: 1024 * 1024 * 1024 * (100 - memoryThresholds.critical?.threshold || 95) / 100, // Convert % free to bytes
        evaluationPeriods: memoryThresholds.critical?.evaluationPeriods || 2,
        comparisonOperator: 'LessThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Critical: Database ${dbInstanceIdentifier} freeable memory below critical threshold`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create storage space alarms
    alarms.warningStorage = createCloudWatchAlarm(`${dbInstanceIdentifier}-warning-storage`, {
        namespace: 'AWS/RDS',
        metricName: 'FreeStorageSpace',
        dimensions,
        threshold: 1024 * 1024 * 1024 * (100 - storageThresholds.warning?.threshold || 75) / 100, // Convert % free to bytes
        evaluationPeriods: storageThresholds.warning?.evaluationPeriods || 3,
        comparisonOperator: 'LessThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Warning: Database ${dbInstanceIdentifier} free storage space below threshold`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.criticalStorage = createCloudWatchAlarm(`${dbInstanceIdentifier}-critical-storage`, {
        namespace: 'AWS/RDS',
        metricName: 'FreeStorageSpace',
        dimensions,
        threshold: 1024 * 1024 * 1024 * (100 - storageThresholds.critical?.threshold || 95) / 100, // Convert % free to bytes
        evaluationPeriods: storageThresholds.critical?.evaluationPeriods || 2,
        comparisonOperator: 'LessThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Critical: Database ${dbInstanceIdentifier} free storage space below critical threshold`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create database connections alarm
    alarms.connections = createCloudWatchAlarm(`${dbInstanceIdentifier}-connections`, {
        namespace: 'AWS/RDS',
        metricName: 'DatabaseConnections',
        dimensions,
        threshold: connectionThresholds.high?.threshold || 85, // Using % of max connections
        evaluationPeriods: connectionThresholds.high?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `High: Database ${dbInstanceIdentifier} connection count approaching limit`,
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    // Create database latency alarms
    alarms.readLatency = createCloudWatchAlarm(`${dbInstanceIdentifier}-read-latency`, {
        namespace: 'AWS/RDS',
        metricName: 'ReadLatency',
        dimensions,
        threshold: latencyThresholds.high?.threshold || 100,
        evaluationPeriods: latencyThresholds.high?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `High: Database ${dbInstanceIdentifier} read latency exceeded threshold`,
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    alarms.writeLatency = createCloudWatchAlarm(`${dbInstanceIdentifier}-write-latency`, {
        namespace: 'AWS/RDS',
        metricName: 'WriteLatency',
        dimensions,
        threshold: latencyThresholds.high?.threshold || 100,
        evaluationPeriods: latencyThresholds.high?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `High: Database ${dbInstanceIdentifier} write latency exceeded threshold`,
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    // Create composite health alarm that combines critical alarms
    const alarmArns = [
        pulumi.interpolate`${alarms.criticalCpu.arn}`,
        pulumi.interpolate`${alarms.criticalMemory.arn}`,
        pulumi.interpolate`${alarms.criticalStorage.arn}`,
    ];
    
    // Build alarm rule expression for composite alarm
    const alarmRuleComponents = alarmArns.map(arn => `ALARM(${arn})`);
    const alarmRule = alarmRuleComponents.join(' OR ');
    
    // Create composite alarm
    alarms.overallHealth = createCompositeAlarm(`${dbInstanceIdentifier}-health`, [alarmRule], {
        alarmDescription: `Critical: Database ${dbInstanceIdentifier} health check failure`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    return alarms;
}

/**
 * Creates a set of CloudWatch alarms for monitoring Redis cache health and performance
 * 
 * @param cacheClusterId ElastiCache Redis cluster identifier
 * @param options Additional configuration options
 * @returns Object containing all created cache alarm resources
 */
export function createCacheAlarms(
    cacheClusterId: string,
    options: CacheAlarmOptions = {}
): { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } {
    // Configure cache dimensions
    const dimensions = {
        CacheClusterId: cacheClusterId,
    };
    
    // Set default CPU utilization thresholds
    const cpuThresholds = options.cpuThresholds || {
        warning: { threshold: 70, evaluationPeriods: 3 }, // Warning: >70% for 15 min
        high: { threshold: 85, evaluationPeriods: 3 },    // High: >85% for 5 min
        critical: { threshold: 95, evaluationPeriods: 2 }, // Critical: >95% for 2 min
    };
    
    // Set default memory usage thresholds
    const memoryThresholds = options.memoryThresholds || {
        warning: { threshold: 70, evaluationPeriods: 3 }, // Warning: >70% for 15 min
        high: { threshold: 85, evaluationPeriods: 3 },    // High: >85% for 5 min
        critical: { threshold: 95, evaluationPeriods: 2 }, // Critical: >95% for 2 min
    };
    
    // Set default eviction thresholds
    const evictionThresholds = options.evictionThresholds || {
        warning: { threshold: 10, evaluationPeriods: 3 }, // Warning: >10 evictions/sec for 15 min
        high: { threshold: 100, evaluationPeriods: 3 },   // High: >100 evictions/sec for 5 min
        critical: { threshold: 1000, evaluationPeriods: 2 }, // Critical: >1000 evictions/sec for 2 min
    };
    
    // Set default hit rate thresholds
    const hitRateThresholds = options.hitRateThresholds || {
        warning: { threshold: 90, evaluationPeriods: 3 }, // Warning: <90% hit rate for 30 min
        high: { threshold: 80, evaluationPeriods: 3 },    // High: <80% hit rate for 15 min
        critical: { threshold: 70, evaluationPeriods: 3 }, // Critical: <70% hit rate for 5 min
    };
    
    // Configure notification channels
    const criticalAlarmActions = pagerDutySnsTopicArn ? [pagerDutySnsTopicArn] : [];
    const highAlarmActions = slackSnsTopicArn ? [slackSnsTopicArn] : [];
    const warningAlarmActions = emailSnsTopicArn ? [emailSnsTopicArn] : [];
    
    // Alarms object to hold all created alarms
    const alarms: { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } = {};
    
    // Create CPU utilization alarms
    alarms.warningCpu = createCloudWatchAlarm(`${cacheClusterId}-warning-cpu`, {
        namespace: 'AWS/ElastiCache',
        metricName: 'CPUUtilization',
        dimensions,
        threshold: cpuThresholds.warning?.threshold || 70,
        evaluationPeriods: cpuThresholds.warning?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Warning: Cache ${cacheClusterId} CPU utilization exceeded threshold`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.criticalCpu = createCloudWatchAlarm(`${cacheClusterId}-critical-cpu`, {
        namespace: 'AWS/ElastiCache',
        metricName: 'CPUUtilization',
        dimensions,
        threshold: cpuThresholds.critical?.threshold || 95,
        evaluationPeriods: cpuThresholds.critical?.evaluationPeriods || 2,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Critical: Cache ${cacheClusterId} CPU utilization exceeded critical threshold`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create memory usage alarms
    alarms.warningMemory = createCloudWatchAlarm(`${cacheClusterId}-warning-memory`, {
        namespace: 'AWS/ElastiCache',
        metricName: 'DatabaseMemoryUsagePercentage',
        dimensions,
        threshold: memoryThresholds.warning?.threshold || 70,
        evaluationPeriods: memoryThresholds.warning?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Warning: Cache ${cacheClusterId} memory usage exceeded threshold`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.criticalMemory = createCloudWatchAlarm(`${cacheClusterId}-critical-memory`, {
        namespace: 'AWS/ElastiCache',
        metricName: 'DatabaseMemoryUsagePercentage',
        dimensions,
        threshold: memoryThresholds.critical?.threshold || 95,
        evaluationPeriods: memoryThresholds.critical?.evaluationPeriods || 2,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Critical: Cache ${cacheClusterId} memory usage exceeded critical threshold`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create eviction alarms
    alarms.highEvictions = createCloudWatchAlarm(`${cacheClusterId}-high-evictions`, {
        namespace: 'AWS/ElastiCache',
        metricName: 'Evictions',
        dimensions,
        threshold: evictionThresholds.high?.threshold || 100,
        evaluationPeriods: evictionThresholds.high?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Sum',
        period: 60,
        alarmDescription: `High: Cache ${cacheClusterId} eviction rate exceeded threshold`,
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    // Create cache hit rate alarms
    alarms.lowHitRate = createCloudWatchAlarm(`${cacheClusterId}-low-hit-rate`, {
        namespace: 'AWS/ElastiCache',
        metricName: 'CacheHitRate',
        dimensions,
        threshold: hitRateThresholds.warning?.threshold || 90,
        evaluationPeriods: hitRateThresholds.warning?.evaluationPeriods || 3,
        comparisonOperator: 'LessThanThreshold',
        statistic: 'Average',
        period: 300, // 5 minutes
        alarmDescription: `Warning: Cache ${cacheClusterId} hit rate below threshold`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.criticalLowHitRate = createCloudWatchAlarm(`${cacheClusterId}-critical-low-hit-rate`, {
        namespace: 'AWS/ElastiCache',
        metricName: 'CacheHitRate',
        dimensions,
        threshold: hitRateThresholds.critical?.threshold || 70,
        evaluationPeriods: hitRateThresholds.critical?.evaluationPeriods || 3,
        comparisonOperator: 'LessThanThreshold',
        statistic: 'Average',
        period: 300, // 5 minutes
        alarmDescription: `Critical: Cache ${cacheClusterId} hit rate below critical threshold`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create connection count alarm
    alarms.connectionCount = createCloudWatchAlarm(`${cacheClusterId}-connections`, {
        namespace: 'AWS/ElastiCache',
        metricName: 'CurrConnections',
        dimensions,
        threshold: 5000, // Depends on instance type and requirements
        evaluationPeriods: 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Maximum',
        period: 60,
        alarmDescription: `High: Cache ${cacheClusterId} connection count approaching limit`,
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    // Create composite health alarm that combines critical alarms
    const alarmArns = [
        pulumi.interpolate`${alarms.criticalCpu.arn}`,
        pulumi.interpolate`${alarms.criticalMemory.arn}`,
        pulumi.interpolate`${alarms.criticalLowHitRate.arn}`,
    ];
    
    // Build alarm rule expression for composite alarm
    const alarmRuleComponents = alarmArns.map(arn => `ALARM(${arn})`);
    const alarmRule = alarmRuleComponents.join(' OR ');
    
    // Create composite alarm
    alarms.overallHealth = createCompositeAlarm(`${cacheClusterId}-health`, [alarmRule], {
        alarmDescription: `Critical: Cache ${cacheClusterId} health check failure`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    return alarms;
}

/**
 * Creates a set of CloudWatch alarms for monitoring external API availability and performance
 * 
 * @param apiName Name of the external API (e.g., 'SecLend', 'MarketData')
 * @param options Additional configuration options
 * @returns Object containing all created external API alarm resources
 */
export function createExternalApiAlarms(
    apiName: string,
    options: ExternalApiAlarmOptions = {}
): { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } {
    // Configure API dimensions
    const namespace = options.namespace || 'BorrowRatePricingEngine';
    const dimensions = options.dimensions || {
        ApiName: apiName,
    };
    
    // Set default error rate thresholds
    const errorRateThresholds = options.errorRateThresholds || {
        warning: { threshold: 1, evaluationPeriods: 3 },  // Warning: >1% errors for 15 min
        high: { threshold: 5, evaluationPeriods: 3 },     // High: >5% errors for 5 min
        critical: { threshold: 10, evaluationPeriods: 2 }, // Critical: >10% errors for 2 min
    };
    
    // Set default latency thresholds
    const latencyThresholds = options.latencyThresholds || {
        warning: { threshold: 300, evaluationPeriods: 3 }, // Warning: >300ms for 15 min
        high: { threshold: 500, evaluationPeriods: 3 },    // High: >500ms for 5 min
        critical: { threshold: 1000, evaluationPeriods: 2 }, // Critical: >1000ms for 2 min
    };
    
    // Set default availability thresholds
    const availabilityThresholds = options.availabilityThresholds || {
        warning: { threshold: 99, evaluationPeriods: 3 },  // Warning: <99% for 15 min
        high: { threshold: 95, evaluationPeriods: 3 },     // High: <95% for 5 min
        critical: { threshold: 90, evaluationPeriods: 2 }, // Critical: <90% for 2 min
    };
    
    // Configure notification channels
    const criticalAlarmActions = pagerDutySnsTopicArn ? [pagerDutySnsTopicArn] : [];
    const highAlarmActions = slackSnsTopicArn ? [slackSnsTopicArn] : [];
    const warningAlarmActions = emailSnsTopicArn ? [emailSnsTopicArn] : [];
    
    // Alarms object to hold all created alarms
    const alarms: { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } = {};
    
    // Create error rate alarms
    alarms.warningErrorRate = createCloudWatchAlarm(`${apiName}-warning-error-rate`, {
        namespace,
        metricName: 'ApiErrorRate',
        dimensions,
        threshold: errorRateThresholds.warning?.threshold || 1,
        evaluationPeriods: errorRateThresholds.warning?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Warning: External API ${apiName} error rate exceeded threshold`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.highErrorRate = createCloudWatchAlarm(`${apiName}-high-error-rate`, {
        namespace,
        metricName: 'ApiErrorRate',
        dimensions,
        threshold: errorRateThresholds.high?.threshold || 5,
        evaluationPeriods: errorRateThresholds.high?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `High: External API ${apiName} error rate exceeded threshold`,
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    alarms.criticalErrorRate = createCloudWatchAlarm(`${apiName}-critical-error-rate`, {
        namespace,
        metricName: 'ApiErrorRate',
        dimensions,
        threshold: errorRateThresholds.critical?.threshold || 10,
        evaluationPeriods: errorRateThresholds.critical?.evaluationPeriods || 2,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Critical: External API ${apiName} error rate exceeded critical threshold`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create latency alarms
    alarms.warningLatency = createCloudWatchAlarm(`${apiName}-warning-latency`, {
        namespace,
        metricName: 'ApiLatency',
        dimensions,
        threshold: latencyThresholds.warning?.threshold || 300,
        evaluationPeriods: latencyThresholds.warning?.evaluationPeriods || 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Warning: External API ${apiName} latency exceeded threshold`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.criticalLatency = createCloudWatchAlarm(`${apiName}-critical-latency`, {
        namespace,
        metricName: 'ApiLatency',
        dimensions,
        threshold: latencyThresholds.critical?.threshold || 1000,
        evaluationPeriods: latencyThresholds.critical?.evaluationPeriods || 2,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 60,
        alarmDescription: `Critical: External API ${apiName} latency exceeded critical threshold`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create availability alarms
    alarms.warningAvailability = createCloudWatchAlarm(`${apiName}-warning-availability`, {
        namespace,
        metricName: 'ApiAvailability',
        dimensions,
        threshold: availabilityThresholds.warning?.threshold || 99,
        evaluationPeriods: availabilityThresholds.warning?.evaluationPeriods || 3,
        comparisonOperator: 'LessThanThreshold',
        statistic: 'Average',
        period: 300, // 5 minutes
        alarmDescription: `Warning: External API ${apiName} availability below threshold`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.criticalAvailability = createCloudWatchAlarm(`${apiName}-critical-availability`, {
        namespace,
        metricName: 'ApiAvailability',
        dimensions,
        threshold: availabilityThresholds.critical?.threshold || 90,
        evaluationPeriods: availabilityThresholds.critical?.evaluationPeriods || 2,
        comparisonOperator: 'LessThanThreshold',
        statistic: 'Average',
        period: 300, // 5 minutes
        alarmDescription: `Critical: External API ${apiName} availability below critical threshold`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create circuit breaker status alarm
    alarms.circuitBreakerOpen = createCloudWatchAlarm(`${apiName}-circuit-breaker`, {
        namespace,
        metricName: 'CircuitBreakerState',
        dimensions,
        threshold: 1, // 1 indicates circuit open
        evaluationPeriods: 1,
        comparisonOperator: 'GreaterThanOrEqualToThreshold',
        statistic: 'Maximum',
        period: 60,
        alarmDescription: `High: External API ${apiName} circuit breaker open`,
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    // Create composite health alarm that combines critical alarms
    const alarmArns = [
        pulumi.interpolate`${alarms.criticalErrorRate.arn}`,
        pulumi.interpolate`${alarms.criticalLatency.arn}`,
        pulumi.interpolate`${alarms.criticalAvailability.arn}`,
    ];
    
    // Build alarm rule expression for composite alarm
    const alarmRuleComponents = alarmArns.map(arn => `ALARM(${arn})`);
    const alarmRule = alarmRuleComponents.join(' OR ');
    
    // Create composite alarm
    alarms.overallHealth = createCompositeAlarm(`${apiName}-health`, [alarmRule], {
        alarmDescription: `Critical: External API ${apiName} health check failure`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    return alarms;
}

/**
 * Creates CloudWatch alarms based on log patterns for detecting issues in application logs
 * 
 * @param logGroupName Name of the CloudWatch log group to monitor
 * @param options Additional configuration options
 * @returns Object containing all created log-based alarm resources
 */
export function createLogBasedAlarms(
    logGroupName: string,
    options: LogBasedAlarmOptions = {}
): { [key: string]: aws.cloudwatch.LogMetricFilter | aws.cloudwatch.MetricAlarm } {
    // Define standard error and warning patterns if not provided
    const errorPatterns = options.errorPatterns || [
        'ERROR',
        'Exception',
        'fail',
        'Fail',
        'FAIL',
    ];
    
    const warningPatterns = options.warningPatterns || [
        'WARN',
        'Warning',
        'warning',
    ];
    
    const criticalPatterns = options.criticalPatterns || [
        'FATAL',
        'CRITICAL',
        'OutOfMemory',
        'StackOverflow',
    ];
    
    // Set default thresholds
    const thresholds = options.thresholds || {
        warning: { threshold: 5, evaluationPeriods: 1 },  // Warning: >5 warnings in 5 min
        high: { threshold: 5, evaluationPeriods: 1 },     // High: >5 errors in 5 min
        critical: { threshold: 1, evaluationPeriods: 1 }, // Critical: >1 critical error in 5 min
    };
    
    // Configure notification channels
    const criticalAlarmActions = pagerDutySnsTopicArn ? [pagerDutySnsTopicArn] : [];
    const highAlarmActions = slackSnsTopicArn ? [slackSnsTopicArn] : [];
    const warningAlarmActions = emailSnsTopicArn ? [emailSnsTopicArn] : [];
    
    // Extract log group name from full ARN if provided
    const logGroupNameShort = logGroupName.split(':').pop()?.split('/').pop() || logGroupName;
    const serviceName = logGroupNameShort.split('-').slice(0, -2).join('-') || 'app';
    
    // Results object to hold all created resources
    const resources: { [key: string]: aws.cloudwatch.LogMetricFilter | aws.cloudwatch.MetricAlarm } = {};
    
    // Create metric filter and alarm for warnings
    const warningFilterPattern = warningPatterns.map(pattern => `"${pattern}"`).join(' ');
    const warningMetricFilter = new aws.cloudwatch.LogMetricFilter(`${serviceName}-warning-filter`, {
        logGroupName,
        name: getResourceName('metric-filter', `${serviceName}-warnings`, { includeStackName: true }),
        pattern: `{${warningFilterPattern}}`,
        metricTransformation: {
            name: `${serviceName}Warnings`,
            namespace: 'LogMetrics',
            value: '1',
            unit: 'Count',
        },
    });
    
    resources.warningFilter = warningMetricFilter;
    
    resources.warningAlarm = createCloudWatchAlarm(`${serviceName}-warnings`, {
        namespace: 'LogMetrics',
        metricName: `${serviceName}Warnings`,
        threshold: thresholds.warning?.threshold || 5,
        evaluationPeriods: thresholds.warning?.evaluationPeriods || 1,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Sum',
        period: 300, // 5 minutes
        alarmDescription: `Warning: High number of warnings in ${serviceName} logs`,
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    // Create metric filter and alarm for errors
    const errorFilterPattern = errorPatterns.map(pattern => `"${pattern}"`).join(' ');
    const errorMetricFilter = new aws.cloudwatch.LogMetricFilter(`${serviceName}-error-filter`, {
        logGroupName,
        name: getResourceName('metric-filter', `${serviceName}-errors`, { includeStackName: true }),
        pattern: `{${errorFilterPattern}}`,
        metricTransformation: {
            name: `${serviceName}Errors`,
            namespace: 'LogMetrics',
            value: '1',
            unit: 'Count',
        },
    });
    
    resources.errorFilter = errorMetricFilter;
    
    resources.errorAlarm = createCloudWatchAlarm(`${serviceName}-errors`, {
        namespace: 'LogMetrics',
        metricName: `${serviceName}Errors`,
        threshold: thresholds.high?.threshold || 5,
        evaluationPeriods: thresholds.high?.evaluationPeriods || 1,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Sum',
        period: 300, // 5 minutes
        alarmDescription: `High: High number of errors in ${serviceName} logs`,
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    // Create metric filter and alarm for critical errors
    const criticalFilterPattern = criticalPatterns.map(pattern => `"${pattern}"`).join(' ');
    const criticalMetricFilter = new aws.cloudwatch.LogMetricFilter(`${serviceName}-critical-filter`, {
        logGroupName,
        name: getResourceName('metric-filter', `${serviceName}-critical-errors`, { includeStackName: true }),
        pattern: `{${criticalFilterPattern}}`,
        metricTransformation: {
            name: `${serviceName}CriticalErrors`,
            namespace: 'LogMetrics',
            value: '1',
            unit: 'Count',
        },
    });
    
    resources.criticalFilter = criticalMetricFilter;
    
    resources.criticalAlarm = createCloudWatchAlarm(`${serviceName}-critical-errors`, {
        namespace: 'LogMetrics',
        metricName: `${serviceName}CriticalErrors`,
        threshold: thresholds.critical?.threshold || 1,
        evaluationPeriods: thresholds.critical?.evaluationPeriods || 1,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Sum',
        period: 300, // 5 minutes
        alarmDescription: `Critical: Critical errors detected in ${serviceName} logs`,
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    // Create specific metric filters for important application errors
    if (serviceName === 'calculation-service') {
        // Add a specific filter for calculation errors
        const calcErrorFilter = new aws.cloudwatch.LogMetricFilter(`calculation-error-filter`, {
            logGroupName,
            name: getResourceName('metric-filter', 'calculation-errors', { includeStackName: true }),
            pattern: '{ $.error = "CalculationError" }',
            metricTransformation: {
                name: 'CalculationErrors',
                namespace: 'LogMetrics',
                value: '1',
                unit: 'Count',
            },
        });
        
        resources.calculationErrorFilter = calcErrorFilter;
        
        resources.calculationErrorAlarm = createCloudWatchAlarm('calculation-errors', {
            namespace: 'LogMetrics',
            metricName: 'CalculationErrors',
            threshold: 1,
            evaluationPeriods: 1,
            comparisonOperator: 'GreaterThanThreshold',
            statistic: 'Sum',
            period: 60, // 1 minute - more sensitive for calculation errors
            alarmDescription: 'Critical: Formula calculation errors detected',
            alarmActions: criticalAlarmActions,
            tags: { Severity: 'Critical', ...tags },
        });
    }
    
    if (serviceName === 'data-service') {
        // Add a specific filter for external API failures
        const apiFailureFilter = new aws.cloudwatch.LogMetricFilter(`api-failure-filter`, {
            logGroupName,
            name: getResourceName('metric-filter', 'external-api-failures', { includeStackName: true }),
            pattern: '{ $.error = "ExternalApiFailure" }',
            metricTransformation: {
                name: 'ExternalApiFailures',
                namespace: 'LogMetrics',
                value: '1',
                unit: 'Count',
            },
        });
        
        resources.apiFailureFilter = apiFailureFilter;
        
        resources.apiFailureAlarm = createCloudWatchAlarm('external-api-failures', {
            namespace: 'LogMetrics',
            metricName: 'ExternalApiFailures',
            threshold: 3,
            evaluationPeriods: 1,
            comparisonOperator: 'GreaterThanThreshold',
            statistic: 'Sum',
            period: 60, // 1 minute
            alarmDescription: 'High: Multiple external API failures detected',
            alarmActions: highAlarmActions,
            tags: { Severity: 'High', ...tags },
        });
    }
    
    return resources;
}

/**
 * Creates CloudWatch alarms for business metrics to detect anomalies in calculation patterns
 * 
 * @param options Additional configuration options
 * @returns Object containing all created business metric alarm resources
 */
export function createBusinessMetricAlarms(
    options: BusinessMetricAlarmOptions = {}
): { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } {
    // Configure namespace
    const namespace = options.namespace || 'BorrowRatePricingEngine';
    
    // Set default borrow rate thresholds (percentage change from previous period)
    const borrowRateThresholds = options.borrowRateThresholds || {
        warning: { threshold: 20, evaluationPeriods: 1 }, // Warning: 20% change
        high: { threshold: 50, evaluationPeriods: 1 },    // High: 50% change
    };
    
    // Set default fee volume thresholds (percentage change from previous period)
    const feeVolumeThresholds = options.feeVolumeThresholds || {
        warning: { threshold: 30, evaluationPeriods: 1 }, // Warning: 30% change
        high: { threshold: 50, evaluationPeriods: 1 },    // High: 50% change
    };
    
    // Set default fee amount thresholds (percentage change from previous period)
    const feeAmountThresholds = options.feeAmountThresholds || {
        warning: { threshold: 25, evaluationPeriods: 1 }, // Warning: 25% change
        high: { threshold: 50, evaluationPeriods: 1 },    // High: 50% change
    };
    
    // Set default fallback usage thresholds (percentage of total calculations)
    const fallbackUsageThresholds = options.fallbackUsageThresholds || {
        warning: { threshold: 5, evaluationPeriods: 1 },  // Warning: >5% using fallback
        high: { threshold: 15, evaluationPeriods: 1 },    // High: >15% using fallback
        critical: { threshold: 30, evaluationPeriods: 1 }, // Critical: >30% using fallback
    };
    
    // Configure notification channels
    const criticalAlarmActions = pagerDutySnsTopicArn ? [pagerDutySnsTopicArn] : [];
    const highAlarmActions = slackSnsTopicArn ? [slackSnsTopicArn] : [];
    const warningAlarmActions = emailSnsTopicArn ? [emailSnsTopicArn] : [];
    
    // Alarms object to hold all created alarms
    const alarms: { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } = {};
    
    // Create borrow rate anomaly alarm
    alarms.borrowRateAnomaly = createCloudWatchAlarm('borrow-rate-anomaly', {
        namespace,
        metricName: 'AvgBorrowRateChange',
        threshold: borrowRateThresholds.warning?.threshold || 20,
        evaluationPeriods: borrowRateThresholds.warning?.evaluationPeriods || 1,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 3600, // 1 hour
        alarmDescription: 'Warning: Unusual change in average borrow rates detected',
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.borrowRateHighAnomaly = createCloudWatchAlarm('borrow-rate-high-anomaly', {
        namespace,
        metricName: 'AvgBorrowRateChange',
        threshold: borrowRateThresholds.high?.threshold || 50,
        evaluationPeriods: borrowRateThresholds.high?.evaluationPeriods || 1,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 3600, // 1 hour
        alarmDescription: 'High: Significant change in average borrow rates detected',
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    // Create fee calculation volume anomaly alarm
    alarms.feeVolumeAnomaly = createCloudWatchAlarm('fee-volume-anomaly', {
        namespace,
        metricName: 'CalculationVolumeChange',
        threshold: feeVolumeThresholds.warning?.threshold || 30,
        evaluationPeriods: feeVolumeThresholds.warning?.evaluationPeriods || 1,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 3600, // 1 hour
        alarmDescription: 'Warning: Unusual change in fee calculation volume detected',
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.feeVolumeHighAnomaly = createCloudWatchAlarm('fee-volume-high-anomaly', {
        namespace,
        metricName: 'CalculationVolumeChange',
        threshold: feeVolumeThresholds.high?.threshold || 50,
        evaluationPeriods: feeVolumeThresholds.high?.evaluationPeriods || 1,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 3600, // 1 hour
        alarmDescription: 'High: Significant change in fee calculation volume detected',
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    // Create fee amount anomaly alarm
    alarms.feeAmountAnomaly = createCloudWatchAlarm('fee-amount-anomaly', {
        namespace,
        metricName: 'AvgFeeAmountChange',
        threshold: feeAmountThresholds.warning?.threshold || 25,
        evaluationPeriods: feeAmountThresholds.warning?.evaluationPeriods || 1,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 3600, // 1 hour
        alarmDescription: 'Warning: Unusual change in average fee amounts detected',
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    // Create fallback mechanism usage alarm
    alarms.fallbackUsage = createCloudWatchAlarm('fallback-usage', {
        namespace,
        metricName: 'FallbackUsagePercent',
        threshold: fallbackUsageThresholds.warning?.threshold || 5,
        evaluationPeriods: fallbackUsageThresholds.warning?.evaluationPeriods || 1,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 300, // 5 minutes
        alarmDescription: 'Warning: Fallback mechanism usage exceeded threshold',
        alarmActions: warningAlarmActions,
        tags: { Severity: 'Warning', ...tags },
    });
    
    alarms.highFallbackUsage = createCloudWatchAlarm('high-fallback-usage', {
        namespace,
        metricName: 'FallbackUsagePercent',
        threshold: fallbackUsageThresholds.high?.threshold || 15,
        evaluationPeriods: fallbackUsageThresholds.high?.evaluationPeriods || 1,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 300, // 5 minutes
        alarmDescription: 'High: Fallback mechanism usage significantly exceeds normal levels',
        alarmActions: highAlarmActions,
        tags: { Severity: 'High', ...tags },
    });
    
    alarms.criticalFallbackUsage = createCloudWatchAlarm('critical-fallback-usage', {
        namespace,
        metricName: 'FallbackUsagePercent',
        threshold: fallbackUsageThresholds.critical?.threshold || 30,
        evaluationPeriods: fallbackUsageThresholds.critical?.evaluationPeriods || 1,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'Average',
        period: 300, // 5 minutes
        alarmDescription: 'Critical: Fallback mechanism usage at critically high level',
        alarmActions: criticalAlarmActions,
        tags: { Severity: 'Critical', ...tags },
    });
    
    return alarms;
}

/**
 * Creates CloudWatch alarms for monitoring SLA compliance across the system
 * 
 * @param options Additional configuration options
 * @returns Object containing all created SLA alarm resources
 */
export function createSlaAlarms(
    options: SlaAlarmOptions = {}
): { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } {
    // Configure namespace
    const namespace = options.namespace || 'BorrowRatePricingEngine';
    
    // Set default SLA thresholds
    const availabilitySlaThreshold = options.availabilitySlaThreshold || 99.95; // 99.95% availability
    const responseTimeSlaThreshold = options.responseTimeSlaThreshold || 100;   // 100ms response time
    const accuracySlaThreshold = options.accuracySlaThreshold || 100;           // 100% calculation accuracy
    
    // Configure notification channels (all SLA breaches should be high priority)
    const slaAlarmActions = pagerDutySnsTopicArn ? [pagerDutySnsTopicArn] : [];
    if (slackSnsTopicArn) {
        slaAlarmActions.push(slackSnsTopicArn);
    }
    
    // Alarms object to hold all created alarms
    const alarms: { [key: string]: aws.cloudwatch.MetricAlarm | aws.cloudwatch.CompositeAlarm } = {};
    
    // Create API availability SLA alarm
    alarms.availabilitySla = createCloudWatchAlarm('api-availability-sla', {
        namespace,
        metricName: 'Availability',
        threshold: availabilitySlaThreshold,
        evaluationPeriods: 3,
        comparisonOperator: 'LessThanThreshold',
        statistic: 'Average',
        period: 300, // 5 minutes
        alarmDescription: `Critical: API availability below SLA target of ${availabilitySlaThreshold}%`,
        alarmActions: slaAlarmActions,
        tags: { Severity: 'Critical', SLA: 'Availability', ...tags },
    });
    
    // Create API response time SLA alarm
    alarms.responseTimeSla = createCloudWatchAlarm('api-response-time-sla', {
        namespace,
        metricName: 'ApiResponseTime',
        threshold: responseTimeSlaThreshold,
        evaluationPeriods: 3,
        comparisonOperator: 'GreaterThanThreshold',
        statistic: 'p95',
        period: 300, // 5 minutes
        alarmDescription: `Critical: API p95 response time exceeds SLA target of ${responseTimeSlaThreshold}ms`,
        alarmActions: slaAlarmActions,
        tags: { Severity: 'Critical', SLA: 'ResponseTime', ...tags },
    });
    
    // Create calculation accuracy SLA alarm
    alarms.accuracySla = createCloudWatchAlarm('calculation-accuracy-sla', {
        namespace,
        metricName: 'CalculationAccuracy',
        threshold: accuracySlaThreshold,
        evaluationPeriods: 1,
        comparisonOperator: 'LessThanThreshold',
        statistic: 'Minimum',
        period: 300, // 5 minutes
        alarmDescription: `Critical: Calculation accuracy below SLA target of ${accuracySlaThreshold}%`,
        alarmActions: slaAlarmActions,
        tags: { Severity: 'Critical', SLA: 'Accuracy', ...tags },
    });
    
    // Create system availability SLA alarm
    alarms.systemAvailabilitySla = createCloudWatchAlarm('system-availability-sla', {
        namespace,
        metricName: 'SystemAvailability',
        threshold: availabilitySlaThreshold,
        evaluationPeriods: 3,
        comparisonOperator: 'LessThanThreshold',
        statistic: 'Average',
        period: 300, // 5 minutes
        alarmDescription: `Critical: System availability below SLA target of ${availabilitySlaThreshold}%`,
        alarmActions: slaAlarmActions,
        tags: { Severity: 'Critical', SLA: 'SystemAvailability', ...tags },
    });
    
    // Create composite SLA alarm to track overall SLA compliance
    const alarmArns = [
        pulumi.interpolate`${alarms.availabilitySla.arn}`,
        pulumi.interpolate`${alarms.responseTimeSla.arn}`,
        pulumi.interpolate`${alarms.accuracySla.arn}`,
        pulumi.interpolate`${alarms.systemAvailabilitySla.arn}`,
    ];
    
    // Build alarm rule expression for composite alarm
    const alarmRuleComponents = alarmArns.map(arn => `ALARM(${arn})`);
    const alarmRule = alarmRuleComponents.join(' OR ');
    
    // Create composite alarm
    alarms.overallSlaCompliance = createCompositeAlarm('sla-compliance', [alarmRule], {
        alarmDescription: 'Critical: SLA breach detected - immediate action required',
        alarmActions: slaAlarmActions,
        tags: { Severity: 'Critical', SLA: 'Overall', ...tags },
    });
    
    return alarms;
}

/**
 * Creates a composite alarm that aggregates the health status of all system components
 * 
 * @param alarmArns Array of alarm ARNs to include in the composite health check
 * @param options Additional configuration options
 * @returns Created composite health alarm resource
 */
export function createCompositeServiceHealthAlarm(
    alarmArns: pulumi.Input<string>[],
    options: AlarmOptions = {}
): aws.cloudwatch.CompositeAlarm {
    // Generate a standardized name for the alarm
    const alarmName = getResourceName('composite-alarm', 'system-health', { includeStackName: true });
    
    // Build alarm rule expression by joining the components with OR
    const alarmRuleComponents = alarmArns.map(arn => `ALARM(${arn})`);
    const alarmRule = alarmRuleComponents.join(' OR ');
    
    // Configure notification channels
    const alarmActions = options.alarmActions || (pagerDutySnsTopicArn ? [pagerDutySnsTopicArn] : []);
    if (slackSnsTopicArn && !alarmActions.includes(slackSnsTopicArn)) {
        alarmActions.push(slackSnsTopicArn);
    }
    
    const okActions = options.okActions || (slackSnsTopicArn ? [slackSnsTopicArn] : []);
    
    // Create the composite alarm
    return new aws.cloudwatch.CompositeAlarm(alarmName, {
        alarmName,
        alarmRule,
        alarmDescription: options.alarmDescription || 'Critical: System-wide health check failure',
        alarmActions,
        okActions,
        insufficientDataActions: options.insufficientDataActions,
        tags: { Severity: 'Critical', ...tags, ...(options.tags || {}) },
    });
}