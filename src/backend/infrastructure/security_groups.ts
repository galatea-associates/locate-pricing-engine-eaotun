/**
 * AWS Security Groups for the Borrow Rate & Locate Fee Pricing Engine infrastructure.
 * 
 * This module defines and provisions security groups with appropriate ingress and egress
 * rules for different infrastructure components, implementing the principle of least privilege.
 */

import * as aws from '@pulumi/aws'; // @pulumi/aws v5.0.0
import * as pulumi from '@pulumi/pulumi'; // @pulumi/pulumi v3.0.0
import { 
    configureAwsProvider, 
    getResourceName, 
    getDefaultTags, 
    AwsResourceOptions 
} from './aws';

// Global configuration and constants
const config = new pulumi.Config();
const stackName = pulumi.getStack();
const sgConfig = new pulumi.Config('securityGroups');
const tags = getDefaultTags({ Component: 'SecurityGroups' });

/**
 * Interface defining a security group rule.
 */
export interface SecurityGroupRule {
    /** Protocol (tcp, udp, icmp, or all) */
    protocol: string;
    /** Starting port range */
    fromPort: number;
    /** Ending port range */
    toPort: number;
    /** CIDR blocks to allow access from/to */
    cidrBlocks?: string[];
    /** Security group IDs to allow access from/to */
    securityGroupIds?: string[];
    /** Description of the rule */
    description: string;
}

/**
 * Interface defining options for security group creation.
 */
export interface SecurityGroupOptions {
    /** Name of the security group */
    name?: string;
    /** Description of the security group */
    description?: string;
    /** Ingress rules to apply */
    ingressRules?: SecurityGroupRule[];
    /** Egress rules to apply */
    egressRules?: SecurityGroupRule[];
    /** Tags to apply to the security group */
    tags?: { [key: string]: string };
}

/**
 * Interface defining the output of security group creation.
 */
export interface SecurityGroupsOutput {
    /** ID of the API Gateway security group */
    apiGatewaySgId: string;
    /** ID of the EKS cluster security group */
    eksClusterSgId: string;
    /** ID of the EKS node security group */
    eksNodeSgId: string;
    /** ID of the database security group */
    databaseSgId: string;
    /** ID of the cache security group */
    cacheSgId: string;
    /** ID of the bastion security group (optional) */
    bastionSgId?: string;
}

/**
 * Creates all required security groups for the infrastructure.
 * 
 * @param vpcId The VPC ID where security groups will be created
 * @param options Additional options for security group creation
 * @returns Object containing all created security group resources
 */
export function createSecurityGroups(
    vpcId: string,
    options: AwsResourceOptions = {}
): SecurityGroupsOutput {
    // Create API Gateway security group
    const apiGatewaySg = createApiGatewaySecurityGroup(vpcId, options);
    
    // Create EKS cluster security group
    const eksClusterSg = createEksSecurityGroup(vpcId, options);
    
    // Create EKS node security group (depends on cluster SG)
    const eksNodeSg = createEksNodeSecurityGroup(vpcId, eksClusterSg.id, options);
    
    // Create database security group (depends on node SG)
    const databaseSg = createDatabaseSecurityGroup(vpcId, eksNodeSg.id, options);
    
    // Create cache security group (depends on node SG)
    const cacheSg = createCacheSecurityGroup(vpcId, eksNodeSg.id, options);
    
    // Create bastion security group if enabled
    let bastionSg: aws.ec2.SecurityGroup | undefined;
    const allowedIpRanges = sgConfig.getObject<string[]>('bastionAllowedIps');
    if (allowedIpRanges && allowedIpRanges.length > 0) {
        bastionSg = createBastionSecurityGroup(vpcId, allowedIpRanges, options);
    }

    // Configure rules between security groups
    configureSecurityGroupRules({
        apiGatewaySg,
        eksClusterSg,
        eksNodeSg,
        databaseSg,
        cacheSg,
        bastionSg
    });

    // Return security group IDs
    return {
        apiGatewaySgId: apiGatewaySg.id,
        eksClusterSgId: eksClusterSg.id,
        eksNodeSgId: eksNodeSg.id,
        databaseSgId: databaseSg.id,
        cacheSgId: cacheSg.id,
        ...(bastionSg && { bastionSgId: bastionSg.id })
    };
}

/**
 * Creates a security group for the API Gateway.
 * 
 * @param vpcId The VPC ID where the security group will be created
 * @param options Additional options for security group creation
 * @returns Created security group resource
 */
export function createApiGatewaySecurityGroup(
    vpcId: string,
    options: AwsResourceOptions = {}
): aws.ec2.SecurityGroup {
    const name = getResourceName('sg', 'api-gateway');
    
    return new aws.ec2.SecurityGroup(name, {
        vpcId: vpcId,
        description: "Security group for API Gateway",
        ingress: [
            // Allow HTTPS from anywhere
            {
                protocol: 'tcp',
                fromPort: 443,
                toPort: 443,
                cidrBlocks: ['0.0.0.0/0'],
                description: "HTTPS inbound from internet"
            },
            // Allow HTTP from anywhere (for HTTP->HTTPS redirect)
            {
                protocol: 'tcp',
                fromPort: 80,
                toPort: 80,
                cidrBlocks: ['0.0.0.0/0'],
                description: "HTTP inbound from internet (for redirect)"
            }
        ],
        egress: [
            // Allow all outbound traffic
            {
                protocol: '-1',
                fromPort: 0,
                toPort: 0,
                cidrBlocks: ['0.0.0.0/0'],
                description: "All outbound traffic"
            }
        ],
        tags: {
            ...tags,
            Name: name,
            Component: 'APIGateway'
        }
    });
}

/**
 * Creates a security group for the EKS cluster control plane.
 * 
 * @param vpcId The VPC ID where the security group will be created
 * @param options Additional options for security group creation
 * @returns Created security group resource
 */
export function createEksSecurityGroup(
    vpcId: string,
    options: AwsResourceOptions = {}
): aws.ec2.SecurityGroup {
    const name = getResourceName('sg', 'eks-cluster');
    
    return new aws.ec2.SecurityGroup(name, {
        vpcId: vpcId,
        description: "Security group for EKS cluster control plane",
        // We'll add ingress rules in configureSecurityGroupRules to avoid circular dependencies
        egress: [
            // Allow all outbound traffic
            {
                protocol: '-1',
                fromPort: 0,
                toPort: 0,
                cidrBlocks: ['0.0.0.0/0'],
                description: "All outbound traffic"
            }
        ],
        tags: {
            ...tags,
            Name: name,
            Component: 'EKSCluster',
            "kubernetes.io/cluster/${eksClusterName}": "owned" // Tag format for EKS integration
        }
    }, {
        replaceOnChanges: ["ingress", "egress"], // Ensure security group rules are properly updated
    });
}

/**
 * Creates a security group for the EKS worker nodes.
 * 
 * @param vpcId The VPC ID where the security group will be created
 * @param eksClusterSgId The ID of the EKS cluster security group
 * @param options Additional options for security group creation
 * @returns Created security group resource
 */
export function createEksNodeSecurityGroup(
    vpcId: string,
    eksClusterSgId: string,
    options: AwsResourceOptions = {}
): aws.ec2.SecurityGroup {
    const name = getResourceName('sg', 'eks-node');
    
    return new aws.ec2.SecurityGroup(name, {
        vpcId: vpcId,
        description: "Security group for EKS worker nodes",
        // Initial ingress rules - we'll add more in configureSecurityGroupRules
        ingress: [
            // Allow all traffic from nodes within the same security group
            {
                protocol: '-1',
                fromPort: 0,
                toPort: 0,
                self: true,
                description: "Allow all traffic between worker nodes"
            }
        ],
        egress: [
            // Allow all outbound traffic
            {
                protocol: '-1',
                fromPort: 0,
                toPort: 0,
                cidrBlocks: ['0.0.0.0/0'],
                description: "All outbound traffic"
            }
        ],
        tags: {
            ...tags,
            Name: name,
            Component: 'EKSNode',
            "kubernetes.io/cluster/${eksClusterName}": "owned" // Tag format for EKS integration
        }
    }, {
        replaceOnChanges: ["ingress", "egress"], // Ensure security group rules are properly updated
    });
}

/**
 * Creates a security group for RDS database instances.
 * 
 * @param vpcId The VPC ID where the security group will be created
 * @param eksNodeSgId The ID of the EKS node security group
 * @param options Additional options for security group creation
 * @returns Created security group resource
 */
export function createDatabaseSecurityGroup(
    vpcId: string,
    eksNodeSgId: string,
    options: AwsResourceOptions = {}
): aws.ec2.SecurityGroup {
    const name = getResourceName('sg', 'database');
    
    return new aws.ec2.SecurityGroup(name, {
        vpcId: vpcId,
        description: "Security group for RDS database instances",
        ingress: [
            // Allow PostgreSQL from EKS nodes
            {
                protocol: 'tcp',
                fromPort: 5432,
                toPort: 5432,
                securityGroups: [eksNodeSgId],
                description: "PostgreSQL from EKS nodes"
            }
        ],
        egress: [
            // Allow all outbound traffic within VPC only
            {
                protocol: '-1',
                fromPort: 0,
                toPort: 0,
                cidrBlocks: [sgConfig.get('vpcCidr') || '10.0.0.0/16'],
                description: "All outbound traffic within VPC"
            }
        ],
        tags: {
            ...tags,
            Name: name,
            Component: 'Database'
        }
    });
}

/**
 * Creates a security group for Redis cache instances.
 * 
 * @param vpcId The VPC ID where the security group will be created
 * @param eksNodeSgId The ID of the EKS node security group
 * @param options Additional options for security group creation
 * @returns Created security group resource
 */
export function createCacheSecurityGroup(
    vpcId: string,
    eksNodeSgId: string,
    options: AwsResourceOptions = {}
): aws.ec2.SecurityGroup {
    const name = getResourceName('sg', 'cache');
    
    return new aws.ec2.SecurityGroup(name, {
        vpcId: vpcId,
        description: "Security group for Redis cache instances",
        ingress: [
            // Allow Redis from EKS nodes
            {
                protocol: 'tcp',
                fromPort: 6379,
                toPort: 6379,
                securityGroups: [eksNodeSgId],
                description: "Redis from EKS nodes"
            }
        ],
        egress: [
            // Allow all outbound traffic within VPC only
            {
                protocol: '-1',
                fromPort: 0,
                toPort: 0,
                cidrBlocks: [sgConfig.get('vpcCidr') || '10.0.0.0/16'],
                description: "All outbound traffic within VPC"
            }
        ],
        tags: {
            ...tags,
            Name: name,
            Component: 'Cache'
        }
    });
}

/**
 * Creates a security group for bastion host.
 * 
 * @param vpcId The VPC ID where the security group will be created
 * @param allowedIpRanges List of CIDR blocks allowed to access the bastion
 * @param options Additional options for security group creation
 * @returns Created security group resource
 */
export function createBastionSecurityGroup(
    vpcId: string,
    allowedIpRanges: string[],
    options: AwsResourceOptions = {}
): aws.ec2.SecurityGroup {
    const name = getResourceName('sg', 'bastion');
    
    return new aws.ec2.SecurityGroup(name, {
        vpcId: vpcId,
        description: "Security group for bastion host",
        ingress: [
            // Allow SSH from specified IP ranges only
            {
                protocol: 'tcp',
                fromPort: 22,
                toPort: 22,
                cidrBlocks: allowedIpRanges,
                description: "SSH from allowed IP ranges"
            }
        ],
        egress: [
            // Allow all outbound traffic
            {
                protocol: '-1',
                fromPort: 0,
                toPort: 0,
                cidrBlocks: ['0.0.0.0/0'],
                description: "All outbound traffic"
            }
        ],
        tags: {
            ...tags,
            Name: name,
            Component: 'Bastion'
        }
    });
}

/**
 * Configures security group rules for proper communication between components.
 * This function adds rules that require references to already-created security groups.
 * 
 * @param securityGroups Object containing all security group resources
 * @returns Object containing all created security group rule resources
 */
export function configureSecurityGroupRules(
    securityGroups: {
        apiGatewaySg: aws.ec2.SecurityGroup;
        eksClusterSg: aws.ec2.SecurityGroup;
        eksNodeSg: aws.ec2.SecurityGroup;
        databaseSg: aws.ec2.SecurityGroup;
        cacheSg: aws.ec2.SecurityGroup;
        bastionSg?: aws.ec2.SecurityGroup;
    }
): Record<string, aws.ec2.SecurityGroupRule> {
    const rules: Record<string, aws.ec2.SecurityGroupRule> = {};

    // API Gateway to EKS cluster (HTTPS)
    rules.apiToEksHttps = new aws.ec2.SecurityGroupRule('api-to-eks-https', {
        type: 'ingress',
        fromPort: 443,
        toPort: 443,
        protocol: 'tcp',
        securityGroupId: securityGroups.eksClusterSg.id,
        sourceSecurityGroupId: securityGroups.apiGatewaySg.id,
        description: 'HTTPS from API Gateway to EKS Cluster',
    });

    // EKS cluster to EKS nodes (all traffic)
    rules.eksClusterToNodes = new aws.ec2.SecurityGroupRule('eks-cluster-to-nodes', {
        type: 'ingress',
        fromPort: 0,
        toPort: 0,
        protocol: '-1',
        securityGroupId: securityGroups.eksNodeSg.id,
        sourceSecurityGroupId: securityGroups.eksClusterSg.id,
        description: 'All traffic from EKS Cluster to Nodes',
    });

    // EKS nodes to EKS cluster (all traffic)
    rules.eksNodesToCluster = new aws.ec2.SecurityGroupRule('eks-nodes-to-cluster', {
        type: 'ingress',
        fromPort: 0,
        toPort: 0,
        protocol: '-1',
        securityGroupId: securityGroups.eksClusterSg.id,
        sourceSecurityGroupId: securityGroups.eksNodeSg.id,
        description: 'All traffic from EKS Nodes to Cluster',
    });

    // If bastion host is enabled, add rules for database access
    if (securityGroups.bastionSg) {
        // Bastion to database (PostgreSQL)
        rules.bastionToDatabase = new aws.ec2.SecurityGroupRule('bastion-to-database', {
            type: 'ingress',
            fromPort: 5432,
            toPort: 5432,
            protocol: 'tcp',
            securityGroupId: securityGroups.databaseSg.id,
            sourceSecurityGroupId: securityGroups.bastionSg.id,
            description: 'PostgreSQL from Bastion to Database',
        });

        // Bastion to Redis (for troubleshooting)
        rules.bastionToCache = new aws.ec2.SecurityGroupRule('bastion-to-cache', {
            type: 'ingress',
            fromPort: 6379,
            toPort: 6379,
            protocol: 'tcp',
            securityGroupId: securityGroups.cacheSg.id,
            sourceSecurityGroupId: securityGroups.bastionSg.id,
            description: 'Redis from Bastion to Cache',
        });
    }

    return rules;
}