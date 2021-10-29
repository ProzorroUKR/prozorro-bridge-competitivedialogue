# Prozorro bridge competitivedialogue


## Docker install

```
docker compose build
docker compose up -d
```


## Manual install

1. Install requirements

```
virtualenv -p python3.8.2 venv
source venv/bin/activate
pip install -r requirements.txt
pip install .
```

2. Set variables in **settings.py**

3. Run application

```
python -m prozorro_bridge_competitivedialogue.main
```

## Tests and coverage 

```
coverage run --source=./src/prozorro_bridge_competitivedialogue -m pytest tests/main.py
```

## Config settings (env variables):

**Required**

- ```API_OPT_FIELDS``` - Fields to parse from feed (need for crawler)
- ```PUBLIC_API_HOST``` - API host on which chronograph will iterate by feed (need for crawler also)
- ```MONGODB_URL``` - String of connection to database (need for crawler also)

**Optional**
- ```CRAWLER_USER_AGENT``` - Set value of variable to all requests header `User-Agent`
- ```MONGODB_DATABASE``` - Name of database
- ```API_TOKEN``` - Access token to CDB

**Doesn't set by env**
- ```ALLOWED_STATUSES``` - Statuses in which not need to create second stage (it already exists)
- ```REWRITE_STATUSES``` - Statuses in which need to create second stage
- ```COPY_NAME_FIELDS``` - Fields to copy in second stage


## Workflow

Service is create second stages for competitive dialogue and patch them into terminated statuses
