/**
 * AWS VPC Infrastructure for the Borrow Rate & Locate Fee Pricing Engine.
 * This module defines and provisions a secure, multi-AZ network architecture with
 * public and private subnets, NAT gateways, and network ACLs to support the application's
 * security and availability requirements.
 */

import * as aws from '@pulumi/aws'; // @pulumi/aws v5.0.0+
import * as pulumi from '@pulumi/pulumi'; // @pulumi/pulumi v3.0.0+
import { 
    configureAwsProvider, 
    getAvailabilityZones, 
    getDefaultTags,
    getResourceName,
    AwsResourceOptions
} from './aws';

// Global configuration
const config = new pulumi.Config();
const stackName = pulumi.getStack();
const vpcConfig = new pulumi.Config('vpc');

// Default CIDR blocks
const defaultCidr = '10.0.0.0/16';
const defaultPublicSubnetCidrs = ['10.0.0.0/24', '10.0.1.0/24', '10.0.2.0/24'];
const defaultPrivateAppSubnetCidrs = ['10.0.10.0/24', '10.0.11.0/24', '10.0.12.0/24'];
const defaultPrivateDataSubnetCidrs = ['10.0.20.0/24', '10.0.21.0/24', '10.0.22.0/24'];

// Default tags for VPC resources
const tags = getDefaultTags({ Component: 'VPC' });

/**
 * Interface defining options for VPC creation
 */
export interface VpcOptions {
    /** CIDR block for the VPC (default: 10.0.0.0/16) */
    cidrBlock?: string;
    /** CIDR blocks for public subnets */
    publicSubnetCidrs?: string[];
    /** CIDR blocks for private application subnets */
    privateAppSubnetCidrs?: string[];
    /** CIDR blocks for private data subnets */
    privateDataSubnetCidrs?: string[];
    /** Whether to enable DNS support (default: true) */
    enableDnsSupport?: boolean;
    /** Whether to enable DNS hostnames (default: true) */
    enableDnsHostnames?: boolean;
    /** Whether to enable VPC Flow Logs (default: true) */
    enableFlowLogs?: boolean;
    /** Number of NAT Gateways to create (default: 1) */
    natGatewaysCount?: number;
    /** Additional tags to apply to VPC resources */
    tags?: { [key: string]: string };
}

/**
 * Interface defining the output of VPC creation
 */
export interface VpcOutput {
    /** The VPC resource */
    vpc: aws.ec2.Vpc;
    /** The VPC ID */
    vpcId: string;
    /** IDs of public subnets */
    publicSubnetIds: pulumi.Output<string[]>;
    /** IDs of private application subnets */
    privateAppSubnetIds: pulumi.Output<string[]>;
    /** IDs of private data subnets */
    privateDataSubnetIds: pulumi.Output<string[]>;
    /** IDs of NAT Gateways */
    natGatewayIds: pulumi.Output<string[]>;
    /** ID of the Internet Gateway */
    internetGatewayId: string;
    /** IDs of route tables */
    routeTableIds: {
        public: string;
        private: string[];
        data: string;
    };
    /** IDs of Network ACLs */
    networkAclIds: {
        public: string;
        privateApp: string;
        privateData: string;
    };
}

/**
 * Interface defining subnet configuration
 */
export interface SubnetConfig {
    /** CIDR block for the subnet */
    cidrBlock: string;
    /** Availability zone for the subnet */
    availabilityZone: string;
    /** Whether to map public IP on launch (for public subnets) */
    mapPublicIpOnLaunch: boolean;
    /** Type of subnet (public, private-app, private-data) */
    type: string;
    /** Additional tags for the subnet */
    tags?: { [key: string]: string };
}

/**
 * Creates a VPC with public and private subnets across multiple availability zones
 * 
 * @param name Base name for VPC resources
 * @param options VPC configuration options
 * @returns VPC configuration including VPC ID, subnet IDs, and route table IDs
 */
export function createVpc(name: string, options: VpcOptions = {}): VpcOutput {
    // Get configuration values with defaults
    const cidrBlock = options.cidrBlock || vpcConfig.get('cidrBlock') || defaultCidr;
    const publicSubnetCidrs = options.publicSubnetCidrs || vpcConfig.getObject<string[]>('publicSubnetCidrs') || defaultPublicSubnetCidrs;
    const privateAppSubnetCidrs = options.privateAppSubnetCidrs || vpcConfig.getObject<string[]>('privateAppSubnetCidrs') || defaultPrivateAppSubnetCidrs;
    const privateDataSubnetCidrs = options.privateDataSubnetCidrs || vpcConfig.getObject<string[]>('privateDataSubnetCidrs') || defaultPrivateDataSubnetCidrs;
    const enableDnsSupport = options.enableDnsSupport !== false;
    const enableDnsHostnames = options.enableDnsHostnames !== false;
    const enableFlowLogs = options.enableFlowLogs !== false;
    const natGatewaysCount = options.natGatewaysCount || vpcConfig.getNumber('natGatewaysCount') || 1;
    const resourceTags = { ...tags, ...(options.tags || {}) };

    // Create VPC
    const vpc = new aws.ec2.Vpc(getResourceName('vpc', name), {
        cidrBlock,
        enableDnsSupport,
        enableDnsHostnames,
        tags: {
            ...resourceTags,
            Name: getResourceName('vpc', name),
        },
    });

    // Get available AZs
    const azs = getAvailabilityZones(3);

    // Create Internet Gateway
    const internetGateway = createInternetGateway(name, vpc.id, { tags: resourceTags });

    // Create subnets
    const publicSubnets = azs.apply(availableAzs => 
        createSubnets(
            vpc.id,
            'public',
            publicSubnetCidrs.slice(0, availableAzs.length),
            availableAzs,
            true,
            { tags: resourceTags }
        )
    );

    const privateAppSubnets = azs.apply(availableAzs => 
        createSubnets(
            vpc.id,
            'private-app',
            privateAppSubnetCidrs.slice(0, availableAzs.length),
            availableAzs,
            false,
            { tags: resourceTags }
        )
    );

    const privateDataSubnets = azs.apply(availableAzs => 
        createSubnets(
            vpc.id,
            'private-data',
            privateDataSubnetCidrs.slice(0, availableAzs.length),
            availableAzs,
            false,
            { tags: resourceTags }
        )
    );

    // Get subnet IDs
    const publicSubnetIds = publicSubnets.apply(subnets => getSubnetIds(subnets));
    const privateAppSubnetIds = privateAppSubnets.apply(subnets => getSubnetIds(subnets));
    const privateDataSubnetIds = privateDataSubnets.apply(subnets => getSubnetIds(subnets));

    // Create NAT Gateways in public subnets
    const natGateways = publicSubnetIds.apply(subnetIds => {
        // Limit to configured number of NAT Gateways
        const natSubnetIds = subnetIds.slice(0, natGatewaysCount);
        return createNatGateways(name, natSubnetIds, { tags: resourceTags });
    });

    // Create route tables
    const natGatewayIds = natGateways.apply(gateways => gateways.map(ng => ng.id));
    const routeTables = pulumi.all([vpc.id, natGatewayIds, internetGateway.id]).apply(
        ([vpcId, ngIds, igwId]) => 
            createRouteTables(
                vpcId, 
                { internetGatewayId: igwId, natGatewayIds: ngIds },
                { tags: resourceTags }
            )
    );

    // Associate subnets with route tables
    const routeTableAssociations = pulumi.all([
        publicSubnetIds, 
        routeTables.public, 
        privateAppSubnetIds, 
        routeTables.private,
        privateDataSubnetIds,
        routeTables.data
    ]).apply(([pubIds, pubRtId, privAppIds, privRtIds, privDataIds, dataRtId]) => 
        associateSubnets(pubIds, pubRtId, privAppIds, privRtIds, privDataIds, dataRtId)
    );

    // Create Network ACLs
    const networkAcls = pulumi.all([vpc.id, publicSubnetIds, privateAppSubnetIds, privateDataSubnetIds])
        .apply(([vpcId, pubIds, privAppIds, privDataIds]) => 
            createNetworkAcls(vpcId, pubIds, privAppIds, privDataIds, { tags: resourceTags })
        );

    // Enable VPC Flow Logs if configured
    let flowLogs = undefined;
    if (enableFlowLogs) {
        flowLogs = enableVpcFlowLogs(vpc.id, { tags: resourceTags });
    }

    // Return VPC configuration
    return {
        vpc,
        vpcId: vpc.id,
        publicSubnetIds,
        privateAppSubnetIds,
        privateDataSubnetIds,
        natGatewayIds,
        internetGatewayId: internetGateway.id,
        routeTableIds: {
            public: routeTables.public,
            private: routeTables.private,
            data: routeTables.data,
        },
        networkAclIds: {
            public: networkAcls.public,
            privateApp: networkAcls.privateApp,
            privateData: networkAcls.privateData,
        },
    };
}

/**
 * Creates subnets across multiple availability zones
 * 
 * @param vpcId ID of the VPC
 * @param namePrefix Prefix for subnet names
 * @param cidrBlocks CIDR blocks for the subnets
 * @param availabilityZones Availability zones to distribute subnets across
 * @param mapPublicIpOnLaunch Whether to map public IP on launch
 * @param options Additional options for subnet creation
 * @returns Created subnet resources
 */
export function createSubnets(
    vpcId: string,
    namePrefix: string,
    cidrBlocks: string[],
    availabilityZones: string[],
    mapPublicIpOnLaunch: boolean,
    options: AwsResourceOptions = {}
): aws.ec2.Subnet[] {
    // Ensure we have matching number of CIDRs and AZs
    const count = Math.min(cidrBlocks.length, availabilityZones.length);
    
    // Create subnets
    const subnets: aws.ec2.Subnet[] = [];
    for (let i = 0; i < count; i++) {
        const azSuffix = availabilityZones[i].slice(-1).toLowerCase();
        const subnetName = getResourceName('subnet', `${namePrefix}-${azSuffix}`);
        
        const subnetTags = {
            ...options.tags,
            Name: subnetName,
            'aws-cdk:subnet-type': namePrefix.startsWith('public') ? 'Public' : 'Private',
            'aws-cdk:subnet-name': namePrefix,
            Type: namePrefix,
        };

        const subnet = new aws.ec2.Subnet(subnetName, {
            vpcId,
            cidrBlock: cidrBlocks[i],
            availabilityZone: availabilityZones[i],
            mapPublicIpOnLaunch,
            tags: subnetTags,
        });

        subnets.push(subnet);
    }

    return subnets;
}

/**
 * Creates an Internet Gateway and attaches it to the VPC
 * 
 * @param name Name for the Internet Gateway
 * @param vpcId ID of the VPC to attach the Internet Gateway to
 * @param options Additional options for Internet Gateway creation
 * @returns Created Internet Gateway resource
 */
export function createInternetGateway(
    name: string,
    vpcId: pulumi.Output<string>,
    options: AwsResourceOptions = {}
): aws.ec2.InternetGateway {
    // Create Internet Gateway
    const igwName = getResourceName('igw', name);
    const igw = new aws.ec2.InternetGateway(igwName, {
        tags: {
            ...options.tags,
            Name: igwName,
        },
    });

    // Attach to VPC
    new aws.ec2.InternetGatewayAttachment(`${igwName}-attachment`, {
        vpcId,
        internetGatewayId: igw.id,
    });

    return igw;
}

/**
 * Creates NAT Gateways in public subnets for private subnet internet access
 * 
 * @param namePrefix Prefix for NAT Gateway names
 * @param publicSubnetIds IDs of public subnets to place NAT Gateways in
 * @param options Additional options for NAT Gateway creation
 * @returns Created NAT Gateway resources
 */
export function createNatGateways(
    namePrefix: string,
    publicSubnetIds: string[],
    options: AwsResourceOptions = {}
): aws.ec2.NatGateway[] {
    const natGateways: aws.ec2.NatGateway[] = [];

    // Create a NAT Gateway in each provided public subnet
    for (let i = 0; i < publicSubnetIds.length; i++) {
        const azSuffix = String.fromCharCode(97 + i); // a, b, c, ...
        const eipName = getResourceName('eip', `nat-${namePrefix}-${azSuffix}`);
        const natName = getResourceName('nat', `${namePrefix}-${azSuffix}`);

        // Create Elastic IP for NAT Gateway
        const eip = new aws.ec2.Eip(eipName, {
            domain: 'vpc',
            tags: {
                ...options.tags,
                Name: eipName,
            },
        });

        // Create NAT Gateway in public subnet
        const natGateway = new aws.ec2.NatGateway(natName, {
            subnetId: publicSubnetIds[i],
            allocationId: eip.id,
            tags: {
                ...options.tags,
                Name: natName,
            },
        });

        natGateways.push(natGateway);
    }

    return natGateways;
}

/**
 * Creates route tables for public and private subnets
 * 
 * @param vpcId ID of the VPC
 * @param gatewayIds IDs of Internet Gateway and NAT Gateways
 * @param options Additional options for route table creation
 * @returns Created route table resources
 */
export function createRouteTables(
    vpcId: string,
    gatewayIds: { internetGatewayId: string, natGatewayIds: string[] },
    options: AwsResourceOptions = {}
): { public: string, private: string[], data: string } {
    // Create public route table with route to Internet Gateway
    const publicRtName = getResourceName('rtb', 'public');
    const publicRt = new aws.ec2.RouteTable(publicRtName, {
        vpcId,
        tags: {
            ...options.tags,
            Name: publicRtName,
            Type: 'public',
        },
    });

    // Create route to Internet Gateway
    new aws.ec2.Route(`${publicRtName}-igw-route`, {
        routeTableId: publicRt.id,
        destinationCidrBlock: '0.0.0.0/0',
        gatewayId: gatewayIds.internetGatewayId,
    });

    // Create private route tables with routes to NAT Gateways
    const privateRts: aws.ec2.RouteTable[] = [];
    for (let i = 0; i < gatewayIds.natGatewayIds.length; i++) {
        const azSuffix = String.fromCharCode(97 + i); // a, b, c, ...
        const privateRtName = getResourceName('rtb', `private-app-${azSuffix}`);
        
        const privateRt = new aws.ec2.RouteTable(privateRtName, {
            vpcId,
            tags: {
                ...options.tags,
                Name: privateRtName,
                Type: 'private-app',
            },
        });

        // Create route to NAT Gateway
        new aws.ec2.Route(`${privateRtName}-nat-route`, {
            routeTableId: privateRt.id,
            destinationCidrBlock: '0.0.0.0/0',
            natGatewayId: gatewayIds.natGatewayIds[i],
        });

        privateRts.push(privateRt);
    }

    // Create data subnet route table with more restricted routing
    const dataRtName = getResourceName('rtb', 'private-data');
    const dataRt = new aws.ec2.RouteTable(dataRtName, {
        vpcId,
        tags: {
            ...options.tags,
            Name: dataRtName,
            Type: 'private-data',
        },
    });

    // Add route to NAT Gateway (usually just one for data subnets)
    if (gatewayIds.natGatewayIds.length > 0) {
        new aws.ec2.Route(`${dataRtName}-nat-route`, {
            routeTableId: dataRt.id,
            destinationCidrBlock: '0.0.0.0/0',
            natGatewayId: gatewayIds.natGatewayIds[0],
        });
    }

    return {
        public: publicRt.id,
        private: privateRts.map(rt => rt.id),
        data: dataRt.id,
    };
}

/**
 * Associates subnets with their respective route tables
 * 
 * @param publicSubnetIds IDs of public subnets
 * @param publicRouteTableId ID of public route table
 * @param privateSubnetIds IDs of private application subnets
 * @param privateRouteTableIds IDs of private route tables
 * @param dataSubnetIds IDs of private data subnets
 * @param dataRouteTableId ID of data route table
 * @returns Created route table association resources
 */
export function associateSubnets(
    publicSubnetIds: string[],
    publicRouteTableId: string,
    privateSubnetIds: string[],
    privateRouteTableIds: string[],
    dataSubnetIds: string[],
    dataRouteTableId: string
): aws.ec2.RouteTableAssociation[] {
    const associations: aws.ec2.RouteTableAssociation[] = [];

    // Associate public subnets with public route table
    for (let i = 0; i < publicSubnetIds.length; i++) {
        const association = new aws.ec2.RouteTableAssociation(`public-rta-${i}`, {
            subnetId: publicSubnetIds[i],
            routeTableId: publicRouteTableId,
        });
        associations.push(association);
    }

    // Associate private subnets with private route tables
    for (let i = 0; i < privateSubnetIds.length; i++) {
        // Use corresponding private route table if available, otherwise use the first one
        const rtbIndex = i < privateRouteTableIds.length ? i : 0;
        const association = new aws.ec2.RouteTableAssociation(`private-app-rta-${i}`, {
            subnetId: privateSubnetIds[i],
            routeTableId: privateRouteTableIds[rtbIndex],
        });
        associations.push(association);
    }

    // Associate data subnets with data route table
    for (let i = 0; i < dataSubnetIds.length; i++) {
        const association = new aws.ec2.RouteTableAssociation(`private-data-rta-${i}`, {
            subnetId: dataSubnetIds[i],
            routeTableId: dataRouteTableId,
        });
        associations.push(association);
    }

    return associations;
}

/**
 * Creates Network ACLs for additional subnet security
 * 
 * @param vpcId ID of the VPC
 * @param publicSubnetIds IDs of public subnets
 * @param privateAppSubnetIds IDs of private application subnets
 * @param privateDataSubnetIds IDs of private data subnets
 * @param options Additional options for Network ACL creation
 * @returns Created Network ACL resources
 */
export function createNetworkAcls(
    vpcId: string,
    publicSubnetIds: string[],
    privateAppSubnetIds: string[],
    privateDataSubnetIds: string[],
    options: AwsResourceOptions = {}
): { public: string, privateApp: string, privateData: string } {
    // Create Network ACL for public subnets
    const publicNaclName = getResourceName('nacl', 'public');
    const publicNacl = new aws.ec2.NetworkAcl(publicNaclName, {
        vpcId,
        tags: {
            ...options.tags,
            Name: publicNaclName,
            Type: 'public',
        },
    });

    // Add rules for public Network ACL
    // Allow all outbound traffic
    new aws.ec2.NetworkAclRule(`${publicNaclName}-outbound-all`, {
        networkAclId: publicNacl.id,
        ruleNumber: 100,
        protocol: '-1', // All protocols
        ruleAction: 'allow',
        egress: true,
        cidrBlock: '0.0.0.0/0',
    });

    // Allow all inbound HTTP/HTTPS traffic
    new aws.ec2.NetworkAclRule(`${publicNaclName}-inbound-http`, {
        networkAclId: publicNacl.id,
        ruleNumber: 100,
        protocol: 'tcp',
        ruleAction: 'allow',
        egress: false,
        cidrBlock: '0.0.0.0/0',
        fromPort: 80,
        toPort: 80,
    });

    new aws.ec2.NetworkAclRule(`${publicNaclName}-inbound-https`, {
        networkAclId: publicNacl.id,
        ruleNumber: 110,
        protocol: 'tcp',
        ruleAction: 'allow',
        egress: false,
        cidrBlock: '0.0.0.0/0',
        fromPort: 443,
        toPort: 443,
    });

    // Allow inbound ephemeral ports for return traffic
    new aws.ec2.NetworkAclRule(`${publicNaclName}-inbound-ephemeral`, {
        networkAclId: publicNacl.id,
        ruleNumber: 120,
        protocol: 'tcp',
        ruleAction: 'allow',
        egress: false,
        cidrBlock: '0.0.0.0/0',
        fromPort: 1024,
        toPort: 65535,
    });

    // Create Network ACL for private application subnets
    const privateAppNaclName = getResourceName('nacl', 'private-app');
    const privateAppNacl = new aws.ec2.NetworkAcl(privateAppNaclName, {
        vpcId,
        tags: {
            ...options.tags,
            Name: privateAppNaclName,
            Type: 'private-app',
        },
    });

    // Add rules for private app Network ACL
    // Allow all outbound traffic to VPC
    new aws.ec2.NetworkAclRule(`${privateAppNaclName}-outbound-vpc`, {
        networkAclId: privateAppNacl.id,
        ruleNumber: 100,
        protocol: '-1', // All protocols
        ruleAction: 'allow',
        egress: true,
        cidrBlock: defaultCidr, // VPC CIDR
    });

    // Allow outbound HTTP/HTTPS for external API access
    new aws.ec2.NetworkAclRule(`${privateAppNaclName}-outbound-http`, {
        networkAclId: privateAppNacl.id,
        ruleNumber: 110,
        protocol: 'tcp',
        ruleAction: 'allow',
        egress: true,
        cidrBlock: '0.0.0.0/0',
        fromPort: 80,
        toPort: 80,
    });

    new aws.ec2.NetworkAclRule(`${privateAppNaclName}-outbound-https`, {
        networkAclId: privateAppNacl.id,
        ruleNumber: 120,
        protocol: 'tcp',
        ruleAction: 'allow',
        egress: true,
        cidrBlock: '0.0.0.0/0',
        fromPort: 443,
        toPort: 443,
    });

    // Allow inbound traffic from VPC
    new aws.ec2.NetworkAclRule(`${privateAppNaclName}-inbound-vpc`, {
        networkAclId: privateAppNacl.id,
        ruleNumber: 100,
        protocol: '-1', // All protocols
        ruleAction: 'allow',
        egress: false,
        cidrBlock: defaultCidr, // VPC CIDR
    });

    // Create Network ACL for private data subnets
    const privateDataNaclName = getResourceName('nacl', 'private-data');
    const privateDataNacl = new aws.ec2.NetworkAcl(privateDataNaclName, {
        vpcId,
        tags: {
            ...options.tags,
            Name: privateDataNaclName,
            Type: 'private-data',
        },
    });

    // Add rules for private data Network ACL
    // Allow outbound traffic to VPC only
    new aws.ec2.NetworkAclRule(`${privateDataNaclName}-outbound-vpc`, {
        networkAclId: privateDataNacl.id,
        ruleNumber: 100,
        protocol: '-1', // All protocols
        ruleAction: 'allow',
        egress: true,
        cidrBlock: defaultCidr, // VPC CIDR
    });

    // Allow inbound traffic from application subnets only
    for (let i = 0; i < defaultPrivateAppSubnetCidrs.length; i++) {
        new aws.ec2.NetworkAclRule(`${privateDataNaclName}-inbound-app-${i}`, {
            networkAclId: privateDataNacl.id,
            ruleNumber: 100 + i,
            protocol: '-1', // All protocols
            ruleAction: 'allow',
            egress: false,
            cidrBlock: defaultPrivateAppSubnetCidrs[i],
        });
    }

    // Associate Network ACLs with respective subnets
    for (let i = 0; i < publicSubnetIds.length; i++) {
        new aws.ec2.NetworkAclAssociation(`public-nacl-assoc-${i}`, {
            networkAclId: publicNacl.id,
            subnetId: publicSubnetIds[i],
        });
    }

    for (let i = 0; i < privateAppSubnetIds.length; i++) {
        new aws.ec2.NetworkAclAssociation(`private-app-nacl-assoc-${i}`, {
            networkAclId: privateAppNacl.id,
            subnetId: privateAppSubnetIds[i],
        });
    }

    for (let i = 0; i < privateDataSubnetIds.length; i++) {
        new aws.ec2.NetworkAclAssociation(`private-data-nacl-assoc-${i}`, {
            networkAclId: privateDataNacl.id,
            subnetId: privateDataSubnetIds[i],
        });
    }

    return {
        public: publicNacl.id,
        privateApp: privateAppNacl.id,
        privateData: privateDataNacl.id,
    };
}

/**
 * Enables VPC Flow Logs for network traffic monitoring
 * 
 * @param vpcId ID of the VPC
 * @param options Additional options for Flow Log creation
 * @returns Created Flow Log resource
 */
export function enableVpcFlowLogs(
    vpcId: string,
    options: AwsResourceOptions = {}
): aws.ec2.FlowLog {
    // Create IAM role for Flow Logs
    const roleName = getResourceName('role', 'vpc-flow-logs');
    const role = new aws.iam.Role(roleName, {
        assumeRolePolicy: JSON.stringify({
            Version: '2012-10-17',
            Statement: [{
                Action: 'sts:AssumeRole',
                Principal: {
                    Service: 'vpc-flow-logs.amazonaws.com'
                },
                Effect: 'Allow',
                Sid: '',
            }],
        }),
        tags: options.tags,
    });

    // Attach policy to role
    const policyName = getResourceName('policy', 'vpc-flow-logs');
    const policy = new aws.iam.Policy(policyName, {
        description: 'Policy for VPC Flow Logs',
        policy: JSON.stringify({
            Version: '2012-10-17',
            Statement: [{
                Action: [
                    'logs:CreateLogGroup',
                    'logs:CreateLogStream',
                    'logs:PutLogEvents',
                    'logs:DescribeLogGroups',
                    'logs:DescribeLogStreams',
                ],
                Resource: '*',
                Effect: 'Allow',
            }],
        }),
        tags: options.tags,
    });

    // Attach policy to role
    new aws.iam.RolePolicyAttachment(`${roleName}-attachment`, {
        role: role.name,
        policyArn: policy.arn,
    });

    // Create log group
    const logGroupName = getResourceName('log-group', 'vpc-flow-logs');
    const logGroup = new aws.cloudwatch.LogGroup(logGroupName, {
        retentionInDays: 30,
        tags: options.tags,
    });

    // Create flow log
    const flowLogName = getResourceName('flow-log', 'vpc');
    return new aws.ec2.FlowLog(flowLogName, {
        iamRoleArn: role.arn,
        logDestination: logGroup.arn,
        trafficType: 'ALL',
        vpcId: vpcId,
        logFormat: '${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}',
        tags: {
            ...options.tags,
            Name: flowLogName,
        },
    });
}

/**
 * Extracts subnet IDs from subnet resources
 * 
 * @param subnets Subnet resources
 * @returns Array of subnet IDs
 */
export function getSubnetIds(subnets: aws.ec2.Subnet[]): string[] {
    return subnets.map(subnet => subnet.id);
}