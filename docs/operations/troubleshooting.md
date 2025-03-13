{
  "name": "borrow-rate-locate-fee-pricing-engine",
  "version": "1.0.0",
  "description": "A specialized financial system designed to dynamically calculate short-selling costs for brokerages and financial institutions",
  "main": "dist/index.js",
  "private": true,
  "engines": {
    "node": ">=18.0.0",
    "npm": ">=8.0.0"
  },
  "scripts": {
    "build": "tsc",
    "lint": "eslint 'infrastructure/**/*.ts'",
    "test": "jest",
    "terraform:init": "cd infrastructure/terraform && terraform init",
    "terraform:plan": "cd infrastructure/terraform && terraform plan",
    "terraform:apply": "cd infrastructure/terraform && terraform apply",
    "terraform:destroy": "cd infrastructure/terraform && terraform destroy",
    "docker:build": "docker-compose build",
    "docker:up": "docker-compose up -d",
    "docker:down": "docker-compose down",
    "start:dev": "npm run docker:up && python -m uvicorn app.main:app --reload",
    "prepare": "husky install"
  },
  "dependencies": {
    "@aws-sdk/client-cloudwatch": "^3.433.0",
    "@aws-sdk/client-ec2": "^3.433.0",
    "@aws-sdk/client-ecr": "^3.433.0",
    "@aws-sdk/client-eks": "^3.433.0",
    "@aws-sdk/client-rds": "^3.433.0",
    "@aws-sdk/client-s3": "^3.433.0",
    "@aws-sdk/client-secrets-manager": "^3.433.0",
    "@kubernetes/client-node": "^0.18.1",
    "aws-cdk-lib": "^2.100.0",
    "constructs": "^10.3.0",
    "dotenv": "^16.3.1",
    "winston": "^3.11.0",
    "yaml": "^2.3.2"
  },
  "devDependencies": {
    "@types/jest": "^29.5.5",
    "@types/node": "^20.8.3",
    "@typescript-eslint/eslint-plugin": "^6.7.5",
    "@typescript-eslint/parser": "^6.7.5",
    "eslint": "^8.51.0",
    "eslint-config-prettier": "^9.0.0",
    "eslint-plugin-import": "^2.28.1",
    "eslint-plugin-prettier": "^5.0.0",
    "husky": "^8.0.3",
    "jest": "^29.7.0",
    "lint-staged": "^15.0.0",
    "prettier": "^3.0.3",
    "ts-jest": "^29.1.1",
    "ts-node": "^10.9.1",
    "typescript": "^5.2.2"
  },
  "lint-staged": {
    "*.ts": [
      "eslint --fix",
      "prettier --write"
    ]
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/organization/borrow-rate-locate-fee-pricing-engine.git"
  },
  "keywords": [
    "finance",
    "securities-lending",
    "borrow-rate",
    "locate-fee",
    "short-selling",
    "pricing-engine"
  ],
  "author": "Financial Engineering Team",
  "license": "UNLICENSED",
  "bugs": {
    "url": "https://github.com/organization/borrow-rate-locate-fee-pricing-engine/issues"
  },
  "homepage": "https://github.com/organization/borrow-rate-locate-fee-pricing-engine#readme"
}