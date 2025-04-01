CREATE EXTENSION IF NOT EXISTS vector;


CREATE TABLE IF NOT EXISTS movies_series (
    id SERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    original_title VARCHAR(300) NOT NULL,
    release_date DATE NOT NULL,
    release_period VARCHAR(30) NOT NULL,
    genres VARCHAR(200) NOT NULL,
    overview VARCHAR(2500) NOT NULL,
    poster_path VARCHAR(100) NOT NULL,
    rating NUMERIC(3,1) NOT NULL,
    title_type VARCHAR(30)  CHECK (title_type IN ('movie', 'series')) NOT NULL,
    embedding VECTOR(768) NOT NULL
);


COPY movies_series(title, original_title, release_date, release_period, genres, overview, poster_path, 
						rating, title_type, embedding) 
FROM '/docker-entrypoint-initdb.d/movies_series.csv' 
DELIMITER ',' 
CSV HEADER;

ALTER TABLE movies_series ADD title_search tsvector GENERATED ALWAYS AS(
	to_tsvector('simple', title)
) STORED;


CREATE INDEX title_seach_index on movies_series
    USING GIN (title_search);




