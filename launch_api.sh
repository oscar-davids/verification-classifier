docker build -f Dockerfile -t verifier:v1 . && docker build -f Dockerfile-api -t verifier-api:v1 . && docker run --volume="$(pwd)/stream":/stream --volume="$(pwd)/logs":/logs -p 5000:5000 verifier-api:v1