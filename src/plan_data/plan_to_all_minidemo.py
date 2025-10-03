def main():
    import os

    import psycopg2

    dsn = os.getenv("NOCTRIA_OBS_PG_DSN")
    if not dsn:
        raise EnvironmentError("NOCTRIA_OBS_PG_DSN is not set")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            # Simulate writing to the database
            cur.execute("INSERT INTO obs_plan_runs DEFAULT VALUES;")
            cur.execute("INSERT INTO obs_infer_calls DEFAULT VALUES;")
            conn.commit()
