#!/bin/sh
set -eu

psql +  --set ON_ERROR_STOP=1 +  --set runtime_data_password="${TOUCHSTONE_DATA_DB_PASSWORD}" +  --set memory_service_password="${TOUCHSTONE_MEMORY_DB_PASSWORD}" +  --file /touchstone-db/postgresql/bootstrap.sql

for schema_file in +  platform_contract.sql +  financial_user_data.sql +  runtime_core.sql +  task_messaging.sql +  notifications.sql +  registry.sql +  run_projection.sql +  watch.sql +  memory_service.sql
do
  psql +    --set ON_ERROR_STOP=1 +    --file "/touchstone-db/postgresql/schema/${schema_file}"
done
