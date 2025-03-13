/**
 * AWS ElastiCache for Redis infrastructure for the Borrow Rate & Locate Fee Pricing Engine.
 * This module defines and provisions Redis cache clusters with Multi-AZ deployment, automatic
 * failover, and security features to support the application's caching requirements.
 */

import * as aws from '@pulumi/aws'; // @pulumi/aws v5.0.0
import * as pulumi from '@pulumi/pulumi'; // @pulumi/pulumi v3.0.0
import * as random from '@pulumi/random'; // @pulumi/random v4.0.0
import { 
    configureAwsProvider, 
    getResourceName, 
    getDefaultTags, 
    AwsResourceOptions 
} from './aws';
import { 
    createVpc, 
    VpcOutput 
} from './vpc';
import { 
    createCacheSecurityGroup 
} from './security_groups';
import { 
    createRedisDashboard, 
    createRedisAlarms 
} from './cloudwatch';
import { 
    generateRandomPassword 
} from './aws_secret_manager';

// Global configuration and constants
const config = new pulumi.Config();
const stackName = pulumi.getStack();
const redisConfig = new pulumi.Config('redis');

// Default Redis configuration values
const defaultEngine = 'redis';
const defaultEngineVersion = '7.0';
const defaultNodeType = 'cache.m5.large';
const defaultNumShards = 1;
const defaultReplicasPerShard = 1;
const defaultPort = 6379;
const defaultParameterGroupFamily = 'redis7';

// Default tags for Redis resources
const tags = getDefaultTags({ Component: 'Redis' });

/**
 * Interface defining options for Redis cluster creation
 */
export interface RedisOptions {
    /** Name of the Redis cluster */
    name?: string;
    /** Redis engine (default: redis) */
    engine?: string;
    /** Redis engine version (default: 7.0) */
    engineVersion?: string;
    /** Node type for Redis instances (default: cache.m5.large) */
    nodeType?: string;
    /** Number of shards for the cluster (default: 1) */
    numShards?: number;
    /** Number of replicas per shard (default: 1) */
    replicasPerShard?: number;
    /** Enable Multi-AZ deployment (default: true) */
    multiAz?: boolean;
    /** Subnet IDs for Redis deployment */
    subnetIds?: string[];
    /** Security group ID for Redis instances */
    securityGroupId?: string;
    /** Redis port (default: 6379) */
    port?: number;
    /** Enable encryption in transit (default: true) */
    transitEncryptionEnabled?: boolean;
    /** Enable encryption at rest (default: true) */
    atRestEncryptionEnabled?: boolean;
    /** Performance options for Redis */
    performanceOptions?: PerformanceOptions;
    /** Caching behavior options */
    cachingOptions?: CachingOptions;
    /** Additional tags for Redis resources */
    tags?: { [key: string]: string };
}

/**
 * Interface defining performance options for Redis clusters
 */
export interface PerformanceOptions {
    /** Maximum client connections (default: 65000) */
    maxConnections?: number;
    /** Memory management policy (default: volatile-lru) */
    maxmemoryPolicy?: string;
    /** Percentage of memory used for data (default: 75) */
    maxmemoryPercent?: string;
    /** Buffer limit configuration */
    clientOutputBufferLimit?: string;
    /** Background save policy */
    saveToDisk?: {
        frequency: string;
        changes: number;
    }[];
}

/**
 * Interface defining caching behavior options
 */
export interface CachingOptions {
    /** Default TTL for volatile keys in seconds (default: 300) */
    defaultTtl?: number;
    /** Eviction policy for keys (default: volatile-lru) */
    evictionPolicy?: string;
    /** How frequently Redis scans for expired keys (default: 10) */
    keyExpirationScanFrequency?: number;
    /** Whether to use lazy freeing for expired keys (default: true) */
    lazyFreeing?: boolean;
}

/**
 * Interface defining the output of Redis cluster creation
 */
export interface RedisOutput {
    /** The replication group resource */
    replicationGroup: aws.elasticache.ReplicationGroup;
    /** The primary endpoint for Redis operations */
    primaryEndpoint: pulumi.Output<string>;
    /** The reader endpoint for read operations */
    readerEndpoint: pulumi.Output<string>;
    /** The port Redis is listening on */
    port: number;
    /** ARN of the secret containing the auth token */
    authTokenSecretArn?: pulumi.Output<string>;
    /** List of all node endpoints */
    nodeEndpoints?: pulumi.Output<string[]>;
}

/**
 * Creates an ElastiCache Redis cluster with Multi-AZ deployment and automatic failover
 * 
 * @param name Name for the Redis cluster
 * @param options Configuration options for the Redis cluster
 * @returns Redis cluster configuration including endpoint, port, and auth token
 */
export function createRedisCluster(
    name: string,
    options: RedisOptions & AwsResourceOptions = {}
): RedisOutput {
    // Get configuration values with defaults
    const engine = options.engine || redisConfig.get('engine') || defaultEngine;
    const engineVersion = options.engineVersion || redisConfig.get('engineVersion') || defaultEngineVersion;
    const nodeType = options.nodeType || redisConfig.get('nodeType') || defaultNodeType;
    const numShards = options.numShards || redisConfig.getNumber('numShards') || defaultNumShards;
    const replicasPerShard = options.replicasPerShard || redisConfig.getNumber('replicasPerShard') || defaultReplicasPerShard;
    const port = options.port || redisConfig.getNumber('port') || defaultPort;
    const multiAz = options.multiAz !== false;
    const transitEncryptionEnabled = options.transitEncryptionEnabled !== false;
    const atRestEncryptionEnabled = options.atRestEncryptionEnabled !== false;
    const resourceTags = { ...tags, ...(options.tags || {}) };

    // Generate auth token for Redis authentication
    const authToken = generateRandomPassword({
        length: 32,
        includeSpecial: false
    });

    // Create subnet group for Redis using private subnets
    let subnetGroup;
    if (options.subnetIds && options.subnetIds.length > 0) {
        subnetGroup = createSubnetGroup(name, options.subnetIds, {
            tags: resourceTags
        });
    } else if (options.subnetIds === undefined) {
        // Log a warning about missing subnet IDs
        console.warn('No subnet IDs provided for Redis cluster. Please ensure VPC integration is handled separately.');
    }

    // Create parameter group with optimized settings
    const parameterGroupFamily = `${engine}${engineVersion.split('.')[0]}`;
    const parameterGroup = createParameterGroup(name, parameterGroupFamily, {
        performanceOptions: options.performanceOptions,
        cachingOptions: options.cachingOptions,
        tags: resourceTags
    });

    // Create or use security group
    let securityGroupId = options.securityGroupId;
    if (!securityGroupId) {
        // Log a warning about missing security group
        console.warn('No security group ID provided for Redis cluster. Please ensure security group is created separately.');
    }

    // Create the replication group (Redis cluster)
    const redisName = getResourceName('redis', name);
    const replicationGroup = new aws.elasticache.ReplicationGroup(redisName, {
        engine,
        engineVersion,
        nodeType,
        port,
        replicationGroupId: redisName,
        description: `Redis cluster for ${name} in ${stackName} environment`,
        
        // Shard configuration
        numCacheClusters: replicasPerShard > 0 ? replicasPerShard + 1 : 1,
        numNodeGroups: numShards,
        replicasPerNodeGroup: replicasPerShard,
        
        // Networking
        subnetGroupName: subnetGroup ? subnetGroup.name : undefined,
        securityGroupIds: securityGroupId ? [securityGroupId] : undefined,
        
        // Reliability settings
        automaticFailoverEnabled: replicasPerShard > 0 && multiAz,
        multiAzEnabled: multiAz,
        
        // Auth and encryption
        authToken: transitEncryptionEnabled ? authToken : undefined,
        transitEncryptionEnabled,
        atRestEncryptionEnabled,
        
        // Parameter group with optimized settings
        parameterGroupName: parameterGroup.name,
        
        // Maintenance and backup
        maintenanceWindow: 'sun:05:00-sun:07:00',
        snapshotWindow: '03:00-05:00',
        snapshotRetentionLimit: 7,
        
        // Apply standard tags
        tags: {
            ...resourceTags,
            Name: redisName
        }
    });

    // Store auth token in Secrets Manager if transit encryption is enabled
    let authTokenSecret;
    if (transitEncryptionEnabled) {
        authTokenSecret = createRedisSecret(
            name,
            authToken,
            replicationGroup.primaryEndpoint.apply(endpoint => endpoint),
            port,
            { tags: resourceTags }
        );
    }

    // Create CloudWatch dashboard and alarms for Redis monitoring
    const dashboard = createRedisDashboard(name, replicationGroup.id, { tags: resourceTags });
    const alarms = createRedisAlarms(name, replicationGroup.id, { tags: resourceTags });

    // Return Redis cluster configuration
    return {
        replicationGroup,
        primaryEndpoint: replicationGroup.primaryEndpoint,
        readerEndpoint: replicationGroup.readerEndpoint,
        port,
        authTokenSecretArn: authTokenSecret ? authTokenSecret.arn : undefined,
        nodeEndpoints: replicationGroup.cacheNodes?.apply(nodes => 
            nodes ? nodes.map(node => node.address) : []
        )
    };
}

/**
 * Creates a Redis parameter group with optimized settings for the pricing engine
 * 
 * @param name Name for the parameter group
 * @param family Redis family (redis7, redis6, etc.)
 * @param options Additional options for the parameter group
 * @returns Created parameter group resource
 */
export function createParameterGroup(
    name: string,
    family: string,
    options: {
        performanceOptions?: PerformanceOptions;
        cachingOptions?: CachingOptions;
        tags?: { [key: string]: string };
    } = {}
): aws.elasticache.ParameterGroup {
    const pgName = getResourceName('pg', `${name}-${family}`);
    
    // Start with base parameters
    let parameters: { [key: string]: string } = {
        // Recommended production settings
        'timeout': '0',                       // Disable client timeout for financial calculations
        'tcp-keepalive': '300',              // Keep connections alive for reuse
        'databases': '16',                    // Default number of databases
    };
    
    // Apply performance configuration
    if (options.performanceOptions) {
        parameters = {
            ...parameters,
            // Memory management
            'maxmemory-policy': options.performanceOptions.maxmemoryPolicy || 'volatile-lru',
            'maxmemory-percent': options.performanceOptions.maxmemoryPercent || '75',
            
            // Connection limits
            'maxclients': options.performanceOptions.maxConnections?.toString() || '65000',
            
            // Output buffer limits for client connections
            'client-output-buffer-limit-normal': options.performanceOptions.clientOutputBufferLimit || 
                '0 0 0',  // No hard limit for normal clients
            'client-output-buffer-limit-pubsub': '33554432 8388608 60',  // Limits for pub/sub clients
        };
    }
    
    // Apply caching configuration
    if (options.cachingOptions) {
        parameters = {
            ...parameters,
            // TTL settings
            'maxmemory-policy': options.cachingOptions.evictionPolicy || 'volatile-lru',
            'hz': options.cachingOptions.keyExpirationScanFrequency?.toString() || '10',
            'lazyfree-lazy-expire': options.cachingOptions.lazyFreeing ? 'yes' : 'no',
        };
    }
    
    // Create the parameter group
    return new aws.elasticache.ParameterGroup(pgName, {
        family,
        name: pgName,
        description: `Redis parameter group for ${name} in ${stackName} environment`,
        parameters: Object.entries(parameters).map(([name, value]) => ({
            name,
            value
        })),
        tags: {
            ...tags,
            ...(options.tags || {}),
            Name: pgName
        }
    });
}

/**
 * Creates a cache subnet group using private data subnets from the VPC
 * 
 * @param name Name for the subnet group
 * @param subnetIds IDs of subnets to include in the group
 * @param options Additional options for the subnet group
 * @returns Created subnet group resource
 */
export function createSubnetGroup(
    name: string,
    subnetIds: string[],
    options: AwsResourceOptions = {}
): aws.elasticache.SubnetGroup {
    const sgName = getResourceName('subnet-group', name);
    
    return new aws.elasticache.SubnetGroup(sgName, {
        name: sgName,
        description: `Subnet group for ${name} Redis in ${stackName} environment`,
        subnetIds: subnetIds,
        tags: {
            ...tags,
            ...(options.tags || {}),
            Name: sgName
        }
    });
}

/**
 * Configures performance settings for the Redis cluster
 * 
 * @param redisArgs Current Redis parameter arguments
 * @param performanceOptions Performance configuration options
 * @returns Updated Redis arguments with performance configuration
 */
export function configurePerformance(
    redisArgs: { [key: string]: string },
    performanceOptions: PerformanceOptions = {}
): { [key: string]: string } {
    // Deep copy the input arguments
    const args = { ...redisArgs };
    
    // Configure memory settings
    args['maxmemory-policy'] = performanceOptions.maxmemoryPolicy || 'volatile-lru';
    args['maxmemory-percent'] = performanceOptions.maxmemoryPercent || '75';
    
    // Configure connection limits
    args['maxclients'] = performanceOptions.maxConnections?.toString() || '65000';
    
    // Configure client output buffer limits
    // Format: <hard limit> <soft limit> <soft seconds>
    args['client-output-buffer-limit-normal'] = 
        performanceOptions.clientOutputBufferLimit || '0 0 0';
    
    // Configure background save policy if provided
    if (performanceOptions.saveToDisk && performanceOptions.saveToDisk.length > 0) {
        const saveConfig = performanceOptions.saveToDisk
            .map(save => `${save.frequency} ${save.changes}`)
            .join(' ');
        args['save'] = saveConfig;
    } else {
        // Default: disable RDB persistence for a pure cache
        args['save'] = '""';
    }
    
    return args;
}

/**
 * Configures caching behavior for different data types
 * 
 * @param redisArgs Current Redis parameter arguments
 * @param cachingOptions Caching behavior options
 * @returns Updated Redis arguments with caching configuration
 */
export function configureCaching(
    redisArgs: { [key: string]: string },
    cachingOptions: CachingOptions = {}
): { [key: string]: string } {
    // Deep copy the input arguments
    const args = { ...redisArgs };
    
    // Configure TTL settings
    // Note: Redis doesn't have a default TTL parameter, but we can set the eviction policy
    args['maxmemory-policy'] = cachingOptions.evictionPolicy || 'volatile-lru';
    
    // Configure key expiration scan frequency (higher values = more CPU used for expiration)
    args['hz'] = cachingOptions.keyExpirationScanFrequency?.toString() || '10';
    
    // Configure lazy freeing for expired keys (reduces blocking on key deletion)
    args['lazyfree-lazy-expire'] = cachingOptions.lazyFreeing !== false ? 'yes' : 'no';
    
    return args;
}

/**
 * Creates a secret for storing Redis auth token
 * 
 * @param name Name for the secret
 * @param authToken Redis authentication token
 * @param endpoint Redis endpoint
 * @param port Redis port
 * @param options Additional options for the secret
 * @returns Created secret resource with ARN
 */
export function createRedisSecret(
    name: string,
    authToken: pulumi.Output<string>,
    endpoint: pulumi.Output<string>,
    port: number,
    options: AwsResourceOptions = {}
): aws.secretsmanager.Secret {
    const secretName = getResourceName('secret', `redis-${name}`);
    
    // Format the connection information
    const secretValue = pulumi.all([authToken, endpoint]).apply(([token, host]) => {
        return JSON.stringify({
            host,
            port,
            authToken: token,
            ssl: true,
            environment: stackName
        });
    });
    
    // Create the secret
    const secret = new aws.secretsmanager.Secret(secretName, {
        name: secretName,
        description: `Redis auth token for ${name} in ${stackName} environment`,
        tags: {
            ...tags,
            ...(options.tags || {}),
            Name: secretName,
            Service: 'Redis',
            Environment: stackName
        }
    });
    
    // Store the secret value
    const secretVersion = new aws.secretsmanager.SecretVersion(`${secretName}-version`, {
        secretId: secret.id,
        secretString: secretValue
    });
    
    // Set up a rotation reminder (we don't configure automatic rotation for Redis auth tokens)
    const reminderDays = 90; // Remind to rotate every 90 days
    const reminderDate = new Date();
    reminderDate.setDate(reminderDate.getDate() + reminderDays);
    
    // Create a CloudWatch Events rule for the reminder (optional)
    const reminderRule = new aws.cloudwatch.EventRule(`${secretName}-reminder`, {
        description: `Reminder to rotate Redis auth token for ${name}`,
        scheduleExpression: `cron(0 10 ${reminderDate.getDate()} ${reminderDate.getMonth() + 1} ? ${reminderDate.getFullYear()})`,
    });
    
    return secret;
}