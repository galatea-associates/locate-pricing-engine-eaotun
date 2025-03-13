# Contributing to the Borrow Rate & Locate Fee Pricing Engine

## Introduction

Thank you for considering contributing to the Borrow Rate & Locate Fee Pricing Engine. This document provides guidelines and instructions for contributing to this project.

As a financial system handling critical calculations for securities lending, we maintain high standards for code quality, accuracy, and security. All contributions must adhere to these standards to ensure the reliability and integrity of the system.

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing to understand our community standards and expectations.

## Getting Started

### Prerequisites

Before you begin contributing, ensure you have the following installed:

- Docker (24.0+)
- Docker Compose (1.29.2+)
- Python (3.11+)
- Git

### Setting Up the Development Environment

Follow the detailed instructions in [docs/development/setup.md](docs/development/setup.md) to set up your local development environment. This includes:

1. Cloning the repository
2. Configuring environment variables
3. Starting the Docker environment
4. Running database migrations
5. Seeding test data

## Development Workflow

### Branching Strategy

- The `main` branch contains the latest stable code
- Create feature branches from `main` for all changes
- Use the following naming convention for branches:
  - `feature/short-description` for new features
  - `bugfix/short-description` for bug fixes
  - `hotfix/short-description` for critical fixes
  - `docs/short-description` for documentation changes

### Development Process

1. Create a new branch from `main`
2. Make your changes following the coding standards
3. Write or update tests to cover your changes
4. Ensure all tests pass locally
5. Update documentation as needed
6. Commit your changes with clear, descriptive commit messages
7. Push your branch to GitHub
8. Create a pull request

## Coding Standards

All contributions must adhere to the project's coding standards. Please review [docs/development/coding-standards.md](docs/development/coding-standards.md) for detailed guidelines on:

- Python and TypeScript style guides
- Documentation requirements
- Testing requirements
- API design principles
- Security best practices

### Key Requirements

- **Code Coverage**: 100% for core calculation logic, ≥90% overall
- **Documentation**: All public functions, classes, and modules must be documented
- **Type Hints**: All Python code must use type hints
- **Tests**: All code must have corresponding tests
- **Security**: All code must follow security best practices
- **Performance**: Critical paths must meet performance requirements

## Testing

### Running Tests

All code changes must be accompanied by appropriate tests. To run the test suite:

```bash
# Run unit tests
docker-compose exec api pytest

# Run with coverage report
docker-compose exec api pytest --cov=src/backend --cov-report=term-missing
```

### Test Types

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete system flows
- **Performance Tests**: Test system under load

Ensure your changes include tests for all applicable test types.

## Pull Request Process

### Creating a Pull Request

1. Ensure your code meets all coding standards and passes all tests
2. Update the documentation to reflect any changes
3. Create a pull request against the `main` branch
4. Fill out the pull request template completely
5. Request review from appropriate team members

### Pull Request Requirements

All pull requests must:

- Address a specific issue or implement a specific feature
- Include comprehensive tests
- Pass all CI checks
- Include updated documentation
- Follow the pull request template
- Be reviewed by at least one maintainer

### Review Process

1. Automated CI checks will run on your pull request
2. Maintainers will review your code for:
   - Adherence to coding standards
   - Test coverage and quality
   - Documentation completeness
   - Security considerations
   - Performance implications
3. Address any feedback from reviewers
4. Once approved, a maintainer will merge your pull request

## Financial Calculation Changes

Changes to financial calculation logic require special attention due to the critical nature of these functions in a securities lending system.

### Requirements for Calculation Changes

- Provide detailed documentation of the formula changes
- Include validation against known test cases
- Consider all edge cases and document them
- Ensure 100% test coverage of calculation logic
- Include performance benchmarks for critical calculations
- Document any potential impact on existing calculations

### Validation Process

Changes to financial calculations will undergo additional review by domain experts to ensure accuracy and compliance with financial regulations.

## Reporting Issues

### Bug Reports

When reporting bugs, please include:

- A clear and descriptive title
- Detailed steps to reproduce the issue
- Expected behavior and actual behavior
- System information (OS, browser, etc.)
- Any relevant logs or error messages

### Feature Requests

When requesting features, please include:

- A clear and descriptive title
- Detailed description of the proposed feature
- Rationale for adding the feature
- Any relevant examples or use cases

## Documentation

Documentation is a critical part of this project. All code changes should include updates to relevant documentation.

### Documentation Types

- **Code Documentation**: Docstrings, comments, and type hints
- **API Documentation**: OpenAPI specifications and examples
- **User Documentation**: README, setup guides, and usage examples
- **Architecture Documentation**: System design and component interactions

### Documentation Standards

- Use clear, concise language
- Include examples for complex functionality
- Keep documentation up to date with code changes
- Follow the project's documentation style guide

## Versioning

This project follows [Semantic Versioning](https://semver.org/).

- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality in a backward-compatible manner
- **PATCH** version for backward-compatible bug fixes

All changes should indicate the appropriate version bump based on the nature of the changes.

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project. See the [LICENSE](LICENSE) file for details.

## Contact

If you have questions about contributing, please contact the project maintainers.