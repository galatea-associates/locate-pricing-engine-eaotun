/**
 * AWS RDS (Relational Database Service) infrastructure for the Borrow Rate & Locate Fee Pricing Engine.
 * 
 * This module defines and provisions PostgreSQL database instances with Multi-AZ deployment,
 * automated backups, and security features to support the application's data persistence requirements.
 * The implementation follows financial industry best practices for security, compliance, and performance.
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
    createDatabaseSecurityGroup 
} from './security_groups';
import { 
    createDatabaseSecret, 
    generateRandomPassword, 
    DatabaseCredentials 
} from './aws_secret_manager';

// Global configuration
const config = new pulumi.Config();
const stackName = pulumi.getStack();
const dbConfig = new pulumi.Config('database');

// Default values for PostgreSQL RDS
const defaultEngine = 'postgres';
const defaultEngineVersion = '15.0';
const defaultInstanceClass = 'db.m5.large';
const defaultAllocatedStorage = 100; // GB
const defaultPort = 5432;
const defaultParameterGroupFamily = 'postgres15';
const defaultUsername = 'dbadmin';

// Default tags for database resources
const tags = getDefaultTags({ Component: 'Database' });

/**
 * Interface defining options for RDS instance creation
 */
export interface RdsOptions {
    /** Name of the database instance */
    name: string;
    /** Database engine (default: postgres) */
    engine?: string;
    /** Engine version (default: 15.0) */
    engineVersion?: string;
    /** RDS instance class (default: db.m5.large) */
    instanceClass?: string;
    /** Allocated storage in GB (default: 100) */
    allocatedStorage?: number;
    /** Enable Multi-AZ deployment (default: true) */
    multiAz?: boolean;
    /** Subnet IDs for the DB subnet group */
    subnetIds?: string[];
    /** Security group ID for the database */
    securityGroupId?: string;
    /** Admin username (default: dbadmin) */
    username?: string;
    /** Database port (default: 5432) */
    port?: number;
    /** Name of the initial database to create */
    dbName?: string;
    /** Enable storage encryption (default: true) */
    storageEncrypted?: boolean;
    /** KMS key ID for encryption */
    kmsKeyId?: string;
    /** Deletion protection (default: true) */
    deletionProtection?: boolean;
    /** Additional tags */
    tags?: { [key: string]: string };
}

/**
 * Interface defining backup options for RDS instances
 */
export interface BackupOptions {
    /** Backup retention period in days (default: 7) */
    retentionPeriod?: number;
    /** Preferred backup window (UTC) */
    backupWindow?: string;
    /** Enable copy of snapshots to secondary region */
    enableCrossRegionCopy?: boolean;
    /** Destination region for cross-region copies */
    destinationRegion?: string;
    /** Automated backup replication */
    replicationEnabled?: boolean;
}

/**
 * Interface defining performance options for RDS instances
 */
export interface PerformanceOptions {
    /** Maximum connections (default: calculated based on instance class) */
    maxConnections?: number;
    /** Shared buffers setting */
    sharedBuffers?: string;
    /** Work memory setting */
    workMem?: string;
    /** Maintenance work memory setting */
    maintenanceWorkMem?: string;
    /** Effective cache size setting */
    effectiveCacheSize?: string;
    /** Enable Performance Insights (default: true) */
    enablePerformanceInsights?: boolean;
    /** Performance Insights retention period in days */
    performanceInsightsRetentionPeriod?: number;
}

/**
 * Interface defining the output of RDS instance creation
 */
export interface RdsOutput {
    /** The RDS instance resource */
    instance: aws.rds.Instance;
    /** Database endpoint (hostname) */
    endpoint: string;
    /** Database port */
    port: number;
    /** Database name */
    dbName: string;
    /** Admin username */
    username: string;
    /** ARN of the secret containing credentials */
    credentialsSecretArn: string;
    /** Endpoints of read replicas (if any) */
    readReplicaEndpoints?: string[];
}

/**
 * Creates an RDS PostgreSQL instance with Multi-AZ deployment and automated backups
 * 
 * @param name Name for the RDS instance
 * @param options Options for RDS instance creation
 * @returns RDS instance configuration including endpoint, port, and credentials
 */
export function createRdsInstance(
    name: string,
    options: RdsOptions
): pulumi.Output<RdsOutput> {
    // Get configuration values with defaults
    const engine = options.engine || dbConfig.get('engine') || defaultEngine;
    const engineVersion = options.engineVersion || dbConfig.get('engineVersion') || defaultEngineVersion;
    const instanceClass = options.instanceClass || dbConfig.get('instanceClass') || defaultInstanceClass;
    const allocatedStorage = options.allocatedStorage || dbConfig.getNumber('allocatedStorage') || defaultAllocatedStorage;
    const multiAz = options.multiAz !== false;
    const port = options.port || dbConfig.getNumber('port') || defaultPort;
    const username = options.username || dbConfig.get('username') || defaultUsername;
    const dbName = options.dbName || dbConfig.get('dbName') || name.replace(/[^a-zA-Z0-9]/g, '');
    const storageEncrypted = options.storageEncrypted !== false;
    const deletionProtection = options.deletionProtection !== false;
    
    // Generate a secure random password for the database admin user
    const passwordOutput = generateRandomPassword({
        length: 32,
        includeSpecial: true,
        includeNumbers: true,
    });
    
    return pulumi.all([passwordOutput]).apply(([password]) => {
        // Create a DB subnet group using private data subnets
        const subnetGroup = createDbSubnetGroup(
            name,
            options.subnetIds || [],
            { tags: options.tags }
        );
        
        // Create a parameter group with optimized PostgreSQL settings
        const parameterGroupFamily = defaultParameterGroupFamily;
        const parameterGroup = createParameterGroup(
            name,
            parameterGroupFamily,
            { tags: options.tags }
        );
        
        // Create or use the provided security group
        let securityGroupId = options.securityGroupId;
        
        // Create the RDS instance
        const rdsName = getResourceName('rds', name);
        
        // Prepare RDS instance arguments
        const rdsArgs: aws.rds.InstanceArgs = {
            identifier: rdsName,
            engine: engine,
            engineVersion: engineVersion,
            instanceClass: instanceClass,
            allocatedStorage: allocatedStorage,
            username: username,
            password: password,
            dbName: dbName,
            port: port,
            multiAz: multiAz,
            dbSubnetGroupName: subnetGroup.name,
            parameterGroupName: parameterGroup.name,
            vpcSecurityGroupIds: securityGroupId ? [securityGroupId] : undefined,
            
            // Storage configuration
            storageType: "gp3",
            storageEncrypted: storageEncrypted,
            kmsKeyId: options.kmsKeyId,
            iops: 12000, // Optimized for financial workloads
            
            // Maintenance and updates
            autoMinorVersionUpgrade: true,
            allowMajorVersionUpgrade: false,
            maintenanceWindow: "sun:03:00-sun:05:00", // Sunday morning maintenance window
            deletionProtection: deletionProtection,
            skipFinalSnapshot: stackName.includes('dev') || stackName.includes('test'),
            finalSnapshotIdentifier: stackName.includes('dev') || stackName.includes('test') ? 
                undefined : `${rdsName}-final-${new Date().getTime()}`,
            
            // Monitoring and insights
            monitoringInterval: 60, // Enhanced monitoring every 60 seconds
            monitoringRoleArn: createMonitoringRole(name).arn,
            enabledCloudwatchLogsExports: ["postgresql", "upgrade"],
            performanceInsightsEnabled: true,
            performanceInsightsRetentionPeriod: 7, // 7 days retention
            
            // Network
            publiclyAccessible: false,
            
            // Tags
            tags: {
                ...tags,
                ...options.tags,
                Name: rdsName,
            },
        };
        
        // Configure backup settings
        const backupOptions: BackupOptions = {
            retentionPeriod: 7, // 7 days retention by default
            backupWindow: "01:00-03:00", // 1-3 AM UTC backup window
        };
        const rdsArgsWithBackup = configureBackup(rdsArgs, backupOptions);
        
        // Configure performance settings
        const performanceOptions: PerformanceOptions = {
            enablePerformanceInsights: true,
        };
        const finalRdsArgs = configurePerformance(rdsArgsWithBackup, performanceOptions);
        
        // Create the RDS instance
        const rdsInstance = new aws.rds.Instance(rdsName, finalRdsArgs);
        
        // Store database credentials in AWS Secrets Manager
        const credentials: DatabaseCredentials = {
            username: username,
            password: password,
            engine: engine,
            host: rdsInstance.endpoint,
            port: port,
            dbname: dbName,
            dbInstanceIdentifier: rdsInstance.id,
        };
        
        const secret = createDatabaseSecret(name, credentials, {
            description: `Credentials for ${name} RDS instance`,
            enableRotation: true,
            rotationDays: 90,
            tags: options.tags,
        });
        
        // Return the RDS instance configuration
        return {
            instance: rdsInstance,
            endpoint: rdsInstance.endpoint,
            port: port,
            dbName: dbName,
            username: username,
            credentialsSecretArn: secret.arn,
        };
    });
}

/**
 * Creates a monitoring role for enhanced RDS monitoring
 * 
 * @param name Name for the monitoring role
 * @returns Created IAM role resource
 */
function createMonitoringRole(name: string): aws.iam.Role {
    const roleName = getResourceName('role', `${name}-monitoring`);
    
    return new aws.iam.Role(roleName, {
        assumeRolePolicy: JSON.stringify({
            Version: "2012-10-17",
            Statement: [{
                Action: "sts:AssumeRole",
                Effect: "Allow",
                Principal: {
                    Service: "monitoring.rds.amazonaws.com"
                }
            }]
        }),
        managedPolicyArns: [
            "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
        ],
        tags: tags,
    });
}

/**
 * Creates a DB parameter group with optimized settings for the pricing engine
 * 
 * @param name Name for the parameter group
 * @param family Parameter group family (e.g., postgres15)
 * @param options Additional options for parameter group creation
 * @returns Created parameter group resource
 */
export function createParameterGroup(
    name: string,
    family: string,
    options: AwsResourceOptions = {}
): aws.rds.ParameterGroup {
    const pgName = getResourceName('pg', name);
    
    return new aws.rds.ParameterGroup(pgName, {
        family: family,
        description: `Optimized parameter group for ${name} database`,
        parameters: [
            // Connection parameters
            { name: "max_connections", value: "200" },
            
            // Memory parameters
            { name: "shared_buffers", value: "8GB" },
            { name: "work_mem", value: "64MB" },
            { name: "maintenance_work_mem", value: "512MB" },
            { name: "effective_cache_size", value: "24GB" },
            
            // Write-ahead logging
            { name: "wal_buffers", value: "16MB" },
            { name: "checkpoint_timeout", value: "15" },
            { name: "synchronous_commit", value: "on" }, // Ensure financial data is committed
            
            // Query planning
            { name: "random_page_cost", value: "1.1" }, // Assuming SSD storage
            { name: "effective_io_concurrency", value: "200" },
            { name: "default_statistics_target", value: "100" },
            
            // Autovacuum
            { name: "autovacuum", value: "on" },
            { name: "autovacuum_max_workers", value: "3" },
            { name: "autovacuum_naptime", value: "60" },
            { name: "autovacuum_vacuum_scale_factor", value: "0.1" },
            { name: "autovacuum_analyze_scale_factor", value: "0.05" },
            
            // Logging for financial compliance
            { name: "log_statement", value: "mod" }, // Log all DDL and modification statements
            { name: "log_min_duration_statement", value: "1000" }, // Log slow queries (>1s)
            { name: "log_connections", value: "on" },
            { name: "log_disconnections", value: "on" },
            { name: "log_lock_waits", value: "on" },
            { name: "log_temp_files", value: "0" },
            
            // Performance tuning
            { name: "track_activities", value: "on" },
            { name: "track_counts", value: "on" },
            { name: "track_io_timing", value: "on" },
            { name: "track_functions", value: "pl" }, // Track procedural language functions
        ],
        tags: {
            ...tags,
            ...options.tags,
            Name: pgName,
        },
    });
}

/**
 * Creates a DB subnet group using private data subnets from the VPC
 * 
 * @param name Name for the subnet group
 * @param subnetIds IDs of subnets to include in the group
 * @param options Additional options for subnet group creation
 * @returns Created DB subnet group resource
 */
export function createDbSubnetGroup(
    name: string,
    subnetIds: string[],
    options: AwsResourceOptions = {}
): aws.rds.SubnetGroup {
    const sgName = getResourceName('dbsg', name);
    
    return new aws.rds.SubnetGroup(sgName, {
        name: sgName,
        subnetIds: subnetIds,
        description: `Subnet group for ${name} database in private data subnets`,
        tags: {
            ...tags,
            ...options.tags,
            Name: sgName,
        },
    });
}

/**
 * Configures automated backup strategy for the RDS instance
 * 
 * @param rdsArgs Base RDS instance arguments
 * @param backupOptions Backup configuration options
 * @returns Updated RDS arguments with backup configuration
 */
export function configureBackup(
    rdsArgs: aws.rds.InstanceArgs,
    backupOptions: BackupOptions = {}
): aws.rds.InstanceArgs {
    // Set backup configuration
    const updatedArgs = {
        ...rdsArgs,
        backupRetentionPeriod: backupOptions.retentionPeriod || 7,
        backupWindow: backupOptions.backupWindow || "01:00-03:00", // 1-3 AM UTC
        copyTagsToSnapshot: true,
    };
    
    // Enable cross-region snapshot copy if requested
    if (backupOptions.enableCrossRegionCopy && backupOptions.destinationRegion) {
        updatedArgs.replicateSourceDb = undefined; // Ensure this is not set for primary instances
    }
    
    return updatedArgs;
}

/**
 * Configures performance settings for the RDS instance
 * 
 * @param rdsArgs Base RDS instance arguments
 * @param performanceOptions Performance configuration options
 * @returns Updated RDS arguments with performance configuration
 */
export function configurePerformance(
    rdsArgs: aws.rds.InstanceArgs,
    performanceOptions: PerformanceOptions = {}
): aws.rds.InstanceArgs {
    // Set performance configuration
    const updatedArgs = {
        ...rdsArgs,
        performanceInsightsEnabled: performanceOptions.enablePerformanceInsights !== false,
        performanceInsightsRetentionPeriod: performanceOptions.performanceInsightsRetentionPeriod || 7,
    };
    
    return updatedArgs;
}

/**
 * Creates a read replica of the primary RDS instance for read scaling
 * 
 * @param name Name for the read replica
 * @param sourceDbIdentifier Identifier of the source RDS instance
 * @param options Additional options for read replica creation
 * @returns Created read replica resource
 */
export function createReadReplica(
    name: string,
    sourceDbIdentifier: string,
    options: AwsResourceOptions & {
        instanceClass?: string;
        availabilityZone?: string;
        port?: number;
        multiAz?: boolean;
    } = {}
): aws.rds.Instance {
    const replicaName = getResourceName('replica', name);
    
    return new aws.rds.Instance(replicaName, {
        identifier: replicaName,
        replicateSourceDb: sourceDbIdentifier,
        instanceClass: options.instanceClass || 'db.m5.large',
        port: options.port || defaultPort,
        multiAz: options.multiAz || false, // Read replicas are typically single-AZ
        availabilityZone: options.availabilityZone,
        
        // Performance settings
        performanceInsightsEnabled: true,
        performanceInsightsRetentionPeriod: 7,
        monitoringInterval: 60,
        monitoringRoleArn: createMonitoringRole(`${name}-replica`).arn,
        
        // Network settings
        publiclyAccessible: false,
        
        // Backup settings for the replica
        backupRetentionPeriod: 1, // Minimal backup retention for replicas
        backupWindow: "03:00-05:00", // Different window than primary
        
        // Storage settings
        storageEncrypted: true, // Inherit from source, but explicitly set
        
        // Tags
        tags: {
            ...tags,
            ...options.tags,
            Name: replicaName,
            ReplicaOf: sourceDbIdentifier,
        },
    });
}