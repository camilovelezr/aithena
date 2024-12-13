identify index building queries

SELECT
    pid,
    usename,
    datname,
    state,
    query,
    query_start
FROM
    pg_stat_activity
WHERE
    query LIKE '%CREATE INDEX%'
    AND state = 'active';


    terminate a backend query:

    SELECT pg_terminate_backend(<pid>);

-------------

SELECT phase, round(100.0 * blocks_done / nullif(blocks_total, 0), 1) AS "%" FROM pg_stat_progress_create_index;