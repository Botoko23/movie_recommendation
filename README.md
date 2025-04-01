# Movie Recommendation Project
This project builds an end-to-end movie recommender system with frontend and is served on AWS
## Hau's notes
1. Download the movies_series.csv data as shared in ggogle drive into the `data` folder
2. pip install sentence-transformers and run the following to download the model locally:
- model_name = "trihoang131/distilroberta-movies-embeddings"
- model_path = "project_root_folder/image/models/finetuned_model"  
- model = SentenceTransformer(model_name)
- model.save(model_path)
3. run docker-compose up for the yaml file in image folder to starting things up (for first run, data will automatically loaded into the table)
4. 
- Project goes as the following: user can search for movies/series titles in the database with the search feature
- users can get recommendations of movies/series by either selecting a specific title from the search result or provide their own description of the plot they want to watch. some filtering options can be applied when search for recommendations like releasePeriod, type (eg. ["movie", "series"], ["movie"]), minRating, maxRating
5. This is the example of curl to do search titles present in the database (search must be present and string, page not given will have default as 1 to mimick first paginated result)
- curl -X POST "http://localhost:9001/2015-03-31/functions/function/invocations" \
     -H "Content-Type: application/json" \
     -d '{
           "queryStringParameters": {
             "search": "example search",
             "page": 1
           }
         }'
6. This is the example of curl to do recommendations with title id returned from the search
- curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
     -H "Content-Type: application/json" \
     -d '{
           "queryStringParameters": {
             "titleId": 53,
             "releasePeriod": ["The 90s", "The 2000s"],
             "type": ["movie", "series"],
             "minRating": 5,
             "maxRating": null,
             "limit": 10
           }
         }'
7. This is the example of curl to do recommendations with user-provided plot w/o base64 encoding
- curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
     -H "Content-Type: application/json" \
     -d '{
           "isBase64Encoded": null,
           "body": "{ \"plot\": \"In a near-future world, an abandoned space station orbiting Jupiter suddenly comes back to life, transmitting a distress signal. A small crew of specialists is sent to investigate, only to find the station seemingly empty—until they start hearing voices. As they unravel logs from the lost crew, they discover that something non-human has learned to mimic them. One by one, they question who among them is real. With their ship’s return systems mysteriously disabled, they must outsmart the entity before they, too, become nothing more than echoes in the void.\", \"filters\": { \"releasePeriod\": null, \"type\": [\"movie\"], \"minRating\": 5, \"maxRating\": null, \"limit\": 5 } }"
         }'
8. This is the example of curl to do recommendations with user-provided plot with base64 encoding
- curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
     -H "Content-Type: application/json" \
     -d '{
           "isBase64Encoded": "true",
           "body": "eyJwbG90IjogIkluIGEgbmVhci1mdXR1cmUgd29ybGQsIGFuIGFiYW5kb25lZCBzcGFjZSBzdGF0aW9uIG9yYml0aW5nIEp1cGl0ZXIgc3VkZGVubHkgY29tZXMgYmFjayB0byBsaWZlLCB0cmFuc21pdHRpbmcgYSBkaXN0cmVzcyBzaWduYWwuIEEgc21hbGwgY3JldyBvZiBzcGVjaWFsaXN0cyBpcyBzZW50IHRvIGludmVzdGlnYXRlLCBvbmx5IHRvIGZpbmQgdGhlIHN0YXRpb24gc2VlbWluZ2x5IGVtcHR5XHUyMDE0dW50aWwgdGhleSBzdGFydCBoZWFyaW5nIHZvaWNlcy4gQXMgdGhleSB1bnJhdmVsIGxvZ3MgZnJvbSB0aGUgbG9zdCBjcmV3LCB0aGV5IGRpc2NvdmVyIHRoYXQgc29tZXRoaW5nIG5vbi1odW1hbiBoYXMgbGVhcm5lZCB0byBtaW1pYyB0aGVtLiBPbmUgYnkgb25lLCB0aGV5IHF1ZXN0aW9uIHdobyBhbW9uZyB0aGVtIGlzIHJlYWwuIFdpdGggdGhlaXIgc2hpcFx1MjAxOXMgcmV0dXJuIHN5c3RlbXMgbXlzdGVyaW91c2x5IGRpc2FibGVkLCB0aGV5IG11c3Qgb3V0c21hcnQgdGhlIGVudGl0eSBiZWZvcmUgdGhleSwgdG9vLCBiZWNvbWUgbm90aGluZyBtb3JlIHRoYW4gZWNob2VzIGluIHRoZSB2b2lkLiIsICJmaWx0ZXJzIjogeyJyZWxlYXNlUGVyaW9kIjogbnVsbCwgInR5cGUiOiBbIm1vdmllIl0sICJtaW5SYXRpbmciOiA1LCAibWF4UmF0aW5nIjogbnVsbCwgImxpbWl0IjogNX19"
         }'
