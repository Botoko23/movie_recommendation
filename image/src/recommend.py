import os
import json
import base64
from typing import List

from data_model import Recommendation, RequestModel, SuccessResponse, ErrorResponse

import psycopg2
from sentence_transformers import SentenceTransformer

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
PORT = os.getenv("PORT")
TABLE = os.getenv("TABLE")
MODEL_PATH = os.getenv("MODEL_PATH")


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=PORT
    )

def recommend_filters(release_period: List[str] | None, title_type: List[str] | None, 
                           min_rating: float | None, max_rating: float | None):
    query = f'''SELECT title, original_title, release_date, genres, overview, poster_path, rating, title_type FROM {TABLE}'''

    conditions = []
    params = []

    if release_period:
        conditions.append(f"release_period IN ({', '.join(['%s'] * len(release_period))})")
        params += release_period
    
    if title_type:
        conditions.append(f"title_type IN ({', '.join(['%s'] * len(title_type))})")
        params += title_type
    
    if min_rating or max_rating:
        conditions.append("rating BETWEEN %s AND %s")
        params += [min_rating or 0, max_rating or 10]

    if conditions:
        query += "\nWHERE " + " AND ".join(conditions)
    
    return query, params

def recommened_by_title_id(title_id: int, release_period: List[str] | None, title_type: List[str] | None, 
                           min_rating: float | None, max_rating: float | None, limit: int | None = 5) -> tuple[List[Recommendation] | None, Exception]:
    try:
        error = None
        recommendations = []

        query, params = recommend_filters(release_period, title_type, min_rating, max_rating)
        # Connect to PostgreSQL
        conn = get_db_connection()
        cursor = conn.cursor()

        query  += f'''\nORDER BY embedding <#> (select embedding from {TABLE} where id = %s) LIMIT %s OFFSET 1;''' 
        params += [title_id, limit]

        cursor.execute(query, tuple(params))
        results = cursor.fetchall()

        for row in results:
            recommendations.append(Recommendation(
                title=row[0],
                originaltitle=row[1],
                releaseDate=row[2].isoformat(),
                genres=row[3],
                overview=row[4],
                posterPath=row[5],
                rating=row[6], 
                titleType=row[7]
            ))

        cursor.close()
        conn.close()
    except Exception as e:
        error = e
    else:
        return recommendations, error

def recommend_by_user_plot(user_plot: str, release_period: List[str], title_type: List[str], 
                           min_rating: float | None, max_rating: float | None, limit: int | None = 5) -> tuple[List[Recommendation] | None, Exception]:
    try: 
        error = None
        recommendations = []

        model = SentenceTransformer(MODEL_PATH)
        query_embedding = model.encode(user_plot).tolist()
        query, params = recommend_filters(release_period, title_type, min_rating, max_rating)
        # Connect to PostgreSQL
        conn = get_db_connection()
        cursor = conn.cursor()     

        query  += '''\nORDER BY embedding <#> %s::vector LIMIT %s''' 
        params += [query_embedding, limit]

        cursor.execute(query, tuple(params))
        results = cursor.fetchall()   
        
        
        for row in results:
            recommendations.append(Recommendation(
                title=row[0],
                originaltitle=row[1],
                releaseDate=row[2].isoformat(),
                genres=row[3],
                overview=row[4],
                posterPath=row[5],
                rating=row[6], 
                titleType=row[7]
            ))

        cursor.close()
        conn.close()
    except Exception as e:
        error = e
    finally:
        return recommendations, error

def lambda_handler(event: dict, context):
    try:
        # Decode if base64 encoded and body exists
        if event.get("isBase64Encoded") and event.get("body", None):
            event["body"] =  base64.b64decode(event["body"]).decode("utf-8")

        event["body"] = json.loads(event["body"]) if event["body"] else {}
        # Parse the request
        parsed_event = {
            "queryStringParameters": event.get("queryStringParameters", {}),
            "body": event.get("body", {})  # Get raw body (None if missing)
        }

        # Validate request using Pydantic
        request = RequestModel(**parsed_event)

    except Exception as e:
        response = ErrorResponse.create(status_code=400, error=str(e))
    else:
        query_params = request.queryStringParameters
        body = request.body
        
        if query_params:
            title_id = query_params.titleId
            release_period = query_params.releasePeriod
            title_type = query_params.type
            min_rating = query_params.minRating
            max_rating = query_params.maxRating
            limit = query_params.limit
            recommendations, error = recommened_by_title_id(title_id, release_period, title_type, 
                                            min_rating, max_rating, limit)
            
            response = SuccessResponse.create(recommendations) if not error else ErrorResponse.create(500, str(error))
        else:
            user_plot = body.plot
            release_period = body.filters.releasePeriod
            title_type = body.filters.type
            min_rating = body.filters.minRating
            max_rating = body.filters.maxRating
            limit = body.filters.limit
            recommendations, error  = recommend_by_user_plot(user_plot, release_period, title_type, min_rating, max_rating, limit)
            response = SuccessResponse.create(recommendations) if not error  else ErrorResponse.create(500, str(error))
    finally:
        return response.model_dump_json(indent=2)
    



