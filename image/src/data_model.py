from pydantic import BaseModel, model_validator
from typing import List, Optional, Union

# Define request query parameters model
class QueryParams(BaseModel):
    titleId: Optional[int] = None
    releasePeriod: Optional[List[str]] = None
    type: Optional[List[str]] = None
    minRating: Optional[int] = None
    maxRating: Optional[int] = None
    limit: Optional[int] = None

# Define request body filters model
class BodyFilters(BaseModel):
    releasePeriod: Optional[List[str]] = None
    type: Optional[List[str]] = None
    minRating: Optional[int] = None
    maxRating: Optional[int] = None
    limit: Optional[int] = None

# Define request body model
class RequestBody(BaseModel):
    plot: Optional[str] = None
    filters: Optional[BodyFilters] = None

# Define full request model
class RequestModel(BaseModel):
    queryStringParameters: Union[QueryParams, dict] = {}
    body: Union[RequestBody, dict] = {}
    # Ensure at least one of titleId or plot is present
    @model_validator(mode="before")
    def check_title_or_plot(cls, values:dict):
        query_params: dict = values.get("queryStringParameters", {})
        body: dict = values.get("body", {})

                # check 1: at least one must be present
        if not query_params and not body:
            raise ValueError("Either 'queryStringParameters' or 'body' must be provided.")

        title_id = query_params.get("titleId", None)
        plot = body.get("plot", None)

        # First Validation: at least one of titleId or plot
        if not title_id and not plot:
            raise ValueError("Either 'titleId' (query parameter) or 'plot' (body) must be provided.")

        # Second Validation: limit check when titleId is present
        if title_id and query_params.get("limit", None) is None:
            raise ValueError("'limit' query parameter is required when 'titleId' is provided.")

        # Third Validation: limit check when plot is present
        if plot:
            filters: dict = body.get("filters", {}) 
            if filters.get("limit", None) is None and title_id is None:
                raise ValueError("'limit' must be provided in 'filters' when 'plot' is provided.")

        return values    

class Recommendation(BaseModel):
    title: str
    originaltitle: str
    releaseDate: str  # Using ISO 8601 format (from .isoformat())
    genres: str  # Assuming it's a comma-separated string or None
    overview: str
    posterPath: str
    rating: float  # Keeping as a string since it's explicitly converted in the code
    titleType: str

class SuccessResponse(BaseModel):
    statusCode: int = 200
    headers: dict = {"Content-Type": "application/json"}
    body: dict

    @classmethod
    def create(cls, recommendations: List[Recommendation]):
        return cls(
            body={"recommendations": [rec.model_dump() for rec in recommendations]}
        )

class ErrorResponse(BaseModel):
    statusCode: int
    headers: dict = {"Content-Type": "application/json"}
    body: dict

    @classmethod
    def create(cls, status_code: int, error: str):
        return cls(
            statusCode=status_code,
            body={"message": "Invalid request", "error": error}
        )
