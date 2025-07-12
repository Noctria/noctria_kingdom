-- 📦 optuna_db を作成（すでに存在する場合はスキップ）
DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_database
      WHERE datname = 'optuna_db'
   ) THEN
      CREATE DATABASE optuna_db;
   END IF;
END
$$;
