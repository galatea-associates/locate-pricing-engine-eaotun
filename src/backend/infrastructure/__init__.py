"""
Infrastructure Package for Borrow Rate & Locate Fee Pricing Engine

This package contains infrastructure-as-code (IaC) definitions and utilities
for provisioning and managing AWS cloud resources required by the Borrow Rate &
Locate Fee Pricing Engine. It serves as a bridge between Python application code
and TypeScript/Terraform infrastructure definitions.

The infrastructure is designed with the following key principles:
- Modular Terraform configurations with versioned modules
- AWS as the primary cloud provider for financial service compliance
- Multi-AZ deployment for high availability and fault tolerance
- Infrastructure as Code for repeatable, version-controlled deployments

Core AWS services utilized include:
- Amazon EKS for container orchestration
- Amazon RDS for PostgreSQL for primary database
- Amazon ElastiCache for Redis caching layer
- Amazon ECR for container registry
- AWS Secrets Manager for credentials management

This module is part of the backend services for the Borrow Rate & Locate Fee
Pricing Engine, providing automated infrastructure provisioning and management.
"""

__version__ = "1.0.0"
__author__ = "Borrow Rate & Locate Fee Pricing Engine Team"