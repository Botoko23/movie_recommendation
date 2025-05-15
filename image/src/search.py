import os
import json
from math import ceil
from typing import List

import psycopg2
from pydantic import BaseModel

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
PORT = os.getenv("PORT")
TABLE = os.getenv("TABLE")

class QueryParams(BaseModel):
    search: str
    page: int = 1

class RequestModel(BaseModel):
    queryStringParameters: QueryParams

class SearchResults(BaseModel):
    titleId: int
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
    def create(cls, titles: List[SearchResults], current_page: int, page_size: int, 
               total_items: int, total_pages: int):
        return cls(
            body={"titles": [title.model_dump() for title in titles],
                  "currentPage": current_page,
                  "pageSize": page_size,
                  "totalItems": total_items,
                  "totalPages": total_pages,
                  "nextPage": current_page + 1 if current_page + 1 <= total_pages else None,
                  "prevPage": current_page - 1 if current_page != 1 else None 
                  }
                )

class ErrorResponse(BaseModel):
    statusCode: int
    headers: dict = {"Content-Type": "application/json"}
    body: dict

    @classmethod
    def create(cls, status_code: int, error: str):
        return cls(
            statusCode=status_code,
            body={"error message": error}
        )

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=PORT
    )

def search(search_text:str, page_size:int, current_page:int) -> tuple[List[SearchResults] | None, int | None, int | None]:
    try:
        ranking_start = page_size * (current_page - 1) + 1 # Start from the last movie_id
        ranking_end = ranking_start + page_size - 1  # End at the last movie_id

        # Convert search text to PostgreSQL tsquery format (replace spaces with '|')
        search_terms = " | ".join([text.strip() for text in search_text.split()])  # "star wars" -> "star | wars"

        # Connect to PostgreSQL
        conn = get_db_connection()
        cursor = conn.cursor()

        # SQL query using full-text search with pagination
        search_query  = f'''SELECT id, title, original_title, release_date, genres, overview, poster_path, rating, title_type,
                ts_rank(title_search, to_tsquery('simple', %s)) AS score,
                ROW_NUMBER() OVER (order by ts_rank(title_search, to_tsquery('simple', %s)) DESC) AS ranking
                FROM {TABLE} 
                WHERE title_search @@ to_tsquery('simple', %s)
                ORDER BY score DESC 
                '''
        # Execute query
        cursor.execute(search_query, (search_terms, search_terms, search_terms))
        results = cursor.fetchall()
        total_items = len(results)

        titles = []
        for row in results[ranking_start:ranking_end]:
            titles.append(SearchResults(
                titleId=row[0],
                title=row[1],
                originaltitle=row[2],
                releaseDate=row[3].isoformat(),
                genres=row[4],
                overview=row[5],
                posterPath=row[6],
                rating=row[7], 
                titleType=row[8]
            ))

        # Close DB connection
        cursor.close()
        conn.close()
    
    except Exception as e:
        return None, None, None
    else:
        return titles, total_items, ceil(total_items/page_size)


def lambda_handler(event: dict, context):
    try:
        # Parse the request
        parsed_event = {
            "queryStringParameters": event.get("queryStringParameters", {})
            }

        # Validate request using Pydantic
        request = RequestModel(**parsed_event)
    except Exception as e:
        response = ErrorResponse.create(status_code=400, error=str(e))
    else:
        search_text = request.queryStringParameters.search  # User search input
        page = request.queryStringParameters.page
        page_size = 20  # Number of results per page
        titles, total_items, total_pages = search(search_text=search_text, page_size=page_size, current_page=page)
        if titles is not None and total_items is not None and total_pages is not None:
            response = SuccessResponse.create(titles, page, page_size, total_items, total_pages)
        else:
            response = ErrorResponse.create(500, "Error with search system")

    finally:
        return {
        'statusCode': response.statusCode,
        'headers': response.headers,
        'body': json.dumps(response.body) # Ensure body is a JSON string
    }

if __name__ == "__main__":

    event = {
        "queryStringParameters": {
            "search": "star wars",
            "page": 1
        }
    }
    response = lambda_handler(event, None)
    print(response)