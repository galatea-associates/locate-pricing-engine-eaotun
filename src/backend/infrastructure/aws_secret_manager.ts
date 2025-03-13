/**
 * AWS Secrets Manager utilities for the Borrow Rate & Locate Fee Pricing Engine.
 * This module provides functionality for securely managing sensitive information
 * such as database credentials, API keys, and external service credentials.
 */

import * as aws from '@pulumi/aws'; // @pulumi/aws v5.0.0
import * as pulumi from '@pulumi/pulumi'; // @pulumi/pulumi v3.0.0
import * as random from '@pulumi/random'; // @pulumi/random v4.0.0
import { 
    configureAwsProvider, 
    getResourceName, 
    getDefaultTags, 
    createKmsKey, 
    AwsResourceOptions 
} from './aws';

// Global configuration
const config = new pulumi.Config();
const stackName = pulumi.getStack();
const secretsConfig = new pulumi.Config('secrets');
const defaultRotationDays = 90; // Default rotation period of 90 days

/**
 * Interface defining options for secret creation
 */
export interface SecretOptions extends AwsResourceOptions {
    /** Description of the secret */
    description?: string;
    /** KMS key ID to use for encryption */
    kmsKeyId?: string;
    /** Whether to enable automatic rotation */
    enableRotation?: boolean;
    /** Number of days between rotations */
    rotationDays?: number;
    /** Resource-based policy for the secret */
    resourcePolicy?: aws.secretsmanager.SecretPolicyArgs;
}

/**
 * Interface defining database credentials structure
 */
export interface DatabaseCredentials {
    /** Database username */
    username: string;
    /** Database password */
    password: string;
    /** Database engine (postgres, mysql, etc.) */
    engine: string;
    /** Database hostname */
    host: string;
    /** Database port */
    port: number;
    /** Database name */
    dbname: string;
    /** RDS instance identifier (optional) */
    dbInstanceIdentifier?: string;
}

/**
 * Interface defining options for secret rotation
 */
export interface RotationOptions {
    /** Whether rotation is enabled */
    enabled: boolean;
    /** Number of days between rotations */
    rotationDays?: number;
    /** Cron expression for rotation schedule */
    rotationSchedule?: string;
    /** Type of rotation (simple, lambda, etc.) */
    rotationType?: string;
    /** Additional parameters for rotation */
    rotationParameters?: {
        [key: string]: any;
    };
}

/**
 * Interface defining options for password generation
 */
export interface PasswordOptions {
    /** Length of the password */
    length?: number;
    /** Whether to include special characters */
    includeSpecial?: boolean;
    /** Whether to include numbers */
    includeNumbers?: boolean;
    /** Whether to include uppercase letters */
    includeUppercase?: boolean;
    /** Whether to include lowercase letters */
    includeLowercase?: boolean;
    /** Override the set of special characters to use */
    overrideSpecial?: string[];
}

/**
 * Creates a new secret in AWS Secrets Manager with appropriate tags and encryption
 * 
 * @param name Name of the secret
 * @param secretValue Value to store in the secret (string or object)
 * @param options Additional options for the secret
 * @returns Created secret resource
 */
export function createSecret(
    name: string,
    secretValue: string | object,
    options: SecretOptions = {}
): aws.secretsmanager.Secret {
    // Generate standardized resource name
    const secretName = getResourceName('secret', name);
    
    // Create KMS key for encryption if not provided
    const kmsKey = options.kmsKeyId 
        ? options.kmsKeyId 
        : createKmsKey(`${name}-secret-key`, {
            description: `KMS key for encrypting ${name} secret`,
            enableKeyRotation: true,
            tags: options.tags,
        });
    
    const kmsKeyId = options.kmsKeyId || kmsKey.keyId;
    
    // Convert object to JSON string if needed
    const secretString = typeof secretValue === 'object' 
        ? JSON.stringify(secretValue) 
        : secretValue;
    
    // Create the secret
    const secret = new aws.secretsmanager.Secret(secretName, {
        name: secretName,
        description: options.description || `Secret for ${name}`,
        kmsKeyId: kmsKeyId,
        tags: getDefaultTags(options.tags),
    });
    
    // Create the secret version with the actual value
    const secretVersion = new aws.secretsmanager.SecretVersion(`${secretName}-version`, {
        secretId: secret.id,
        secretString: secretString,
    });
    
    // Apply resource policy if provided
    if (options.resourcePolicy) {
        new aws.secretsmanager.SecretPolicy(`${secretName}-policy`, {
            secretArn: secret.arn,
            policy: options.resourcePolicy.policy,
        });
    }
    
    // Configure rotation if enabled
    if (options.enableRotation) {
        configureSecretRotation(secret, {
            enabled: true,
            rotationDays: options.rotationDays || defaultRotationDays,
        });
    }
    
    return secret;
}

/**
 * Creates a secret specifically for database credentials
 * 
 * @param name Name of the database
 * @param credentials Database connection credentials
 * @param options Additional options for the secret
 * @returns Created database secret with ARN and credentials
 */
export function createDatabaseSecret(
    name: string,
    credentials: DatabaseCredentials,
    options: SecretOptions = {}
): aws.secretsmanager.Secret {
    // Generate standardized name for the database secret
    const dbSecretName = getResourceName('db', name);
    
    // Format the credentials object according to AWS RDS requirements
    const formattedCredentials = {
        username: credentials.username,
        password: credentials.password,
        engine: credentials.engine,
        host: credentials.host,
        port: credentials.port,
        dbname: credentials.dbname,
        dbInstanceIdentifier: credentials.dbInstanceIdentifier,
    };
    
    // Enable automatic rotation by default for database credentials
    const enableRotation = options.enableRotation !== false;
    
    // Create the secret
    const secret = createSecret(dbSecretName, formattedCredentials, {
        description: options.description || `Database credentials for ${name}`,
        kmsKeyId: options.kmsKeyId,
        enableRotation: enableRotation,
        rotationDays: options.rotationDays || defaultRotationDays,
        tags: {
            ...options.tags,
            DatabaseName: credentials.dbname,
            DatabaseEngine: credentials.engine,
        },
    });
    
    // Create a resource-based policy for the secret to allow RDS access
    if (credentials.dbInstanceIdentifier) {
        const resourcePolicy = new aws.secretsmanager.SecretPolicy(`${dbSecretName}-policy`, {
            secretArn: secret.arn,
            policy: pulumi.all([secret.arn]).apply(([arn]) => JSON.stringify({
                Version: "2012-10-17",
                Statement: [
                    {
                        Sid: "AllowRDSToUseSecret",
                        Effect: "Allow",
                        Principal: {
                            Service: "rds.amazonaws.com"
                        },
                        Action: [
                            "secretsmanager:GetSecretValue",
                            "secretsmanager:DescribeSecret"
                        ],
                        Resource: arn
                    }
                ]
            })),
        });
    }
    
    return secret;
}

/**
 * Creates a secret for storing API keys for external services
 * 
 * @param name Name identifier for the API keys
 * @param apiKeys Object containing API keys for different services
 * @param options Additional options for the secret
 * @returns Created API key secret
 */
export function createApiKeySecret(
    name: string,
    apiKeys: { [service: string]: string },
    options: SecretOptions = {}
): aws.secretsmanager.Secret {
    // Generate standardized name for the API key secret
    const apiKeySecretName = getResourceName('apikey', name);
    
    // Create the secret with API keys
    const secret = createSecret(apiKeySecretName, apiKeys, {
        description: options.description || `API keys for ${name} services`,
        enableRotation: options.enableRotation || false, // Manual rotation by default for API keys
        rotationDays: options.rotationDays || defaultRotationDays,
        kmsKeyId: options.kmsKeyId,
        tags: {
            ...options.tags,
            SecretType: 'ApiKeys',
            Services: Object.keys(apiKeys).join(','),
        },
    });
    
    // Set up notification for manual rotation reminder
    if (!options.enableRotation) {
        const rotationDays = options.rotationDays || defaultRotationDays;
        const reminderDate = new Date();
        reminderDate.setDate(reminderDate.getDate() + rotationDays);
        
        // Create a CloudWatch Events rule to notify about key rotation
        const reminderRule = new aws.cloudwatch.EventRule(`${apiKeySecretName}-reminder`, {
            description: `Reminder to rotate API keys for ${name}`,
            scheduleExpression: `cron(0 10 ${reminderDate.getDate()} ${reminderDate.getMonth() + 1} ? ${reminderDate.getFullYear()})`,
        });
        
        // Optional: Set up an SNS topic and subscription for the reminder
        // This would require additional code to create SNS resources
    }
    
    return secret;
}

/**
 * Configures automatic rotation for a secret using AWS Lambda
 * 
 * @param secret The secret to configure rotation for
 * @param rotationOptions Options for rotation configuration
 * @returns Rotation configuration including Lambda function and schedule
 */
export function configureSecretRotation(
    secret: aws.secretsmanager.Secret,
    rotationOptions: RotationOptions
): any {
    if (!rotationOptions.enabled) {
        return null;
    }
    
    // Default rotation period is 90 days
    const rotationDays = rotationOptions.rotationDays || defaultRotationDays;
    
    // Default rotation schedule is at 3:00 AM UTC
    const rotationSchedule = rotationOptions.rotationSchedule || `cron(0 3 ? * SAT *)`;
    
    // Create IAM role for the rotation Lambda
    const lambdaRole = new aws.iam.Role(`${secret.name}-rotation-role`, {
        assumeRolePolicy: JSON.stringify({
            Version: "2012-10-17",
            Statement: [{
                Action: "sts:AssumeRole",
                Effect: "Allow",
                Principal: {
                    Service: "lambda.amazonaws.com",
                },
            }],
        }),
    });
    
    // Attach necessary policies to the rotation Lambda role
    new aws.iam.RolePolicyAttachment(`${secret.name}-rotation-sm-policy`, {
        role: lambdaRole.name,
        policyArn: "arn:aws:iam::aws:policy/SecretsManagerReadWrite",
    });
    
    new aws.iam.RolePolicyAttachment(`${secret.name}-rotation-lambda-policy`, {
        role: lambdaRole.name,
        policyArn: "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    });
    
    // Create custom policy for specific resources if needed
    const rotationType = rotationOptions.rotationType || "generic";
    
    // Determine Lambda function code based on rotation type
    let handlerCode = `
        exports.handler = async (event, context) => {
            console.log('Secret rotation triggered:', JSON.stringify(event));
            // Implement rotation logic here based on rotation type
            return { statusCode: 200, body: 'Rotation successful' };
        }
    `;
    
    // Create Lambda function for rotation
    const rotationLambda = new aws.lambda.Function(`${secret.name}-rotation-lambda`, {
        runtime: "nodejs16.x",
        handler: "index.handler",
        role: lambdaRole.arn,
        code: new pulumi.asset.AssetArchive({
            "index.js": new pulumi.asset.StringAsset(handlerCode),
        }),
        environment: {
            variables: {
                SECRET_ARN: secret.arn,
                ROTATION_TYPE: rotationType,
                ...rotationOptions.rotationParameters,
            },
        },
        timeout: 60,
    });
    
    // Configure rotation schedule
    const rotationScheduling = new aws.secretsmanager.SecretRotation(`${secret.name}-rotation`, {
        secretId: secret.id,
        rotationLambdaArn: rotationLambda.arn,
        rotationRules: {
            automaticallyAfterDays: rotationDays,
        },
    });
    
    return {
        lambda: rotationLambda,
        schedule: rotationScheduling,
    };
}

/**
 * Generates a secure random password for use in secrets
 * 
 * @param options Password generation options
 * @returns Generated password
 */
export function generateRandomPassword(
    options: PasswordOptions = {}
): pulumi.Output<string> {
    // Set default options if not specified
    const length = options.length || 32;
    const includeSpecial = options.includeSpecial !== false;
    const includeNumbers = options.includeNumbers !== false;
    const includeUppercase = options.includeUppercase !== false;
    const includeLowercase = options.includeLowercase !== false;
    const overrideSpecial = options.overrideSpecial?.join('') || "!@#$%^&*()_+[]{}|;:,.<>?";
    
    // Create a random password resource
    const password = new random.RandomPassword(`random-password`, {
        length: length,
        special: includeSpecial,
        numeric: includeNumbers,
        upper: includeUppercase,
        lower: includeLowercase,
        overrideSpecial: overrideSpecial,
        // Ensure minimum requirements are met
        minLower: includeLowercase ? 1 : 0,
        minUpper: includeUppercase ? 1 : 0,
        minNumeric: includeNumbers ? 1 : 0,
        minSpecial: includeSpecial ? 1 : 0,
    });
    
    return password.result;
}

/**
 * Retrieves a secret value from AWS Secrets Manager
 * 
 * @param secretId Secret ID or ARN
 * @returns Secret value as a string
 */
export function getSecretValue(
    secretId: string
): pulumi.Output<string> {
    // Use aws.secretsmanager.getSecretVersion to retrieve the secret
    return pulumi.output(aws.secretsmanager.getSecretVersion({
        secretId: secretId,
    })).apply(secret => secret.secretString);
}