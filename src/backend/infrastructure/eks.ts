/**
 * AWS EKS (Elastic Kubernetes Service) Infrastructure for the Borrow Rate & Locate Fee Pricing Engine.
 * 
 * This module defines and provisions a secure, scalable, and highly available Kubernetes cluster
 * with appropriate node groups, IAM roles, and network configuration to support the application's
 * containerized microservices architecture.
 */

import * as aws from '@pulumi/aws'; // @pulumi/aws v5.0.0+
import * as eks from '@pulumi/eks'; // @pulumi/eks v1.0.0+
import * as pulumi from '@pulumi/pulumi'; // @pulumi/pulumi v3.0.0+
import * as k8s from '@pulumi/kubernetes'; // @pulumi/kubernetes v3.0.0+
import { 
    configureAwsProvider,
    getResourceName,
    getDefaultTags,
    getAvailabilityZones,
    AwsResourceOptions
} from './aws';
import { VpcOutput } from './vpc';
import { SecurityGroupsOutput } from './security_groups';

// Global configuration
const config = new pulumi.Config();
const stackName = pulumi.getStack();
const eksConfig = new pulumi.Config('eks');

// Default configurations
const defaultK8sVersion = '1.28';
const defaultNodeGroupConfig = {
    instanceType: 'm5.large',
    desiredCapacity: 3,
    minSize: 3,
    maxSize: 10,
    diskSize: 100 // GB
};

// Default tags for EKS resources
const tags = getDefaultTags({ Component: 'EKS' });

/**
 * Interface defining options for EKS cluster creation
 */
export interface EksOptions {
    /** Kubernetes version for the EKS cluster */
    version?: string;
    /** Whether to enable private endpoint for EKS API server */
    enablePrivateEndpoint?: boolean;
    /** Whether to enable public endpoint for EKS API server */
    enablePublicEndpoint?: boolean;
    /** Log types to enable for the EKS cluster */
    clusterLogTypes?: string[];
    /** Additional tags to apply to EKS resources */
    tags?: { [key: string]: string };
}

/**
 * Interface defining options for EKS node group creation
 */
export interface NodeGroupOptions {
    /** EC2 instance type for node group */
    instanceType?: string;
    /** Desired number of nodes */
    desiredCapacity?: number;
    /** Minimum number of nodes */
    minSize?: number;
    /** Maximum number of nodes */
    maxSize?: number;
    /** Size of root EBS volume in GB */
    diskSize?: number;
    /** Kubernetes labels to apply to nodes */
    labels?: { [key: string]: string };
    /** Kubernetes taints to apply to nodes */
    taints?: { key: string; value: string; effect: string; }[];
    /** Additional tags to apply to node group resources */
    tags?: { [key: string]: string };
}

/**
 * Interface defining the output of EKS cluster creation
 */
export interface EksClusterOutput {
    /** The EKS cluster object */
    cluster: eks.Cluster;
    /** The name of the EKS cluster */
    clusterName: string;
    /** The ARN of the EKS cluster */
    clusterArn: pulumi.Output<string>;
    /** Kubeconfig for accessing the cluster */
    kubeconfig: pulumi.Output<string>;
    /** Created node groups */
    nodeGroups: {
        system?: eks.NodeGroup;
        application?: eks.NodeGroup;
    };
    /** IAM roles created for the cluster */
    iamRoles: {
        clusterRole: aws.iam.Role;
        nodeRole: aws.iam.Role;
    };
}

/**
 * Interface defining options for cluster autoscaler configuration
 */
export interface ClusterAutoscalerOptions {
    /** Version of cluster autoscaler to deploy */
    version?: string;
    /** Delay after adding nodes before considering scale down */
    scaleDownDelayAfterAdd?: number;
    /** How long a node should be unused before scaling down */
    scaleDownUnneededTime?: number;
    /** Whether to enable detailed metrics */
    enableDetailedMetrics?: boolean;
    /** Resource requests and limits */
    resources?: {
        requests?: {
            cpu?: string;
            memory?: string;
        };
        limits?: {
            cpu?: string;
            memory?: string;
        };
    };
}

/**
 * Creates an EKS cluster with the specified configuration
 * 
 * @param name Base name for EKS resources
 * @param vpcOutput VPC configuration for the cluster
 * @param securityGroupsOutput Security groups for the cluster
 * @param options Additional options for EKS cluster creation
 * @returns EKS cluster configuration including cluster object, kubeconfig, and node groups
 */
export function createEksCluster(
    name: string,
    vpcOutput: VpcOutput,
    securityGroupsOutput: SecurityGroupsOutput,
    options: EksOptions = {}
): EksClusterOutput {
    // Get configuration values with defaults
    const k8sVersion = options.version || eksConfig.get('version') || defaultK8sVersion;
    const enablePrivateEndpoint = options.enablePrivateEndpoint ?? eksConfig.getBoolean('enablePrivateEndpoint') ?? true;
    const enablePublicEndpoint = options.enablePublicEndpoint ?? eksConfig.getBoolean('enablePublicEndpoint') ?? true;
    const clusterLogTypes = options.clusterLogTypes || 
        eksConfig.getObject<string[]>('clusterLogTypes') || 
        ['api', 'audit', 'authenticator', 'controllerManager', 'scheduler'];
    const resourceTags = { ...tags, ...(options.tags || {}) };
    
    // Create IAM roles for the cluster and node groups
    const iamRoles = createIamRoles(name, { tags: resourceTags });
    
    // Get subnet IDs for the cluster
    const subnetIds = [
        ...vpcOutput.privateAppSubnetIds,
        ...(enablePublicEndpoint ? vpcOutput.publicSubnetIds : [])
    ];
    
    // Create the EKS cluster
    const clusterName = getResourceName('eks', name);
    const cluster = new eks.Cluster(clusterName, {
        // Basic cluster configuration
        name: clusterName,
        version: k8sVersion,
        roleArn: iamRoles.clusterRole.arn,
        
        // VPC and networking configuration
        vpcId: vpcOutput.vpcId,
        subnetIds: subnetIds,
        securityGroupIds: [securityGroupsOutput.eksClusterSgId],
        
        // Endpoint access configuration
        endpointPrivateAccess: enablePrivateEndpoint,
        endpointPublicAccess: enablePublicEndpoint,
        
        // Logging configuration
        enabledClusterLogTypes: clusterLogTypes,
        
        // Skip default node group creation, we'll create custom ones
        skipDefaultNodeGroup: true,
        
        // Tags for all cluster resources
        tags: resourceTags,
    });
    
    // Create managed node groups
    const privateSubnetIds = vpcOutput.privateAppSubnetIds;
    const nodeGroups = createNodeGroups(
        cluster, 
        iamRoles.nodeRole.arn, 
        privateSubnetIds, 
        { tags: resourceTags }
    );
    
    // Configure cluster autoscaler
    const autoscaler = configureClusterAutoscaler(cluster, nodeGroups, { tags: resourceTags });
    
    // Setup logging
    const logging = setupClusterLogging(cluster, { tags: resourceTags });
    
    // Setup monitoring
    const monitoring = setupClusterMonitoring(cluster, { tags: resourceTags });
    
    // Return cluster output
    return {
        cluster,
        clusterName: clusterName,
        clusterArn: cluster.eksCluster.arn,
        kubeconfig: cluster.kubeconfig,
        nodeGroups,
        iamRoles,
    };
}

/**
 * Creates IAM roles required for EKS cluster and node groups
 * 
 * @param clusterName Base name for IAM roles
 * @param options Additional options for IAM role creation
 * @returns Created IAM role resources
 */
function createIamRoles(
    clusterName: string,
    options: AwsResourceOptions = {}
): { clusterRole: aws.iam.Role; nodeRole: aws.iam.Role } {
    const resourceTags = { ...tags, ...(options.tags || {}) };
    
    // Create IAM role for EKS cluster
    const clusterRoleName = getResourceName('role', `eks-cluster-${clusterName}`);
    const clusterRole = new aws.iam.Role(clusterRoleName, {
        assumeRolePolicy: JSON.stringify({
            Version: '2012-10-17',
            Statement: [{
                Action: 'sts:AssumeRole',
                Principal: {
                    Service: 'eks.amazonaws.com'
                },
                Effect: 'Allow',
                Sid: ''
            }]
        }),
        tags: resourceTags
    });
    
    // Attach required policies to cluster role
    new aws.iam.RolePolicyAttachment(`${clusterRoleName}-AmazonEKSClusterPolicy`, {
        role: clusterRole.name,
        policyArn: 'arn:aws:iam::aws:policy/AmazonEKSClusterPolicy'
    });
    
    new aws.iam.RolePolicyAttachment(`${clusterRoleName}-AmazonEKSVPCResourceController`, {
        role: clusterRole.name,
        policyArn: 'arn:aws:iam::aws:policy/AmazonEKSVPCResourceController'
    });
    
    // Create IAM role for EKS node groups
    const nodeRoleName = getResourceName('role', `eks-node-${clusterName}`);
    const nodeRole = new aws.iam.Role(nodeRoleName, {
        assumeRolePolicy: JSON.stringify({
            Version: '2012-10-17',
            Statement: [{
                Action: 'sts:AssumeRole',
                Principal: {
                    Service: 'ec2.amazonaws.com'
                },
                Effect: 'Allow',
                Sid: ''
            }]
        }),
        tags: resourceTags
    });
    
    // Attach required policies to node role
    const nodePolicies = [
        'arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy',
        'arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy',
        'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly',
        'arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy'
    ];
    
    nodePolicies.forEach((policyArn, idx) => {
        new aws.iam.RolePolicyAttachment(`${nodeRoleName}-${idx}`, {
            role: nodeRole.name,
            policyArn
        });
    });
    
    // Create custom policy for node autoscaling
    const nodeAutoscalingPolicyName = getResourceName('policy', `eks-node-autoscaling-${clusterName}`);
    const nodeAutoscalingPolicy = new aws.iam.Policy(nodeAutoscalingPolicyName, {
        description: 'Policy for EKS node autoscaling',
        policy: JSON.stringify({
            Version: '2012-10-17',
            Statement: [{
                Action: [
                    'autoscaling:DescribeAutoScalingGroups',
                    'autoscaling:DescribeAutoScalingInstances',
                    'autoscaling:DescribeLaunchConfigurations',
                    'autoscaling:DescribeTags',
                    'autoscaling:SetDesiredCapacity',
                    'autoscaling:TerminateInstanceInAutoScalingGroup',
                    'ec2:DescribeLaunchTemplateVersions'
                ],
                Resource: '*',
                Effect: 'Allow'
            }]
        }),
        tags: resourceTags
    });
    
    // Attach autoscaling policy to node role
    new aws.iam.RolePolicyAttachment(`${nodeRoleName}-autoscaling`, {
        role: nodeRole.name,
        policyArn: nodeAutoscalingPolicy.arn
    });
    
    return {
        clusterRole,
        nodeRole
    };
}

/**
 * Creates node groups for the EKS cluster
 * 
 * @param cluster EKS cluster to create node groups for
 * @param nodeRoleArn ARN of the IAM role for node groups
 * @param subnetIds Subnet IDs to place nodes in
 * @param options Additional options for node group creation
 * @returns Created node group resources
 */
export function createNodeGroups(
    cluster: eks.Cluster,
    nodeRoleArn: string,
    subnetIds: pulumi.Output<string[]>,
    options: AwsResourceOptions = {}
): { system?: eks.NodeGroup; application?: eks.NodeGroup } {
    const resourceTags = { ...tags, ...(options.tags || {}) };
    
    // Create system node group for infrastructure components
    const systemNodeGroup = createSystemNodeGroup(
        cluster,
        nodeRoleArn,
        subnetIds,
        { tags: resourceTags }
    );
    
    // Create application node group for application workloads
    const applicationNodeGroup = createApplicationNodeGroup(
        cluster,
        nodeRoleArn,
        subnetIds,
        { tags: resourceTags }
    );
    
    return {
        system: systemNodeGroup,
        application: applicationNodeGroup
    };
}

/**
 * Creates a node group for system services like monitoring and logging
 * 
 * @param cluster EKS cluster to create node group for
 * @param nodeRoleArn ARN of the IAM role for node group
 * @param subnetIds Subnet IDs to place nodes in
 * @param options Additional options for node group creation
 * @returns Created system node group
 */
function createSystemNodeGroup(
    cluster: eks.Cluster,
    nodeRoleArn: string,
    subnetIds: pulumi.Output<string[]>,
    options: AwsResourceOptions = {}
): eks.NodeGroup {
    const resourceTags = { ...tags, ...(options.tags || {}) };
    
    // Get node group configuration from config or use defaults
    const instanceType = eksConfig.get('systemNodeInstanceType') || 't3.large';
    const desiredCapacity = eksConfig.getNumber('systemNodeDesiredCapacity') || 2;
    const minSize = eksConfig.getNumber('systemNodeMinSize') || 2;
    const maxSize = eksConfig.getNumber('systemNodeMaxSize') || 4;
    const diskSize = eksConfig.getNumber('systemNodeDiskSize') || 50;
    
    // System node group labels
    const labels = {
        'role': 'system',
        'node-type': 'system',
        'kubernetes.io/role': 'system'
    };
    
    // System node group taints to ensure only system workloads run on these nodes
    const taints = [{
        key: 'dedicated',
        value: 'system',
        effect: 'NoSchedule'
    }];
    
    // Create the system node group
    const nodeGroupName = getResourceName('nodegroup', 'system');
    const nodeGroup = new eks.NodeGroup(nodeGroupName, {
        cluster: cluster,
        nodeGroupName: nodeGroupName,
        nodeRoleArn: nodeRoleArn,
        subnetIds: subnetIds,
        
        // Node configuration
        instanceTypes: [instanceType],
        diskSize: diskSize,
        
        // Scaling configuration
        scalingConfig: {
            desiredSize: desiredCapacity,
            minSize: minSize,
            maxSize: maxSize
        },
        
        // Labels and taints
        labels: labels,
        taints: taints,
        
        // Tags
        tags: {
            ...resourceTags,
            Name: nodeGroupName,
            NodeType: 'system'
        }
    });
    
    return nodeGroup;
}

/**
 * Creates a node group for application workloads
 * 
 * @param cluster EKS cluster to create node group for
 * @param nodeRoleArn ARN of the IAM role for node group
 * @param subnetIds Subnet IDs to place nodes in
 * @param options Additional options for node group creation
 * @returns Created application node group
 */
function createApplicationNodeGroup(
    cluster: eks.Cluster,
    nodeRoleArn: string,
    subnetIds: pulumi.Output<string[]>,
    options: AwsResourceOptions = {}
): eks.NodeGroup {
    const resourceTags = { ...tags, ...(options.tags || {}) };
    
    // Get node group configuration from config or use defaults
    const instanceType = eksConfig.get('appNodeInstanceType') || 'm5.large';
    const desiredCapacity = eksConfig.getNumber('appNodeDesiredCapacity') || defaultNodeGroupConfig.desiredCapacity;
    const minSize = eksConfig.getNumber('appNodeMinSize') || defaultNodeGroupConfig.minSize;
    const maxSize = eksConfig.getNumber('appNodeMaxSize') || defaultNodeGroupConfig.maxSize;
    const diskSize = eksConfig.getNumber('appNodeDiskSize') || defaultNodeGroupConfig.diskSize;
    
    // Application node group labels
    const labels = {
        'role': 'application',
        'node-type': 'application',
        'kubernetes.io/role': 'application'
    };
    
    // Create the application node group
    const nodeGroupName = getResourceName('nodegroup', 'application');
    const nodeGroup = new eks.NodeGroup(nodeGroupName, {
        cluster: cluster,
        nodeGroupName: nodeGroupName,
        nodeRoleArn: nodeRoleArn,
        subnetIds: subnetIds,
        
        // Node configuration
        instanceTypes: [instanceType],
        diskSize: diskSize,
        
        // Scaling configuration
        scalingConfig: {
            desiredSize: desiredCapacity,
            minSize: minSize,
            maxSize: maxSize
        },
        
        // Labels
        labels: labels,
        
        // Tags
        tags: {
            ...resourceTags,
            Name: nodeGroupName,
            NodeType: 'application'
        }
    });
    
    return nodeGroup;
}

/**
 * Configures cluster autoscaler for EKS node groups
 * 
 * @param cluster EKS cluster to configure autoscaler for
 * @param nodeGroups Node groups to enable autoscaling for
 * @param options Additional options for autoscaler configuration
 * @returns Cluster autoscaler configuration
 */
export function configureClusterAutoscaler(
    cluster: eks.Cluster,
    nodeGroups: { system?: eks.NodeGroup; application?: eks.NodeGroup },
    options: ClusterAutoscalerOptions = {}
): k8s.helm.v3.Release {
    // Get autoscaler configuration from options or use defaults
    const version = options.version || eksConfig.get('autoscalerVersion') || '1.27.1';
    const scaleDownDelayAfterAdd = options.scaleDownDelayAfterAdd || 
        eksConfig.getNumber('autoscalerScaleDownDelayAfterAdd') || 10; // minutes
    const scaleDownUnneededTime = options.scaleDownUnneededTime || 
        eksConfig.getNumber('autoscalerScaleDownUnneededTime') || 10; // minutes
    const enableDetailedMetrics = options.enableDetailedMetrics ?? 
        eksConfig.getBoolean('autoscalerEnableDetailedMetrics') ?? true;
    
    // Default resource requests and limits
    const resources = options.resources || {
        requests: {
            cpu: '100m',
            memory: '300Mi'
        },
        limits: {
            cpu: '200m',
            memory: '500Mi'
        }
    };
    
    // Create Kubernetes provider using the cluster's kubeconfig
    const k8sProvider = new k8s.Provider('k8s-provider', {
        kubeconfig: cluster.kubeconfig.apply(JSON.stringify),
    });
    
    // Deploy cluster autoscaler using Helm chart
    const autoscalerName = getResourceName('autoscaler', 'cluster');
    const autoscaler = new k8s.helm.v3.Release(autoscalerName, {
        chart: 'cluster-autoscaler',
        version: version,
        repositoryOpts: {
            repo: 'https://kubernetes.github.io/autoscaler'
        },
        namespace: 'kube-system',
        values: {
            autoDiscovery: {
                clusterName: cluster.eksCluster.name,
            },
            awsRegion: aws.config.region,
            rbac: {
                create: true,
                serviceAccount: {
                    annotations: {
                        'eks.amazonaws.com/role-arn': nodeGroups.application?.nodeGroupName || ''
                    }
                }
            },
            extraArgs: {
                'scale-down-delay-after-add': `${scaleDownDelayAfterAdd}m`,
                'scale-down-unneeded-time': `${scaleDownUnneededTime}m`,
                'scale-down-utilization-threshold': '0.5',
                'scan-interval': '10s',
                'max-empty-bulk-delete': '10',
                'skip-nodes-with-local-storage': 'false',
                'skip-nodes-with-system-pods': 'true',
                'balance-similar-node-groups': 'true',
                'expander': 'least-waste',
            },
            extraEnv: enableDetailedMetrics ? {
                PROMETHEUS_DETAILED_METRICS: 'true'
            } : undefined,
            resources: resources,
            priorityClassName: 'system-cluster-critical',
            podAnnotations: {
                'cluster-autoscaler.kubernetes.io/safe-to-evict': 'false'
            }
        }
    }, { provider: k8sProvider });
    
    return autoscaler;
}

/**
 * Sets up logging for the EKS cluster
 * 
 * @param cluster EKS cluster to set up logging for
 * @param options Additional options for logging configuration
 * @returns Logging configuration
 */
export function setupClusterLogging(
    cluster: eks.Cluster,
    options: AwsResourceOptions = {}
): k8s.helm.v3.Release {
    const resourceTags = { ...tags, ...(options.tags || {}) };
    
    // Create Kubernetes provider using the cluster's kubeconfig
    const k8sProvider = new k8s.Provider('k8s-logging-provider', {
        kubeconfig: cluster.kubeconfig.apply(JSON.stringify),
    });
    
    // Deploy Fluent Bit for log collection
    const fluentBitName = getResourceName('logging', 'fluent-bit');
    const fluentBit = new k8s.helm.v3.Release(fluentBitName, {
        chart: 'fluent-bit',
        version: '0.20.0', // Use specific chart version for stability
        repositoryOpts: {
            repo: 'https://fluent.github.io/helm-charts'
        },
        namespace: 'logging',
        createNamespace: true,
        values: {
            serviceAccount: {
                create: true,
                annotations: {
                    'eks.amazonaws.com/role-arn': cluster.eksCluster.roleArn
                }
            },
            config: {
                outputs: `
                    [OUTPUT]
                        Name cloudwatch_logs
                        Match *
                        region ${aws.config.region}
                        log_group_name ${getResourceName('logs', 'eks-cluster')}
                        log_stream_prefix fluentbit-
                        auto_create_group true
                `,
                filters: `
                    [FILTER]
                        Name kubernetes
                        Match kube.*
                        Merge_Log On
                        Keep_Log Off
                        K8S-Logging.Parser On
                        K8S-Logging.Exclude Off
                `
            },
            tolerations: [
                {
                    key: 'dedicated',
                    operator: 'Equal',
                    value: 'system',
                    effect: 'NoSchedule'
                }
            ],
            nodeSelector: {
                'node-type': 'system'
            }
        }
    }, { provider: k8sProvider });
    
    return fluentBit;
}

/**
 * Sets up monitoring for the EKS cluster
 * 
 * @param cluster EKS cluster to set up monitoring for
 * @param options Additional options for monitoring configuration
 * @returns Monitoring configuration
 */
export function setupClusterMonitoring(
    cluster: eks.Cluster,
    options: AwsResourceOptions = {}
): k8s.helm.v3.Release {
    const resourceTags = { ...tags, ...(options.tags || {}) };
    
    // Create Kubernetes provider using the cluster's kubeconfig
    const k8sProvider = new k8s.Provider('k8s-monitoring-provider', {
        kubeconfig: cluster.kubeconfig.apply(JSON.stringify),
    });
    
    // Deploy Prometheus and Grafana stack
    const promStackName = getResourceName('monitoring', 'kube-prometheus-stack');
    const promStack = new k8s.helm.v3.Release(promStackName, {
        chart: 'kube-prometheus-stack',
        version: '45.0.0', // Use specific chart version for stability
        repositoryOpts: {
            repo: 'https://prometheus-community.github.io/helm-charts'
        },
        namespace: 'monitoring',
        createNamespace: true,
        values: {
            // Configure Prometheus
            prometheus: {
                prometheusSpec: {
                    storageSpec: {
                        volumeClaimTemplate: {
                            spec: {
                                storageClassName: 'gp2',
                                accessModes: ['ReadWriteOnce'],
                                resources: {
                                    requests: {
                                        storage: '50Gi'
                                    }
                                }
                            }
                        }
                    },
                    retention: '7d',
                    resources: {
                        requests: {
                            cpu: '500m',
                            memory: '1Gi'
                        },
                        limits: {
                            cpu: '1000m',
                            memory: '2Gi'
                        }
                    },
                    tolerations: [
                        {
                            key: 'dedicated',
                            operator: 'Equal',
                            value: 'system',
                            effect: 'NoSchedule'
                        }
                    ],
                    nodeSelector: {
                        'node-type': 'system'
                    }
                }
            },
            // Configure Grafana
            grafana: {
                adminPassword: 'prom-operator', // In production, use a secret or parameter
                persistence: {
                    enabled: true,
                    storageClassName: 'gp2',
                    size: '10Gi'
                },
                resources: {
                    requests: {
                        cpu: '200m',
                        memory: '256Mi'
                    },
                    limits: {
                        cpu: '500m',
                        memory: '512Mi'
                    }
                },
                tolerations: [
                    {
                        key: 'dedicated',
                        operator: 'Equal',
                        value: 'system',
                        effect: 'NoSchedule'
                    }
                ],
                nodeSelector: {
                    'node-type': 'system'
                },
                // Add default dashboards
                dashboardProviders: {
                    dashboardproviders: {
                        apiVersion: 1,
                        providers: [
                            {
                                name: 'default',
                                orgId: 1,
                                folder: '',
                                type: 'file',
                                disableDeletion: false,
                                editable: true,
                                options: {
                                    path: '/var/lib/grafana/dashboards/default'
                                }
                            }
                        ]
                    }
                }
            },
            // Configure Alert Manager
            alertmanager: {
                alertmanagerSpec: {
                    resources: {
                        requests: {
                            cpu: '100m',
                            memory: '128Mi'
                        },
                        limits: {
                            cpu: '200m',
                            memory: '256Mi'
                        }
                    },
                    tolerations: [
                        {
                            key: 'dedicated',
                            operator: 'Equal',
                            value: 'system',
                            effect: 'NoSchedule'
                        }
                    ],
                    nodeSelector: {
                        'node-type': 'system'
                    }
                }
            },
            // Deploy node exporter
            nodeExporter: {
                enabled: true
            },
            // Deploy kube state metrics
            kubeStateMetrics: {
                enabled: true
            }
        }
    }, { provider: k8sProvider });
    
    return promStack;
}

/**
 * Generates a kubeconfig for accessing the EKS cluster
 * 
 * @param cluster EKS cluster to generate kubeconfig for
 * @returns Kubeconfig content as a string
 */
export function getKubeconfig(cluster: eks.Cluster): pulumi.Output<string> {
    return cluster.kubeconfig;
}