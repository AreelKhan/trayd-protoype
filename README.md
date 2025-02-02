# Job Management API

Hey Cara! Here's my attempt at building an API for the job management system.
# Setup

1. Prerequisites:
   - Docker
   - Docker Compose
   - Port 8000 is free

2. Running the API:
```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`

# API Endpoints

### Create a Job
```bash
POST /jobs/

# Required fields
{
    "name": "string",      # 1-100 characters
    "customer": "string"   # 1-100 characters
}

# Optional fields
{
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "status": "string"     # Must be one of: "In Progress", "Completed", "Cancelled"
}
```

### Create a Worker
```bash
POST /workers/

{
    "name": "string",      # 1-100 characters
    "role": "string",      # 1-100 characters
    "job_id": number       # Optional, references a job
}
```

### Get a job
```bash
GET /jobs/

# Available query parameters:
keyword=string          # Search in name and customer fields
status=string           # Filter by specific status
start_after=YYYY-MM-DD  # Filter jobs starting after this date
end_before=YYYY-MM-DD   # Filter jobs ending before this date
sort_by=field_name      # Sort by: name, start_date, customer, or status
desc=boolean            # Sort in descending order (default: false)
```

### Get a worker
```bash
GET /workers/

# Available query parameters:
name=string          # Search by worker name
role=string          # Filter by role
job_id=number        # Filter by job ID
```

### Analytics
```bash
GET /analytics/

# Returns statistics about jobs and workers
Response:
{
    "total_jobs": 3,
    "jobs_by_status": {
        "In Progress": 2,
        "Completed": 1,
        "Unspecified": 0
    },
    "total_workers": 5,
    "workers_by_role": {
        "Electrician": 2,
        "Plumber": 1,
        "Carpenter": 2
    }
}
```

The analytics endpoint provides:
- Total number of jobs in the system
- Breakdown of jobs by their status
- Total number of workers
- Distribution of workers by their roles

### Other Endpoints
- `GET /jobs/{id}` - Get a specific job.
- `DELETE /jobs/{id}` - Delete a job and its workers
- `GET /workers/` - List all workers
- `GET /jobs/{id}/workers/` - Get workers for a specific job
- `PUT /workers/{worker_id}/assign/{job_id}` - Assign worker to a job
- `GET /analytics/` - Get analytics about jobs and workers

### Improvements

- No pagination for large result sets
- No fuzzy search support or text search (regex, etc.)
- No historical data tracking (ie, when a job is not in DB, it's not in analytics)
- No data archiving strategy, once a job is Completed, it just sits there.
- No migrations. It would suck to use this in production.

# Approach
- Disclaimer: I use Cursor as my primary IDE, so much of the code was written with AI assistance.
- Python is my first language, so I used it.
- FastAPI is fast, hence, suitable for this task. But for a full fedged app I'd go with Django.
- I opted for a relational database because our data suits it. Went with PostgreSQL because I am familiar with it.
- I used SQLAlchemy as the ORM. I have never used an ORM besides Django's and Prisma. So this was a good learning experience!
- I used Pydantic for defining models and validating data. It's a tool I am very comfortable with.
- I used Docker to save my sanity when it comes to deploying.
- I tested the app with Postman.
- I faced an issue where if you delete a job with workers assigned to it, they are left pointing to a non-existent job. So, I added a cascade delete to the workers table to avoid this issue. Perhaps this is not the best approach. It may make more sense for the workers to not depend on a job. A mapping table can link workers to jobs. This way a worker can be assigned to no jobs and also to multiple jobs.
