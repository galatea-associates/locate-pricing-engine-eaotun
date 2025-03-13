{
  "name": "borrow-rate-locate-fee-pricing-engine",
  "version": "1.0.0",
  "description": "A specialized financial system designed to dynamically calculate short-selling costs for brokerages and financial institutions",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "engines": {
    "node": ">=18.0.0",
    "npm": ">=8.0.0"
  },
  "scripts": {
    "build": "tsc",
    "watch": "tsc -w",
    "test": "jest",
    "test:coverage": "jest --coverage",
    "lint": "eslint . --ext .ts",
    "lint:fix": "eslint . --ext .ts --fix",
    "format": "prettier --write \"**/*.{ts,js,json}\"",
    "docs": "typedoc --out docs src",
    "clean": "rimraf dist coverage docs",
    "prepare": "husky install",
    "infra:validate": "ts-node scripts/validate-infra.ts",
    "infra:plan": "ts-node scripts/plan-infra.ts",
    "infra:apply": "ts-node scripts/apply-infra.ts",
    "infra:destroy": "ts-node scripts/destroy-infra.ts",
    "db:migrate": "ts-node scripts/db-migrate.ts",
    "db:seed": "ts-node scripts/db-seed.ts"
  },
  "dependencies": {
    "@aws-sdk/client-cloudwatch": "^3.433.0",
    "@aws-sdk/client-dynamodb": "^3.433.0",
    "@aws-sdk/client-ec2": "^3.433.0",
    "@aws-sdk/client-ecs": "^3.433.0",
    "@aws-sdk/client-eks": "^3.433.0",
    "@aws-sdk/client-elasticache": "^3.433.0",
    "@aws-sdk/client-rds": "^3.433.0",
    "@aws-sdk/client-s3": "^3.433.0",
    "@aws-sdk/client-secrets-manager": "^3.433.0",
    "@pulumi/aws": "^6.4.0",
    "@pulumi/awsx": "^2.0.2",
    "@pulumi/pulumi": "^3.90.1",
    "axios": "^1.5.1",
    "cdktf": "^0.18.0",
    "constructs": "^10.3.0",
    "datadog-metrics": "^1.0.0",
    "date-fns": "^2.30.0",
    "decimal.js": "^10.4.3",
    "dotenv": "^16.3.1",
    "helmet": "^7.0.0",
    "ioredis": "^5.3.2",
    "joi": "^17.11.0",
    "lodash": "^4.17.21",
    "winston": "^3.11.0"
  },
  "devDependencies": {
    "@types/jest": "^29.5.6",
    "@types/lodash": "^4.14.200",
    "@types/node": "^20.8.9",
    "@typescript-eslint/eslint-plugin": "^6.9.0",
    "@typescript-eslint/parser": "^6.9.0",
    "eslint": "^8.52.0",
    "eslint-config-prettier": "^9.0.0",
    "eslint-plugin-import": "^2.29.0",
    "eslint-plugin-prettier": "^5.0.1",
    "husky": "^8.0.3",
    "jest": "^29.7.0",
    "lint-staged": "^15.0.2",
    "prettier": "^3.0.3",
    "rimraf": "^5.0.5",
    "ts-jest": "^29.1.1",
    "ts-node": "^10.9.1",
    "typedoc": "^0.25.2",
    "typescript": "^5.2.2"
  },
  "lint-staged": {
    "*.{ts,js}": [
      "eslint --fix",
      "prettier --write"
    ],
    "*.{json,md}": [
      "prettier --write"
    ]
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/organization/borrow-rate-locate-fee-pricing-engine.git"
  },
  "keywords": [
    "finance",
    "brokerage",
    "securities-lending",
    "short-selling",
    "pricing",
    "locate-fee",
    "borrow-rate"
  ],
  "author": "Financial Engineering Team",
  "license": "UNLICENSED",
  "private": true,
  "bugs": {
    "url": "https://github.com/organization/borrow-rate-locate-fee-pricing-engine/issues"
  },
  "homepage": "https://github.com/organization/borrow-rate-locate-fee-pricing-engine#readme"
}