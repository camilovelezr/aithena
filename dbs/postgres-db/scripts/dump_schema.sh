#!/bin/bash

# Load environment variables from .env file
export $(grep -v '^#' .env | xargs)

# Connect to the PostgreSQL database using psql
pgdump -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -p $POSTGRES_PORT -s -f openalex_polus2.sql