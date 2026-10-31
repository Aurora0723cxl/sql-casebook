-- 电商订单分析案例库 · 表结构
-- 零依赖：SQLite 3，直接 `sqlite3 data.db < schema.sql`

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS impressions;
DROP TABLE IF EXISTS channel_spend;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id     INTEGER PRIMARY KEY,
    signup_date TEXT NOT NULL,              -- YYYY-MM-DD
    city        TEXT NOT NULL,
    channel     TEXT NOT NULL,              -- 注册来源渠道
    age_band    TEXT NOT NULL               -- 18-24 / 25-30 / 31-40 / 41+
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    category   TEXT NOT NULL,
    title      TEXT NOT NULL,
    price      REAL NOT NULL
);

CREATE TABLE orders (
    order_id   INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(user_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity   INTEGER NOT NULL,
    amount     REAL NOT NULL,               -- 实付金额
    status     TEXT NOT NULL,               -- paid / refunded / cancelled
    created_at TEXT NOT NULL,               -- YYYY-MM-DD HH:MM:SS
    paid_at    TEXT                         -- 未支付为 NULL
);

-- 用户级埋点：点击及之后的动作。曝光量是广告后台的汇总数，见 impressions 表。
CREATE TABLE events (
    event_id   INTEGER PRIMARY KEY,
    user_id    INTEGER REFERENCES users(user_id),
    channel    TEXT NOT NULL,
    event_type TEXT NOT NULL,               -- 点击 / 加购 / 下单 / 支付
    ts         TEXT NOT NULL
);

CREATE TABLE impressions (
    channel     TEXT NOT NULL,
    month       TEXT NOT NULL,              -- YYYY-MM
    impressions INTEGER NOT NULL,
    PRIMARY KEY (channel, month)
);

CREATE TABLE channel_spend (
    channel TEXT NOT NULL,
    month   TEXT NOT NULL,                  -- YYYY-MM
    spend   REAL NOT NULL,                  -- 当月投放花费
    PRIMARY KEY (channel, month)
);
