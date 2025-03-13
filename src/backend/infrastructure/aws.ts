/**
 * Core AWS provider and utility functions for the Borrow Rate & Locate Fee Pricing Engine infrastructure.
 * This module provides standardized configuration, naming conventions, and resource creation
 * utilities to ensure consistency across all AWS resources.
 */

import * as aws from '@pulumi/aws'; // @pulumi/aws v5.0.0+
import * as pulumi from '@pulumi/pulumi'; // @pulumi/pulumi v3.0.0+

// Global configuration and constants
const config = new pulumi.Config();
const stackName = pulumi.getStack();
const awsConfig = new pulumi.Config('aws');
const defaultRegion = 'us-east-1';
const defaultProfile = 'default';
const defaultTags = { Project: 'BorrowRatePricingEngine', Environment: stackName };

/**
 * Interface defining common options for AWS resource creation.
 */
export interface AwsResourceOptions {
    /** Name of the resource (will be standardized) */
    name?: string;
    /** Tags to apply to the resource */
    tags?: { [key: string]: string };
    /** Region to create the resource in */
    region?: string;
    /** Whether to skip standardized naming */
    skipNaming?: boolean;
    /** Whether to skip default tagging */
    skipTagging?: boolean;
}

/**
 * Interface defining options for AWS provider configuration.
 */
export interface AwsProviderOptions {
    /** AWS region to deploy resources to */
    region?: string;
    /** AWS profile to use for authentication */
    profile?: string;
    /** Default tags to apply to all resources */
    tags?: { [key: string]: string };
    /** Whether to skip applying default tags */
    skipDefaultTags?: boolean;
}

/**
 * Interface defining options for resource naming.
 */
export interface ResourceNamingOptions {
    /** Prefix to add to the resource name */
    prefix?: string;
    /** Suffix to add to the resource name */
    suffix?: string;
    /** Separator character between name parts */
    separator?: string;
    /** Whether to include the stack name in the resource name */
    includeStackName?: boolean;
}

/**
 * Configures the AWS provider with the specified region, profile, and default tags.
 * 
 * @param options Provider configuration options
 * @returns Configured AWS provider instance
 */
export function configureAwsProvider(options: AwsProviderOptions = {}): aws.Provider {
    // Get AWS region from config or use default
    const region = options.region || awsConfig.get('region') || defaultRegion;
    
    // Get AWS profile from config or use default
    const profile = options.profile || awsConfig.get('profile') || defaultProfile;
    
    // Create AWS provider with specified region and profile
    const providerArgs: aws.ProviderArgs = {
        region,
        profile,
    };
    
    // Apply default tags to all resources created with this provider
    if (!options.skipDefaultTags) {
        providerArgs.defaultTags = {
            tags: options.tags || defaultTags,
        };
    }
    
    // Return the configured provider instance
    return new aws.Provider('aws-provider', providerArgs);
}

/**
 * Generates a standardized resource name with prefix, resource type, and optional suffix.
 * 
 * @param resourceType The type of resource (e.g., 'lambda', 'rds')
 * @param resourceName The specific name for this resource
 * @param options Additional naming options
 * @returns Standardized resource name
 */
export function getResourceName(
    resourceType: string,
    resourceName: string,
    options: ResourceNamingOptions = {}
): string {
    // Get project prefix from config or use default
    const prefix = options.prefix || config.get('projectPrefix') || 'brpe';
    
    // Get environment from stack name
    const environment = options.includeStackName !== false ? `-${stackName}` : '';
    
    // Set separator character
    const separator = options.separator || '-';
    
    // Combine prefix, environment, resource type, and resource name
    let name = `${prefix}${separator}${resourceType}${separator}${resourceName}${environment}`;
    
    // Apply optional suffix if provided
    if (options.suffix) {
        name = `${name}${separator}${options.suffix}`;
    }
    
    // Ensure name meets AWS naming requirements (length, characters)
    name = name.toLowerCase().replace(/[^a-z0-9-_]/g, '');
    
    // Handle length limitations for AWS resource names
    const maxLength = 64;
    if (name.length > maxLength) {
        const prefixPart = `${prefix}${separator}${resourceType}${separator}`;
        const suffixPart = options.suffix ? `${separator}${options.suffix}${environment}` : environment;
        const availableLength = maxLength - prefixPart.length - suffixPart.length;
        
        if (availableLength > 0) {
            const truncatedResourceName = resourceName.substring(0, availableLength);
            name = `${prefixPart}${truncatedResourceName}${suffixPart}`;
        } else {
            // If there's not enough space, create a hash of the resource name
            const hash = require('crypto')
                .createHash('md5')
                .update(resourceName)
                .digest('hex')
                .substring(0, 8);
            name = `${prefix}${separator}${resourceType}${separator}${hash}${environment}`;
        }
    }
    
    return name;
}

/**
 * Returns default tags to be applied to all AWS resources.
 * 
 * @param additionalTags Additional tags to merge with defaults
 * @returns Combined default and additional tags
 */
export function getDefaultTags(additionalTags: { [key: string]: string } = {}): { [key: string]: string } {
    // Start with base tags (Project, Environment, ManagedBy)
    const tags: { [key: string]: string } = {
        Project: 'BorrowRatePricingEngine',
        Environment: stackName,
        ManagedBy: 'Pulumi',
    };
    
    // Add stack name as Environment tag
    tags.Environment = stackName;
    
    // Add timestamp for creation date
    if (!tags.CreatedAt) {
        tags.CreatedAt = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format
    }
    
    // Merge with any additional tags provided
    return { ...tags, ...additionalTags };
}

/**
 * Retrieves available AWS availability zones for the current region.
 * 
 * @param count Optional number of AZs to return
 * @returns List of availability zone names
 */
export function getAvailabilityZones(count?: number): pulumi.Output<string[]> {
    // Query AWS for available availability zones in the current region
    const availableAzs = aws.getAvailabilityZones({
        state: 'available', // Filter for 'available' zones only
    });
    
    // Limit to the requested count if specified
    return availableAzs.then(zones => {
        let azNames = zones.names;
        if (count && count > 0 && count < azNames.length) {
            azNames = azNames.slice(0, count);
        }
        return azNames;
    });
}

/**
 * Creates an AWS resource with standardized naming and tagging.
 * 
 * @param resourceType The type of resource being created
 * @param resourceName The specific name for this resource
 * @param resourceCreator Function that creates the actual resource
 * @param options Additional resource options
 * @returns Created AWS resource
 */
export function createAwsResource<T>(
    resourceType: string,
    resourceName: string,
    resourceCreator: (args: any) => T,
    options: AwsResourceOptions = {}
): T {
    // Generate standardized resource name using getResourceName
    const name = options.skipNaming
        ? options.name || resourceName
        : getResourceName(resourceType, resourceName);
    
    // Apply default tags using getDefaultTags
    const tags = options.skipTagging
        ? options.tags || {}
        : getDefaultTags(options.tags);
    
    // Merge options with standardized name and tags
    const mergedOptions = {
        ...options,
        name,
        tags,
    };
    
    // Call the provided resource creator function with merged options
    return resourceCreator(mergedOptions);
}

/**
 * Creates a KMS key with standardized configuration and permissions.
 * 
 * @param name Name for the KMS key
 * @param options Additional KMS key options
 * @returns Created KMS key resource
 */
export function createKmsKey(
    name: string,
    options: aws.kms.KeyArgs = {}
): aws.kms.Key {
    // Generate standardized resource name using getResourceName
    const keyName = getResourceName('kms', name);
    
    // Create KMS key with appropriate description
    const description = options.description || `KMS key for ${name} in ${stackName} environment`;
    
    // Configure key rotation (enabled by default, yearly)
    const enableKeyRotation = options.enableKeyRotation !== false;
    
    // Set up key policy for proper access control
    const policy = options.policy || createDefaultKmsPolicy();
    
    // Apply standard tags to the key
    const tags = getDefaultTags(options.tags);
    
    // Return the created KMS key
    return new aws.kms.Key(keyName, {
        description,
        enableKeyRotation,
        policy,
        deletionWindowInDays: options.deletionWindowInDays || 30,
        tags,
        ...options,
    });
}

/**
 * Creates a default KMS key policy that allows the account to administer the key.
 * This is a helper function used by createKmsKey.
 * 
 * @returns KMS key policy as a JSON string
 */
function createDefaultKmsPolicy(): pulumi.Output<string> {
    return getAccountId().apply(accountId => {
        const policy = {
            Version: '2012-10-17',
            Statement: [
                {
                    Sid: 'Enable IAM User Permissions',
                    Effect: 'Allow',
                    Principal: {
                        AWS: `arn:aws:iam::${accountId}:root`,
                    },
                    Action: 'kms:*',
                    Resource: '*',
                },
            ],
        };
        return JSON.stringify(policy);
    });
}

/**
 * Gets the current AWS region being used.
 * 
 * @returns AWS region name
 */
export function getRegion(): string {
    // Get region from AWS config if available
    const region = awsConfig.get('region');
    
    // Fall back to default region if not specified
    return region || defaultRegion;
}

/**
 * Gets the current AWS account ID.
 * 
 * @returns AWS account ID
 */
export function getAccountId(): pulumi.Output<string> {
    // Use AWS provider to get current caller identity
    const callerIdentity = aws.getCallerIdentity({});
    
    // Extract account ID from caller identity
    return callerIdentity.then(identity => identity.accountId);
}