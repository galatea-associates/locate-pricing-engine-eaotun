"""
Implements the REST API endpoint for calculating locate fees in the Borrow Rate & Locate Fee Pricing Engine.
This module handles client requests for fee calculations, validates input parameters, retrieves necessary data,
performs calculations, and returns standardized responses with fee details.
"""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status  # fastapi 0.103.0+
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session  # sqlalchemy 2.0.0+

from ...api.deps import get_db, authenticate_api_key, validate_ticker, validate_position_value, validate_loan_days, get_redis_cache  # Internal imports
from ...schemas.request import CalculateLocateRequest  # Internal imports
from ...schemas.response import CalculateLocateResponse, BaseResponse  # Internal imports
from ...schemas.calculation import FeeBreakdownSchema  # Internal imports
from ...services.calculation.locate_fee import calculate_locate_fee  # Internal imports
from ...services.data.brokers import BrokerService, broker_service  # Internal imports
from ...core.constants import ErrorCodes, TransactionFeeType  # Internal imports
from ...core.errors import create_error_response  # Internal imports
from ...core.exceptions import ClientNotFoundException, CalculationException  # Internal imports

# Initialize logger
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(tags=["calculations"])


@router.post("/calculate-locate", response_model=CalculateLocateResponse, status_code=status.HTTP_200_OK)
@router.get("/calculate-locate", response_model=CalculateLocateResponse, status_code=status.HTTP_200_OK)
async def calculate_locate_fee_endpoint(
    request: CalculateLocateRequest,
    db: Session = Depends(get_db),
) -> CalculateLocateResponse:
    """
    API endpoint for calculating locate fees.

    Args:
        request (CalculateLocateRequest): Request model containing ticker, position_value, loan_days, and client_id.
        db (Session): Database session dependency.

    Returns:
        CalculateLocateResponse: Locate fee calculation response with total fee and breakdown.
    """
    # Log the incoming request with ticker, position_value, loan_days, and client_id
    logger.info(f"Received locate fee calculation request: ticker={request.ticker}, position_value={request.position_value}, loan_days={request.loan_days}, client_id={request.client_id}")

    try:
        # Try to retrieve broker configuration using broker_service.get_broker(client_id)
        broker_config = broker_service.get_broker(request.client_id)

        # Extract markup_percentage, fee_type, and fee_amount from broker configuration
        markup_percentage = broker_config["markup_percentage"]
        fee_type = broker_config["transaction_fee_type"]
        fee_amount = broker_config["transaction_amount"]

        # Call calculate_locate_fee with ticker, position_value, loan_days, markup_percentage, fee_type, and fee_amount
        calculation_result = calculate_locate_fee(
            ticker=request.ticker,
            position_value=request.position_value,
            loan_days=request.loan_days,
            markup_percentage=markup_percentage,
            fee_type=fee_type,
            fee_amount=fee_amount
        )

        # Create FeeBreakdownSchema from the calculation result breakdown
        fee_breakdown = FeeBreakdownSchema(**calculation_result["breakdown"])

        # Return CalculateLocateResponse with status='success', total_fee, breakdown, and borrow_rate_used
        response = CalculateLocateResponse(
            status="success",
            total_fee=Decimal(calculation_result["total_fee"]),
            breakdown=fee_breakdown,
            borrow_rate_used=Decimal(calculation_result["borrow_rate_used"])
        )
        logger.info(f"Successfully calculated locate fee for ticker: {request.ticker}, total_fee: {response.total_fee}")
        return response

    except ClientNotFoundException as e:
        # Handle ClientNotFoundException by returning appropriate error response
        logger.warning(f"Client not found: {str(e)}")
        error_response = create_error_response(
            message=str(e),
            error_code=ErrorCodes.CLIENT_NOT_FOUND,
            details={"client_id": request.client_id}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response["error"]
        )

    except CalculationException as e:
        # Handle CalculationException by returning appropriate error response
        logger.error(f"Calculation error: {str(e)}")
        error_response = create_error_response(
            message=str(e),
            error_code=ErrorCodes.CALCULATION_ERROR,
            details={"ticker": request.ticker, "position_value": request.position_value, "loan_days": request.loan_days}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response["error"]
        )

    except Exception as e:
        # Handle other exceptions by logging and returning a generic error response
        logger.exception(f"Unexpected error: {str(e)}")
        error_response = create_error_response(
            message="Internal server error",
            error_code=ErrorCodes.CALCULATION_ERROR,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response["error"]
        )


# Export the router
__all__ = ["router"]