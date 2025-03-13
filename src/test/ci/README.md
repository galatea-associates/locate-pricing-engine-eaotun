# Continuous Integration (CI) Documentation

This document describes the Continuous Integration (CI) configuration and workflows used in the Borrow Rate & Locate Fee Pricing Engine testing framework.

## Introduction

The Borrow Rate & Locate Fee Pricing Engine employs a comprehensive CI/CD approach to ensure the highest levels of quality, reliability, and security. As a financial system handling critical short-selling cost calculations, automated testing is essential to:

- Validate calculation accuracy for all fee formulas
- Ensure API reliability and performance under various loads
- Maintain security standards and prevent vulnerabilities
- Verify compliance with financial regulations
- Provide audit trails of all system changes

Our CI workflows automatically execute tests at various stages of development, providing rapid feedback to developers and ensuring only high-quality code reaches production.

## CI Directory Structure

The test/ci directory contains all CI-related configuration and supporting files:

```
src/test/ci/
├── README.md                   # This documentation file
├── github_actions/             # GitHub Actions workflow definitions
│   ├── integration_test_workflow.yml
│   ├── e2e_test_workflow.yml
│   ├── performance_test_workflow.yml
│   ├── security_scan_workflow.yml
│   ├── compliance_test_workflow.yml
│   └── nightly_test_workflow.yml
├── scripts/                    # Supporting scripts for CI workflows
│   ├── setup_test_env.sh       # Environment setup script
│   ├── run_mock_servers.py     # Script to start mock external APIs
│   ├── generate_test_report.py # Test report generation utility
│   └── notify.py               # Notification utility
└── config/                     # Configuration files for CI environments
    ├── test_env.json           # Test environment configuration
    ├── staging_env.json        # Staging environment configuration
    ├── performance_env.json    # Performance environment configuration
    └── compliance_env.json     # Compliance environment configuration
```

### GitHub Actions Workflows

The `github_actions` directory contains workflow definitions that automate testing across different dimensions of the system. Each workflow is designed to address specific quality aspects and is triggered at appropriate stages of the development process.

### Supporting Scripts

The `scripts` directory contains utility scripts that support the CI workflows, handling tasks such as environment setup, test execution, report generation, and notifications.

## Workflow Descriptions

### Integration Test Workflow

**File**: `github_actions/integration_test_workflow.yml`

This workflow tests the interaction between different components of the system, ensuring they function correctly together.

**Triggers**:
- Pull requests to main/develop branches
- Manual workflow dispatch

**Key Steps**:
1. Set up test environment with mocked dependencies
2. Start mock servers for SecLend API, Market Volatility API, and Event Calendar API
3. Execute integration test suite
4. Generate test reports in JUnit and HTML formats
5. Upload test artifacts for review
6. Notify team of test results

**Example Usage**:

```yaml
name: Manual Integration Test Run
on:
  workflow_dispatch:
    inputs:
      test_scope:
        description: 'Test scope (full, smoke, critical)'
        default: 'full'
```

### End-to-End Test Workflow

**File**: `github_actions/e2e_test_workflow.yml`

This workflow verifies the entire system's functionality from API requests to calculation results, ensuring the complete user journey works as expected.

**Triggers**:
- Pull requests to main branch
- After successful integration tests
- Manual workflow dispatch

**Key Steps**:
1. Deploy complete test environment with all services
2. Configure external sandbox APIs
3. Execute E2E test suite using actual API calls
4. Validate calculation results against known test cases
5. Generate comprehensive test report
6. Capture logs and diagnostics on failure
7. Clean up test environment

**Example Usage**:

```yaml
name: E2E Tests on API Changes
on:
  pull_request:
    paths:
      - 'src/api/**'
      - 'src/calculation/**'
```

### Performance Test Workflow

**File**: `github_actions/performance_test_workflow.yml`

This workflow runs performance tests to ensure the system meets its performance requirements, handling expected loads with acceptable response times.

**Triggers**:
- Nightly schedule (midnight)
- Manual workflow dispatch

**Key Steps**:
1. Set up performance test environment with appropriate resources
2. Run load tests simulating normal operations (1000 req/sec)
3. Run stress tests pushing beyond expected capacity (2000+ req/sec)
4. Run spike tests simulating sudden traffic increases
5. Run endurance tests for sustained load over time
6. Analyze results against performance SLAs
7. Generate performance reports with trends
8. Trigger alerts if performance degrades from baseline

**Resource Requirements**:
- High-capacity runners (16+ cores)
- 32+ GB RAM
- Separate database instance with monitoring

### Security Scan Workflow

**File**: `github_actions/security_scan_workflow.yml`

This workflow scans the codebase, dependencies, and container images for security vulnerabilities, ensuring the system remains secure.

**Triggers**:
- Pull requests to main/develop branches
- Push to main/develop branches
- Weekly schedule (Sunday midnight)
- Manual workflow dispatch

**Key Steps**:
1. Dependency vulnerability scanning with Snyk
2. SAST (Static Application Security Testing) with SonarQube
3. Container image scanning with Trivy
4. Secret detection with GitGuardian
5. OWASP ZAP API security testing
6. Generate comprehensive security report
7. Block PR if critical vulnerabilities found

**Security Gate Criteria**:
- No critical vulnerabilities in dependencies
- No high or critical code vulnerabilities
- No secrets or credentials in codebase
- No container image vulnerabilities with CVSS score ≥ 7.0

### Compliance Test Workflow

**File**: `github_actions/compliance_test_workflow.yml`

This workflow verifies that the system meets regulatory requirements and financial calculation accuracy standards.

**Triggers**:
- Weekly schedule (Monday midnight)
- Manual workflow dispatch
- Push to main branch affecting calculation or audit services

**Key Steps**:
1. Run audit trail tests verifying complete logging
2. Validate calculation accuracy against reference implementation
3. Test data retention policies and mechanisms
4. Verify API documentation completeness
5. Ensure rate calculations conform to financial standards
6. Generate compliance report
7. Store evidence for regulatory reviews

**Compliance Areas Covered**:
- SEC Rule 17a-4 (record keeping)
- SOX controls
- GDPR/CCPA data handling
- Financial calculation accuracy standards

### Nightly Test Workflow

**File**: `github_actions/nightly_test_workflow.yml`

This comprehensive workflow runs all test types nightly to ensure the system maintains high quality between releases.

**Triggers**:
- Nightly schedule (midnight)
- Manual workflow dispatch

**Key Steps**:
1. Run integration tests
2. Run E2E tests
3. Run performance tests
4. Run security scans
5. Run compliance tests
6. Generate comprehensive test report
7. Send notifications with test summary

**Example Report**:
```
Nightly Test Summary (2023-10-15)
- Integration Tests: 245/245 passed
- E2E Tests: 120/122 passed (2 flaky tests identified)
- Performance: All metrics within SLA (98.5ms p95 response time)
- Security: 0 critical, 2 medium vulnerabilities
- Compliance: All checks passed

Detailed reports: https://github.com/org/repo/actions/runs/12345
```

## Environment Configuration

### Test Environment

The test environment is used for basic integration tests and provides lightweight mocked versions of external dependencies:

- Containerized services (API Gateway, Calculation Service, Data Service)
- In-memory databases and Redis
- Mock external APIs with predefined responses
- Configuration stored in `config/test_env.json`

### Staging Environment

The staging environment is a production-like environment used for E2E tests:

- Complete deployment of all services
- Dedicated databases with test data
- Sandbox versions of external APIs
- Configuration stored in `config/staging_env.json`

### Performance Environment

The performance environment is optimized for load testing:

- High-capacity instances for all services
- Performance-optimized database configuration
- Monitoring and metrics collection enabled
- Configuration stored in `config/performance_env.json`

### Compliance Environment

The compliance environment includes additional controls for regulatory testing:

- Complete audit logging enabled
- Extended data retention
- Strict security controls
- Reference implementation for calculation validation
- Configuration stored in `config/compliance_env.json`

## Secrets Management

### Required Secrets

The following secrets must be configured in GitHub repository settings for workflows to function properly:

| Secret Name | Description | Used By |
|-------------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key for infrastructure | All workflows |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for infrastructure | All workflows |
| `DATABASE_PASSWORD` | Test database password | All workflows |
| `SECLEND_API_KEY` | API key for SecLend sandbox | E2E, Compliance workflows |
| `MARKET_API_KEY` | API key for Market Data sandbox | E2E, Compliance workflows |
| `SNYK_TOKEN` | Token for Snyk vulnerability scanning | Security workflow |
| `SONAR_TOKEN` | Token for SonarQube analysis | Security workflow |
| `SLACK_WEBHOOK_URL` | Webhook for Slack notifications | All workflows |

### Secret Rotation

Secrets used in CI environments are automatically rotated every 90 days using the following process:

1. New secrets are generated and added to GitHub repository settings
2. Workflows are updated to use new secrets
3. Old secrets are removed after successful workflow runs

The secrets rotation schedule is tracked in the team's security calendar.

### Environment-Specific Secrets

Secrets are scoped to specific environments using GitHub Environments feature:

- `test` environment - basic credentials for integration tests
- `staging` environment - sandbox API keys for E2E tests
- `performance` environment - high-capacity resource credentials
- `compliance` environment - full access credentials with audit capabilities

## Test Reporting

### Report Generation

Test reports are generated in multiple formats:

- JUnit XML for CI integration
- HTML reports for human readability
- JSON for programmatic analysis
- Markdown summaries for GitHub PR comments

Reports include:
- Test execution summary (pass/fail counts)
- Detailed test results with failure information
- Test execution time and performance metrics
- Code coverage for applicable tests
- Screenshots or API responses for failed tests

### Artifact Storage

Test artifacts are stored in GitHub Actions for 30 days and include:

- Test reports in all formats
- Log files from test execution
- Performance test results
- Security scan reports
- Screenshots or API responses from failures

For compliance purposes, reports are also archived to a secure S3 bucket with a 7-year retention period.

### Notifications

Test results trigger notifications through multiple channels:

- GitHub PR checks for code reviews
- Slack notifications for failed workflows
- Email digests for nightly and weekly test runs
- PagerDuty alerts for critical failures in main branch

## Workflow Customization

### Adding New Workflows

To add a new GitHub Actions workflow:

1. Create a new YAML file in the `github_actions` directory
2. Follow the existing workflow structure for consistency
3. Document the workflow purpose, triggers, and steps in this README
4. Test the workflow using manual dispatch before committing
5. Add appropriate secrets and environment configurations

### Modifying Existing Workflows

When modifying existing workflows:

1. Test changes using a feature branch first
2. Use the workflow visualization in GitHub to validate the workflow structure
3. Update this README with any significant changes
4. Consider the impact on CI resources and execution time
5. Maintain or improve test coverage and quality gates

### Workflow Parameters

Most workflows support customization through workflow dispatch inputs:

```yaml
inputs:
  test_scope:
    description: 'Test scope (full, smoke, critical)'
    default: 'full'
  parallel_workers:
    description: 'Number of parallel test workers'
    default: '4'
  environment:
    description: 'Target environment'
    default: 'test'
```

Common configurable parameters include:
- Test scope or specific test suites
- Number of parallel workers
- Target environment
- Notification settings
- Debug level

## Troubleshooting

### Common Workflow Failures

| Issue | Cause | Solution |
|-------|-------|----------|
| External API Timeouts | Sandbox API limits or outages | Use mock APIs with `--mock` flag |
| Resource Exhaustion | Too many parallel tests | Reduce `parallel_workers` parameter |
| Database Connection Failures | Incorrect credentials | Verify database secrets are configured |
| Missing Secrets | Secrets not configured | Add required secrets to repository settings |
| Docker Build Failures | Base image changes | Update base image version in Dockerfile |

### Debugging Workflows

To debug workflow issues:

1. Enable debug logging by setting the `ACTIONS_RUNNER_DEBUG` and `ACTIONS_STEP_DEBUG` secrets to `true`
2. Use the "Re-run jobs" feature to retry specific failed jobs
3. Check the raw logs for detailed error information
4. Use the `tmate` action to get interactive shell access when needed:

```yaml
- name: Setup tmate session
  uses: mxschmitt/action-tmate@v3
  if: ${{ failure() }}
```

### Getting Help

For help with CI workflow issues:

- Check the CI documentation in this README
- Review the GitHub Actions documentation: https://docs.github.com/en/actions
- Contact the DevOps team in the #devops Slack channel
- Create an issue with the "ci" label in the project repository

## Best Practices

### Workflow Efficiency

To optimize workflow execution time and resource usage:

- Use matrix builds for parallel testing
- Implement test splitting for large test suites
- Use appropriate test scopes (smoke, critical, full)
- Cache dependencies between workflow runs
- Use dependency-based triggers to run only relevant tests

Example of efficient workflow configuration:

```yaml
strategy:
  matrix:
    shard: [1, 2, 3, 4]
  fail-fast: false

steps:
  - uses: actions/cache@v3
    with:
      path: ~/.cache/pip
      key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
  
  - name: Run tests
    run: python -m pytest tests/ --shard-id=${{ matrix.shard }} --shard-count=4
```

### Test Isolation

To ensure tests are isolated and don't interfere with each other:

- Use dedicated databases for each test run
- Reset state between tests
- Avoid shared resources between parallel test runs
- Use unique identifiers for test resources
- Implement proper cleanup in teardown phases

### Resource Management

For effective resource management in CI workflows:

- Use appropriate GitHub-hosted runner sizes based on needs
- Schedule resource-intensive workflows during off-hours
- Implement timeout limits for all workflow jobs
- Clean up resources after tests complete
- Monitor workflow run times and optimize long-running tests

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [Workflow Syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [GitHub Actions for Python](https://github.com/actions/setup-python)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [AWS CLI Configuration and Credential Files](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [Docker Documentation](https://docs.docker.com/)
- [SonarQube Documentation](https://docs.sonarqube.org/)
- [Snyk Documentation](https://docs.snyk.io/)