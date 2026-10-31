# -*- coding: utf-8 -*-
"""生成案例库的示例数据（确定性随机，seed=42）。

用法：
    python seed.py            # 生成 data.db
    python seed.py --force    # 已存在也重建

数据是合成的，但结构、口径、异常都按真实业务埋：
- 渠道 5 个，投放花费与转化率不同；
- 订单状态含退款，其中一个品类在特定月份出现退款异常；
- 2025-11（双 11）、2026-06（618）有明显大促峰值。
"""
import os
import random
import sqlite3
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data.db")
SCHEMA = os.path.join(HERE, "schema.sql")

RNG = random.Random(42)

CHANNELS = ["自然搜索", "信息流", "社群", "老客推荐", "直播"]
CH_WEIGHT = [0.30, 0.26, 0.18, 0.12, 0.14]
CH_CTR = {          # 点击 / 曝光
    "自然搜索": 0.055,
    "信息流": 0.018,
    "社群": 0.072,
    "老客推荐": 0.061,
    "直播": 0.093,
}
CH_CVR = {          # 支付 / 点击（大促月会上浮）
    "自然搜索": 0.031,
    "信息流": 0.014,
    "社群": 0.040,
    "老客推荐": 0.052,
    "直播": 0.036,
}
CH_SPEND_BASE = {   # 每月基础花费
    "自然搜索": 42000,
    "信息流": 180000,
    "社群": 36000,
    "老客推荐": 9000,
    "直播": 120000,
}
CITIES = ["长春", "沈阳", "大连", "哈尔滨", "北京", "青岛", "上海"]
CITY_W = [0.16, 0.18, 0.13, 0.10, 0.14, 0.13, 0.16]
AGES = ["18-24", "25-30", "31-40", "41+"]
AGE_W = [0.22, 0.38, 0.28, 0.12]

CATEGORIES = {
    "数码": (600, 4800, 0.8),
    "家居": (120, 1600, 0.5),
    "美妆": (80, 900, 1.2),
    "食品": (20, 260, 1.6),
    "服饰": (90, 1200, 1.0),
}

START = date(2025, 1, 1)   # 订单统计起点（注册可以更早）
END = date(2026, 9, 30)
PROMO_MONTHS = {"2025-11": 2.6, "2026-06": 2.1}


def month_list():
    out = []
    y, m = 2025, 1
    while (y, m) <= (2026, 9):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


MONTHS = month_list()


def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


def weighted(seq, weights):
    return RNG.choices(seq, weights=weights, k=1)[0]


def make_users(n=1500):
    rows = []
    for uid in range(1, n + 1):
        # 注册日期：前期平稳、后期略增，方便做队列留存
        r = RNG.random()
        if r < 0.55:
            d0, d1 = date(2024, 1, 1), date(2024, 12, 31)
        elif r < 0.85:
            d0, d1 = date(2025, 1, 1), date(2025, 12, 31)
        else:
            d0, d1 = date(2026, 1, 1), date(2026, 9, 30)
        span = (d1 - d0).days
        signup = d0 + timedelta(days=RNG.randint(0, span))
        rows.append(
            (
                uid,
                signup.isoformat(),
                weighted(CITIES, CITY_W),
                weighted(CHANNELS, CH_WEIGHT),
                weighted(AGES, AGE_W),
            )
        )
    return rows


def make_products():
    rows = []
    pid = 1
    for cat, (lo, hi, _w) in CATEGORIES.items():
        for i in range(1, 6):
            price = round(RNG.uniform(lo, hi), 2)
            rows.append((pid, cat, f"{cat}-{i:02d}", price))
            pid += 1
    return rows


def promo_factor(d: date):
    key = f"{d.year:04d}-{d.month:02d}"
    if key in PROMO_MONTHS:
        # 大促集中在当月 10-20 日
        return PROMO_MONTHS[key] if 10 <= d.day <= 20 else 1.0
    return 1.0


def make_orders(users, products):
    by_cat = {}
    for p in products:
        by_cat.setdefault(p[1], []).append(p)

    orders = []
    oid = 1
    for uid, signup, city, channel, age in users:
        s = max(date.fromisoformat(signup), START)
        # 活跃度分层：10% 高频、45% 中频、45% 低频
        r = RNG.random()
        lam = 2.4 if r < 0.10 else (0.9 if r < 0.55 else 0.2)

        n_orders = 0
        for d in daterange(s, END):
            base = lam / 30.0 * promo_factor(d)
            if RNG.random() < base:
                n_orders += 1
                if n_orders > 60:
                    break
                cat = weighted(list(CATEGORIES), [0.30, 0.18, 0.20, 0.20, 0.12])
                prod = RNG.choice(by_cat[cat])
                qty = 1 if cat != "食品" else RNG.choice([1, 1, 2, 3])
                amount = round(prod[3] * qty * RNG.uniform(0.82, 1.0), 2)
                hour = RNG.randint(8, 23)
                minute = RNG.randint(0, 59)
                created = datetime(d.year, d.month, d.day, hour, minute)

                status = "paid"
                rr = RNG.random()
                if rr < 0.055:
                    status = "refunded"
                elif rr < 0.155:
                    status = "cancelled"

                # 造一个退款异常：美妆在 2026-03 退款率明显偏高
                if cat == "美妆" and f"{d.year:04d}-{d.month:02d}" == "2026-03" and RNG.random() < 0.16:
                    status = "refunded"

                paid = None
                if status != "cancelled":
                    paid = (created + timedelta(minutes=RNG.randint(1, 180))).strftime("%Y-%m-%d %H:%M:%S")

                orders.append(
                    (
                        oid,
                        uid,
                        prod[0],
                        qty,
                        amount,
                        status,
                        created.strftime("%Y-%m-%d %H:%M:%S"),
                        paid,
                        channel,
                        cat,
                    )
                )
                oid += 1
    return orders


def make_events(orders):
    """订单反推埋点：每单 点击 → 加购 → 下单 → 支付；再补一部分只看不买的点击。"""
    events = []
    eid = 1
    for o in orders:
        oid, uid, pid, qty, amount, status, created, paid, channel, cat = o
        t0 = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
        events.append((eid, uid, channel, "点击", (t0 - timedelta(minutes=RNG.randint(6, 90))).strftime("%Y-%m-%d %H:%M:%S")))
        eid += 1
        if RNG.random() < 0.82:
            events.append((eid, uid, channel, "加购", (t0 - timedelta(minutes=RNG.randint(1, 5))).strftime("%Y-%m-%d %H:%M:%S")))
            eid += 1
        events.append((eid, uid, channel, "下单", created))
        eid += 1
        if status != "cancelled":
            events.append((eid, uid, channel, "支付", paid))
            eid += 1

    # 加购了但没下单：约为订单量的 0.55 倍
    n_cart_drop = int(len(orders) * 0.55)
    for _ in range(n_cart_drop):
        o = RNG.choice(orders)
        uid, channel = o[1], o[8]
        d = START + timedelta(days=RNG.randint(0, (END - START).days))
        ts = datetime(d.year, d.month, d.day, RNG.randint(8, 23), RNG.randint(0, 59))
        events.append((eid, uid, channel, "加购", ts.strftime("%Y-%m-%d %H:%M:%S")))
        eid += 1

    # 一小部分“高频用户”连续 N 天来（给 Q7 连续活跃题准备真实的连续段）
    streak_users = RNG.sample([o[1] for o in orders], k=max(1, len(orders) // 900))
    for uid in set(streak_users):
        ch = RNG.choice(CHANNELS)
        start = START + timedelta(days=RNG.randint(0, (END - START).days - 40))
        length = RNG.randint(12, 34)
        for k in range(length):
            d = start + timedelta(days=k)
            ts = datetime(d.year, d.month, d.day, RNG.randint(9, 22), RNG.randint(0, 59))
            events.append((eid, uid, ch, "点击", ts.strftime("%Y-%m-%d %H:%M:%S")))
            eid += 1

    # 只看不买的点击：约等于已成交点击的 1.6 倍
    n_extra = int(len(orders) * 1.6)
    for _ in range(n_extra):
        o = RNG.choice(orders)
        uid, channel = o[1], o[8]
        d = START + timedelta(days=RNG.randint(0, (END - START).days))
        ts = datetime(d.year, d.month, d.day, RNG.randint(8, 23), RNG.randint(0, 59))
        events.append((eid, uid, channel, "点击", ts.strftime("%Y-%m-%d %H:%M:%S")))
        eid += 1
    return events


def make_impressions(events):
    clicks = {}
    for e in events:
        if e[3] != "点击":
            continue
        key = (e[2], e[4][:7])
        clicks[key] = clicks.get(key, 0) + 1

    rows = []
    for ch in CHANNELS:
        for m in MONTHS:
            c = clicks.get((ch, m), 0)
            ctr = CH_CTR[ch] * RNG.uniform(0.9, 1.1)
            rows.append((ch, m, max(200, int(c / ctr))))
    return rows


def make_spend():
    rows = []
    for ch in CHANNELS:
        for m in MONTHS:
            f = PROMO_MONTHS.get(m, 1.0) ** 0.5
            rows.append((ch, m, round(CH_SPEND_BASE[ch] * f * RNG.uniform(0.85, 1.15), 2)))
    return rows


def main():
    force = "--force" in sys.argv
    if os.path.exists(DB) and not force:
        print(f"data.db 已存在，跳过生成。要重建请加 --force")
        return

    if os.path.exists(DB):
        os.remove(DB)

    con = sqlite3.connect(DB)
    con.executescript(open(SCHEMA, encoding="utf-8").read())

    users = make_users()
    products = make_products()
    orders = make_orders([(u[0], u[1], u[2], u[3], u[4]) for u in users], products)
    events = make_events(orders)
    imps = make_impressions(events)
    spend = make_spend()

    con.executemany("INSERT INTO users VALUES (?,?,?,?,?)", users)
    con.executemany("INSERT INTO products VALUES (?,?,?,?)", products)
    con.executemany(
        "INSERT INTO orders (order_id,user_id,product_id,quantity,amount,status,created_at,paid_at) VALUES (?,?,?,?,?,?,?,?)",
        [o[:8] for o in orders],
    )
    con.executemany("INSERT INTO events VALUES (?,?,?,?,?)", events)
    con.executemany("INSERT INTO impressions VALUES (?,?,?)", imps)
    con.executemany("INSERT INTO channel_spend VALUES (?,?,?)", spend)
    con.commit()

    stats = {
        "users": con.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "products": con.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "orders": con.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "events": con.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        "gmv_paid": con.execute("SELECT ROUND(SUM(amount),2) FROM orders WHERE status='paid'").fetchone()[0],
    }
    con.close()
    print("data.db 生成完成：", stats)


if __name__ == "__main__":
    main()
