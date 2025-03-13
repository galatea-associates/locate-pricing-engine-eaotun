# Pull Request

## Description

Please provide a clear and concise description of the changes introduced in this pull request. Include the purpose of the changes and how they address the requirements.

## Related Issues

Please link any related issues or requirements that this PR addresses.

Example: Resolves #123, Implements requirement F-001-RQ-002

## Type of Change

- [ ] New Feature (adds new functionality)
- [ ] Bug Fix (resolves an issue)
- [ ] Performance Improvement (improves system performance)
- [ ] Refactoring (code improvement with no functional change)
- [ ] Documentation (updates to documentation only)
- [ ] Test (adds or modifies tests)
- [ ] Infrastructure (changes to CI/CD or deployment)
- [ ] Security (addresses security concerns)
- [ ] Other (please describe)

## Components Affected

- [ ] API Gateway
- [ ] Calculation Service
- [ ] Data Service
- [ ] Cache Service
- [ ] Audit Service
- [ ] Database Models/Migrations
- [ ] External API Integration
- [ ] Authentication/Authorization
- [ ] Error Handling
- [ ] Documentation
- [ ] Infrastructure
- [ ] Tests
- [ ] Other (please specify)

## Financial Calculation Changes

_Complete this section if your changes involve financial calculations, otherwise delete it._

If this PR modifies any financial calculation logic, please provide:

- Description of the formula changes
- Validation approach used
- Expected impact on calculation results
- Any edge cases considered

## Testing

### Unit Tests

Describe the unit tests added or modified to verify these changes.

### Integration Tests

Describe any integration tests performed to verify these changes.

### Edge Cases

List any edge cases or special scenarios that were tested.

### Test Coverage

Confirm that test coverage meets or exceeds the required thresholds:
- Core calculation logic: 100%
- API endpoints: 95%
- Data access layer: 90%
- Overall coverage: ≥90%

## Performance Considerations

Describe any performance implications of these changes. Include benchmark results if applicable.

Confirm that the changes meet the performance requirements:
- API response time: <100ms (p95)
- Calculation time: <50ms
- Database query time: <30ms

## Security Considerations

Describe any security implications of these changes. Confirm that security best practices have been followed and that no new vulnerabilities have been introduced.

## Documentation Updates

Describe any updates made to documentation, including:

- Code comments and docstrings
- API documentation
- README or other markdown files
- Architecture diagrams

Confirm that all public functions, classes, and modules have appropriate documentation.

## Deployment Considerations

Describe any special considerations for deploying these changes, such as:

- Database migrations
- Configuration changes
- External service dependencies
- Backward compatibility concerns
- Rollback procedures

## Screenshots

_If applicable, add screenshots or diagrams to help explain your changes._

## Checklist

- [ ] My code follows the project's coding standards
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] I have updated the documentation accordingly
- [ ] My changes generate no new warnings or errors
- [ ] I have checked for potential performance impacts
- [ ] I have considered security implications
- [ ] I have added appropriate logging
- [ ] I have verified error handling
- [ ] I have reviewed my own code before requesting review

## Reviewer Notes

Any specific areas you'd like reviewers to focus on, or any particular concerns you'd like addressed during review.