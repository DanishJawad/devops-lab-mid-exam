# Lab Notes: Docker, Compose and AWS ALB/ASG deployment

A small notes app (FastAPI + PostgreSQL) deployed on EC2 with Docker Compose,
behind an Application Load Balancer and an Auto Scaling Group, tested with Selenium.

## Run locally
    cp .env.example .env
    docker compose up -d --build
    open http://localhost

## Selenium tests
    pip install selenium pytest
    APP_URL=http://localhost pytest -v tests/

## Known limitation
Each EC2 instance runs its own Postgres container, so the two instances have
separate data. Instance replacement by the ASG also loses that instance's data.
A production setup would move the database to a shared service such as Amazon RDS.
