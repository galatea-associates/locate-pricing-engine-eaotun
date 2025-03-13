# Coding Standards and Best Practices

## Introduction

This document outlines the coding standards and best practices for the Borrow Rate & Locate Fee Pricing Engine project. Adherence to these standards ensures code quality, maintainability, and consistency across the codebase. As a financial system handling critical calculations, our code must meet high standards for accuracy, performance, and security.

## General Principles

### Code Quality
- Write clean, readable, and maintainable code
- Follow the principle of least surprise
- Optimize for readability over cleverness
- Ensure code is testable and well-tested
- Prioritize correctness in financial calculations

### Security First
- Consider security implications in all code changes
- Validate all inputs, especially from external sources
- Follow the principle of least privilege
- Never store sensitive information in code
- Use secure coding practices to prevent common vulnerabilities

### Performance Considerations
- Write efficient code, especially for critical calculation paths
- Use appropriate data structures and algorithms
- Consider memory usage and allocation patterns
- Implement caching where appropriate
- Profile and optimize performance bottlenecks

### Consistency
- Follow established patterns and conventions
- Use consistent naming, formatting, and structure
- Maintain architectural consistency across components
- Ensure consistent error handling and logging
- Follow the same patterns for similar functionality

## Python Coding Standards

### Style Guide
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines
- Use 4 spaces for indentation (no tabs)
- Limit lines to 88 characters (compatible with Black formatter)
- Use snake_case for functions, methods, and variables
- Use PascalCase for classes
- Use UPPER_CASE for constants
- Group imports in the following order: standard library, third-party, local application

### Type Hints
- Use type hints for all function parameters and return values
- Use typing module for complex types (List, Dict, Optional, etc.)
- Use Union[Type1, Type2] for parameters that accept multiple types
- Use Optional[Type] for parameters that may be None
- Use Callable[[Param1Type, Param2Type], ReturnType] for function parameters
- Use TypeVar for generic types

```python
from typing import Dict, List, Optional, Union

def calculate_borrow_rate(
    ticker: str,
    volatility_index: float,
    event_risk: Optional[int] = None
) -> float:
    """Calculate the borrow rate for a security.
    
    Args:
        ticker: The stock ticker symbol
        volatility_index: Market volatility index value
        event_risk: Optional risk factor for upcoming events (0-10)
        
    Returns:
        The calculated borrow rate as a decimal percentage
    """
    # Implementation
```

### Docstrings
- Use Google-style docstrings for all modules, classes, and functions
- Include a brief description of the purpose
- Document all parameters with types and descriptions
- Document return values with types and descriptions
- Document exceptions that may be raised
- Include examples for complex functions
- Keep docstrings up to date with code changes

```python
def calculate_locate_fee(
    ticker: str,
    position_value: Decimal,
    loan_days: int,
    client_id: str
) -> Dict[str, Any]:
    """Calculate the total locate fee for borrowing securities.
    
    This function calculates the fee charged to clients for locating and
    borrowing securities for short-selling operations. It includes the
    base borrow cost, broker markup, and transaction fees.
    
    Args:
        ticker: The stock ticker symbol
        position_value: The total value of the position in USD
        loan_days: The duration of the loan in days
        client_id: The client identifier for fee structure
        
    Returns:
        A dictionary containing the total fee and breakdown:
        {
            "total_fee": Decimal,
            "breakdown": {
                "borrow_cost": Decimal,
                "markup": Decimal,
                "transaction_fees": Decimal
            },
            "borrow_rate_used": Decimal
        }
        
    Raises:
        ValidationError: If any parameters are invalid
        CalculationError: If an error occurs during calculation
        ExternalAPIError: If external data sources are unavailable
    
    Example:
        >>> calculate_locate_fee("AAPL", Decimal("100000"), 30, "client123")
        {
            "total_fee": Decimal("428.77"),
            "breakdown": {
                "borrow_cost": Decimal("383.56"),
                "markup": Decimal("19.18"),
                "transaction_fees": Decimal("26.03")
            },
            "borrow_rate_used": Decimal("0.047")
        }
    """
    # Implementation
```

### Error Handling
- Use custom exception classes for different error types
- Provide meaningful error messages with context
- Handle exceptions at the appropriate level
- Log exceptions with sufficient context for debugging
- Use specific exception types rather than catching Exception
- Include error codes for API error responses

```python
try:
    borrow_rate = get_borrow_rate(ticker)
    if not validate_borrow_rate(borrow_rate):
        raise ValidationException(
            param="borrow_rate",
            detail=f"Borrow rate {borrow_rate} is outside valid range"
        )
    # Continue with calculation
except ExternalAPIException as e:
    logger.error(f"External API error for ticker {ticker}: {str(e)}")
    # Use fallback mechanism
    borrow_rate = get_fallback_rate(ticker)
    # Continue with calculation using fallback
except ValidationException as e:
    logger.warning(f"Validation error: {str(e)}")
    # Re-raise for API error response
    raise
```

### Testing Requirements
- Write unit tests for all functions and methods
- Achieve 100% code coverage for core calculation logic
- Achieve at least 90% overall code coverage
- Test edge cases and error conditions
- Use pytest fixtures for common test data
- Mock external dependencies
- Use parameterized tests for multiple scenarios
- Include docstrings for complex test functions

```python
@pytest.mark.parametrize(
    "ticker,api_rate,volatility,event_risk,expected",
    [
        ("AAPL", 0.05, 15.0, 0, 0.0575),  # Normal case
        ("TSLA", 0.10, 30.0, 5, 0.1550),  # High volatility, medium event risk
        ("XYZ", 0.02, 10.0, None, 0.0220),  # No event risk
        ("GME", 0.50, 50.0, 10, 0.7500),  # Extreme case
    ]
)
def test_calculate_borrow_rate(
    ticker, api_rate, volatility, event_risk, expected, mock_api_client
):
    """Test borrow rate calculation with various inputs."""
    # Arrange
    mock_api_client.get_sec_lend_rate.return_value = api_rate
    mock_data_service.get_volatility.return_value = volatility
    mock_data_service.get_event_risk.return_value = event_risk
    
    # Act
    result = calculation_service.calculate_borrow_rate(ticker)
    
    # Assert
    assert result == pytest.approx(expected, abs=1e-4)
```

### Code Organization
- Follow the project's module structure
- Keep files focused on a single responsibility
- Limit file size to maintain readability (aim for <500 lines)
- Group related functions and classes together
- Use appropriate abstraction levels
- Avoid circular dependencies
- Use relative imports for internal modules

### Performance Optimization
- Use appropriate data structures for the task
- Optimize critical calculation paths
- Use caching for expensive operations
- Minimize database queries and external API calls
- Use bulk operations where appropriate
- Profile code to identify bottlenecks
- Document performance considerations in comments

## TypeScript Coding Standards

### Style Guide
- Follow the [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html)
- Use 2 spaces for indentation (no tabs)
- Limit lines to 100 characters
- Use camelCase for variables and functions
- Use PascalCase for classes, interfaces, and type aliases
- Use UPPER_CASE for constants
- Use semicolons at the end of statements
- Use single quotes for strings

### Type Definitions
- Use explicit type annotations for function parameters and return types
- Define interfaces for complex object structures
- Use type aliases for repeated types
- Use union types for variables that can have multiple types
- Use optional properties with the ? syntax
- Use readonly for immutable properties
- Export types that are used across modules

```typescript
// Define interfaces for data structures
export interface BorrowRateParams {
  ticker: string;
  volatilityIndex: number;
  eventRisk?: number;
}

export interface LocateFeeResult {
  totalFee: number;
  breakdown: {
    borrowCost: number;
    markup: number;
    transactionFees: number;
  };
  borrowRateUsed: number;
}

// Function with type annotations
export async function calculateLocateFee(
  params: BorrowRateParams,
  clientId: string,
  loanDays: number,
  positionValue: number
): Promise<LocateFeeResult> {
  // Implementation
}
```

### Documentation
- Use JSDoc comments for all functions, classes, and interfaces
- Include a brief description of the purpose
- Document all parameters with types and descriptions
- Document return values with types and descriptions
- Document exceptions that may be thrown
- Include examples for complex functions
- Keep documentation up to date with code changes

```typescript
/**
 * Configures AWS resources for the Borrow Rate Engine.
 *
 * This function sets up all required AWS infrastructure including VPC,
 * security groups, EKS cluster, RDS database, and Redis cache.
 *
 * @param {AwsConfig} config - Configuration parameters for AWS resources
 * @param {string} environment - Deployment environment (dev, staging, prod)
 * @returns {Promise<AwsResources>} Object containing references to created resources
 * @throws {ConfigurationError} If configuration is invalid
 * @throws {AwsError} If AWS resource creation fails
 *
 * @example
 * const resources = await configureAwsResources({
 *   region: 'us-east-1',
 *   vpcCidr: '10.0.0.0/16',
 *   databaseSize: 'db.t3.medium'
 * }, 'dev');
 */
export async function configureAwsResources(
  config: AwsConfig,
  environment: string
): Promise<AwsResources> {
  // Implementation
}
```

### Error Handling
- Use custom error classes for different error types
- Provide meaningful error messages with context
- Use try/catch blocks for error handling
- Propagate errors with appropriate context
- Use async/await with proper error handling
- Log errors with sufficient context for debugging

```typescript
try {
  const vpc = await createVpc(config.vpcCidr);
  logger.info(`VPC created with ID ${vpc.id}`);
  
  try {
    const securityGroups = await createSecurityGroups(vpc.id, config.securityRules);
    logger.info(`Created ${securityGroups.length} security groups`);
    
    // Continue with other resource creation
  } catch (error) {
    logger.error(`Failed to create security groups: ${error.message}`);
    await deleteVpc(vpc.id);  // Clean up VPC
    throw new AwsError('Security group creation failed', { cause: error });
  }
} catch (error) {
  logger.error(`Failed to create AWS resources: ${error.message}`);
  throw new AwsError('AWS resource creation failed', { cause: error });
}
```

### Testing Requirements
- Write unit tests for all functions and classes
- Achieve at least 90% code coverage
- Use Jest for testing
- Mock AWS services and external dependencies
- Test error handling and edge cases
- Use descriptive test names
- Group related tests in describe blocks

```typescript
describe('AWS Resource Configuration', () => {
  // Mock AWS SDK
  const mockVpcCreate = jest.fn();
  const mockSecurityGroupCreate = jest.fn();
  
  beforeEach(() => {
    // Set up mocks
    mockVpcCreate.mockReset().mockResolvedValue({ id: 'vpc-12345' });
    mockSecurityGroupCreate.mockReset().mockResolvedValue([{ id: 'sg-12345' }]);
    
    // Mock AWS SDK modules
    jest.mock('aws-sdk', () => ({
      EC2: jest.fn().mockImplementation(() => ({
        createVpc: mockVpcCreate,
        createSecurityGroup: mockSecurityGroupCreate
      }))
    }));
  });
  
  test('should create VPC with correct CIDR block', async () => {
    // Arrange
    const config = { vpcCidr: '10.0.0.0/16' };
    
    // Act
    await createVpc(config.vpcCidr);
    
    // Assert
    expect(mockVpcCreate).toHaveBeenCalledWith({
      CidrBlock: '10.0.0.0/16',
      AmazonProvidedIpv6CidrBlock: false
    });
  });
  
  test('should throw AwsError when VPC creation fails', async () => {
    // Arrange
    mockVpcCreate.mockRejectedValue(new Error('AWS API Error'));
    const config = { vpcCidr: '10.0.0.0/16' };
    
    // Act & Assert
    await expect(createVpc(config.vpcCidr))
      .rejects
      .toThrow(AwsError);
  });
});
```

### Code Organization
- Use modules to organize code
- Keep files focused on a single responsibility
- Limit file size to maintain readability (aim for <300 lines)
- Group related functions and classes together
- Use appropriate abstraction levels
- Avoid circular dependencies
- Use barrel exports (index.ts) for public APIs

## API Development Standards

### API Design Principles
- Follow REST architectural principles
- Use resource-oriented URLs
- Use appropriate HTTP methods (GET, POST, PUT, DELETE)
- Use consistent URL patterns
- Use query parameters for filtering and pagination
- Use meaningful HTTP status codes
- Design for backward compatibility
- See [API Design Documentation](../architecture/api-design.md) for details

### Request Validation
- Validate all request parameters
- Provide clear error messages for validation failures
- Use Pydantic models for request validation
- Define validation rules in a centralized location
- Include validation for both format and business rules
- Return appropriate HTTP status codes for validation errors

```python
class LocateFeeRequest(BaseModel):
    """Request model for locate fee calculation."""
    ticker: str
    position_value: Decimal
    loan_days: int
    client_id: str
    
    @validator('ticker')
    def validate_ticker(cls, v):
        """Validate ticker format."""
        if not TICKER_PATTERN.match(v):
            raise ValueError('Invalid ticker format')
        return v.upper()
    
    @validator('position_value')
    def validate_position_value(cls, v):
        """Validate position value range."""
        if v < MIN_POSITION_VALUE or v > MAX_POSITION_VALUE:
            raise ValueError(
                f'Position value must be between {MIN_POSITION_VALUE} and '
                f'{MAX_POSITION_VALUE}'
            )
        return v
    
    @validator('loan_days')
    def validate_loan_days(cls, v):
        """Validate loan days range."""
        if v < MIN_LOAN_DAYS or v > MAX_LOAN_DAYS:
            raise ValueError(
                f'Loan days must be between {MIN_LOAN_DAYS} and {MAX_LOAN_DAYS}'
            )
        return v
    
    @validator('client_id')
    def validate_client_id(cls, v):
        """Validate client ID format."""
        if not CLIENT_ID_PATTERN.match(v):
            raise ValueError('Invalid client ID format')
        return v
```

### Response Formatting
- Use consistent response formats
- Include status field in all responses
- Provide detailed error information
- Use appropriate HTTP status codes
- Format decimal values consistently
- Include all required fields in responses
- Document response formats in OpenAPI specification

```python
def format_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Format a successful API response."""
    return {
        "status": "success",
        **data
    }

def format_error_response(
    error: str,
    error_code: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format an error API response."""
    response = {
        "status": "error",
        "error": error,
        "error_code": error_code
    }
    if details:
        response["details"] = details
    return response
```

### API Documentation
- Document all API endpoints using OpenAPI 3.0
- Include detailed descriptions of endpoints
- Document request parameters and response schemas
- Include example requests and responses
- Document error responses and codes
- Keep documentation in sync with implementation
- Generate API documentation from code annotations

```python
@router.post("/calculate-locate", response_model=LocateFeeResponse)
async def calculate_locate_fee(
    request: LocateFeeRequest,
    api_key: str = Depends(get_api_key),
    calculation_service: CalculationService = Depends(get_calculation_service)
):
    """Calculate the locate fee for borrowing securities.
    
    This endpoint calculates the total fee charged to clients for locating and
    borrowing securities for short-selling operations. It includes the base
    borrow cost, broker markup, and transaction fees.
    
    Parameters:
    - **ticker**: Stock symbol (e.g., "AAPL")
    - **position_value**: Total value of the position in USD
    - **loan_days**: Duration of the loan in days
    - **client_id**: Client identifier for fee structure
    
    Returns a JSON object containing:
    - **total_fee**: Total fee amount
    - **breakdown**: Detailed breakdown of fee components
    - **borrow_rate_used**: Borrow rate used in calculation
    """
    try:
        result = await calculation_service.calculate_locate_fee(
            ticker=request.ticker,
            position_value=request.position_value,
            loan_days=request.loan_days,
            client_id=request.client_id
        )
        return format_success_response(result)
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=format_error_response(
                error=f"Validation error: {str(e)}",
                error_code="INVALID_PARAMETER",
                details={"validation_errors": e.errors}
            )
        )
    except CalculationError as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error=f"Calculation error: {str(e)}",
                error_code="CALCULATION_ERROR"
            )
        )
```

### API Versioning
- Use URL path versioning (e.g., /api/v1/)
- Maintain backward compatibility within a major version
- Document breaking changes clearly
- Support multiple API versions simultaneously during transitions
- Provide deprecation notices for outdated endpoints
- Include version information in API documentation

### API Security
- Require authentication for all endpoints
- Implement rate limiting to prevent abuse
- Validate and sanitize all inputs
- Use HTTPS for all API traffic
- Implement proper error handling to avoid information leakage
- Log all API access for audit purposes
- Implement appropriate authorization checks

## Database Standards

### Database Access
- Use SQLAlchemy ORM for database access
- Use async database access where appropriate
- Implement connection pooling
- Use transactions for related operations
- Implement retry logic for transient failures
- Close connections properly
- Use parameterized queries to prevent SQL injection

### Schema Design
- Use meaningful table and column names
- Define appropriate data types for columns
- Implement proper constraints (primary keys, foreign keys, unique)
- Use indexes for frequently queried columns
- Document table schemas and relationships
- Use migrations for schema changes
- Consider performance implications of schema design

### Query Optimization
- Write efficient queries
- Use appropriate indexes
- Avoid N+1 query problems
- Use bulk operations where appropriate
- Limit result sets to necessary data
- Monitor query performance
- Optimize critical queries

### Data Validation
- Validate data before insertion
- Implement appropriate constraints in the database
- Handle constraint violations gracefully
- Implement business rules at the application level
- Document validation rules
- Test data validation thoroughly

### Migrations
- Use Alembic for database migrations
- Write reversible migrations when possible
- Test migrations thoroughly
- Document migration changes
- Include data migrations when necessary
- Consider performance impact of migrations
- Plan for zero-downtime migrations

## Security Standards

### Authentication and Authorization
- Implement proper authentication for all endpoints
- Use secure password storage with appropriate hashing
- Implement role-based access control
- Validate permissions for all operations
- Use secure session management
- Implement proper API key management
- Log authentication and authorization events

### Input Validation
- Validate all inputs from external sources
- Implement both client-side and server-side validation
- Use parameterized queries for database access
- Sanitize inputs to prevent injection attacks
- Validate file uploads
- Implement proper error handling for validation failures
- Document validation rules

### Sensitive Data Handling
- Never store sensitive data in code or logs
- Use environment variables for configuration
- Use secure storage for secrets (AWS Secrets Manager)
- Implement proper encryption for sensitive data
- Minimize exposure of sensitive data
- Implement proper data masking
- Follow regulatory requirements for data handling

### Secure Communications
- Use HTTPS for all communications
- Implement proper certificate validation
- Use secure TLS configurations
- Implement proper authentication for API calls
- Validate external API responses
- Implement proper error handling for communication failures
- Monitor for security vulnerabilities in communication libraries

### Dependency Management
- Keep dependencies up to date
- Monitor for security vulnerabilities in dependencies
- Use dependency scanning tools
- Pin dependency versions
- Document dependency requirements
- Test dependency updates thoroughly
- Have a process for emergency security updates

## Testing Standards

### Unit Testing
- Write unit tests for all functions and methods
- Achieve 100% code coverage for core calculation logic
- Achieve at least 90% overall code coverage
- Test edge cases and error conditions
- Use pytest for Python tests
- Use Jest for TypeScript tests
- Mock external dependencies
- Use standard test patterns (Arrange-Act-Assert)

### Integration Testing
- Test component interactions
- Test database access
- Test API endpoints
- Test external API integrations
- Use realistic test data
- Test error handling and recovery
- Document integration test requirements

### Performance Testing
- Test system performance under load
- Establish performance baselines
- Test critical calculation paths
- Test database query performance
- Test API response times
- Document performance requirements
- Monitor performance metrics

### Security Testing
- Test authentication and authorization
- Test input validation
- Test for common vulnerabilities
- Use security scanning tools
- Test error handling for security implications
- Document security test requirements
- Perform regular security assessments

### Test Data Management
- Use realistic test data
- Maintain test data in version control
- Use fixtures for common test data
- Clean up test data after tests
- Document test data requirements
- Use data generators for large datasets
- Consider privacy implications of test data

## Documentation Standards

### Code Documentation
- Write clear and concise comments
- Document complex algorithms and business logic
- Use docstrings for all modules, classes, and functions
- Keep documentation up to date with code changes
- Document assumptions and constraints
- Document performance considerations
- Document security considerations

### API Documentation
- Document all API endpoints
- Use OpenAPI 3.0 for API documentation
- Include example requests and responses
- Document error responses and codes
- Keep API documentation up to date
- Generate API documentation from code annotations
- Make documentation accessible to API consumers

### Project Documentation
- Maintain a comprehensive README
- Document project structure
- Document development setup
- Document deployment procedures
- Document troubleshooting steps
- Keep documentation up to date
- Use clear and concise language

### Architecture Documentation
- Document system architecture
- Document component interactions
- Document data flow
- Document security architecture
- Use diagrams to illustrate complex concepts
- Keep architecture documentation up to date
- Document architectural decisions

## Code Review Standards

### Code Review Process
- All code changes must be reviewed
- Use pull requests for code reviews
- Assign appropriate reviewers
- Address all review comments
- Merge only after approval
- Document code review requirements
- Maintain a constructive review culture

### Review Checklist
- Code follows style guidelines
- Code is well-documented
- Tests are comprehensive and pass
- Code coverage meets requirements
- Error handling is appropriate
- Security considerations are addressed
- Performance implications are considered
- No unnecessary complexity

### Review Feedback
- Provide constructive feedback
- Focus on code, not the author
- Be specific about issues
- Suggest improvements
- Acknowledge good practices
- Explain the reasoning behind feedback
- Be timely with reviews

### Continuous Integration
- All pull requests must pass CI checks
- CI checks include:
  - Linting
  - Type checking
  - Unit tests
  - Integration tests
  - Code coverage
  - Security scanning
- Address CI failures promptly
- Document CI requirements

## Version Control Standards

### Branching Strategy
- Use feature branches for development
- Use pull requests for code reviews
- Maintain a clean main branch
- Use release branches for production releases
- Use hotfix branches for emergency fixes
- Document branching strategy
- Keep branches up to date with main

### Commit Standards
- Write clear and concise commit messages
- Use present tense for commit messages
- Reference issue numbers in commit messages
- Keep commits focused on a single change
- Avoid large commits
- Ensure commits compile and pass tests
- Sign commits when required

### Pull Request Standards
- Write clear and descriptive PR titles
- Provide a detailed description of changes
- Reference related issues
- Keep PRs focused on a single feature or fix
- Ensure all CI checks pass
- Address review comments promptly
- Update PR description as needed

### Versioning
- Use semantic versioning (MAJOR.MINOR.PATCH)
- Increment MAJOR for breaking changes
- Increment MINOR for new features
- Increment PATCH for bug fixes
- Document version changes in release notes
- Tag releases in version control
- Follow a consistent versioning process

## Conclusion

Adherence to these coding standards ensures that the Borrow Rate & Locate Fee Pricing Engine maintains high quality, security, and maintainability. These standards should be followed by all developers working on the project. Regular reviews of these standards will be conducted to ensure they remain relevant and effective.

## References

- [Development Environment Setup](./setup.md)
- [API Design Documentation](../architecture/api-design.md)
- [Python PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html)
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)