from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "t_user" (
    "created_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "status" INT NOT NULL  DEFAULT 1,
    "user_id" UUID NOT NULL  PRIMARY KEY,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "fullname" VARCHAR(1000) NOT NULL  DEFAULT '',
    "phone" VARCHAR(100) NOT NULL  DEFAULT '',
    "token" VARCHAR(1000) NOT NULL  DEFAULT '',
    "type" INT NOT NULL  DEFAULT 1
);
CREATE INDEX IF NOT EXISTS "idx_t_user_email_6fe6a5" ON "t_user" ("email");
CREATE INDEX IF NOT EXISTS "idx_t_user_token_f70d89" ON "t_user" ("token");
CREATE TABLE IF NOT EXISTS "t_user_devices" (
    "created_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "status" INT NOT NULL  DEFAULT 1,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "device_name" VARCHAR(100) NOT NULL  DEFAULT '',
    "device_id" VARCHAR(100) NOT NULL  DEFAULT '',
    "location" VARCHAR(100) NOT NULL  DEFAULT '',
    "user_id" UUID NOT NULL REFERENCES "t_user" ("user_id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
