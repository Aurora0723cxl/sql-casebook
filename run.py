# -*- coding: utf-8 -*-
"""一键跑通：建库 → 依次执行 queries/*.sql → 打印结果并写出 RESULTS.md

用法：
    python run.py            # 跑全部查询
    python run.py --bench    # 顺便做一次索引对比实验
    python run.py q03        # 只跑文件名含 q03 的

依赖：只用 Python 标准库（sqlite3）。
"""
import os
import re
import sqlite3
import sys
import time
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data.db")
QDIR = os.path.join(HERE, "queries")
RESULTS = os.path.join(HERE, "RESULTS.md")
MAX_ROWS = 20


def build_if_missing():
    if os.path.exists(DB):
        return False
    sys.path.insert(0, HERE)
    import seed
    seed.main()
    return True


def disp_width(s):
    w = 0
    for ch in str(s):
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def pad(s, width, align="left"):
    s = str(s)
    gap = width - disp_width(s)
    if gap <= 0:
        return s
    return (" " * gap + s) if align == "right" else (s + " " * gap)


def fmt(v):
    if isinstance(v, float):
        return f"{v:,.2f}"
    if isinstance(v, int):
        return f"{v:,}"
    if v is None:
        return "-"
    return str(v)


def render_table(cols, rows, max_rows=MAX_ROWS):
    show = rows[:max_rows]
    cells = [[fmt(r[i]) for i in range(len(cols))] for r in show]
    widths = []
    for i, c in enumerate(cols):
        w = max([disp_width(c)] + [disp_width(r[i]) for r in cells]) if cells else disp_width(c)
        widths.append(min(w, 42))
    line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    out = [line, "| " + " | ".join(pad(c, widths[i]) for i, c in enumerate(cols)) + " |", line]
    for r in cells:
        out.append("| " + " | ".join(pad(r[i], widths[i], "right" if re.fullmatch(r"[-,\d.]+", r[i] or "") else "left") for i in range(len(cols))) + " |")
    out.append(line)
    if len(rows) > max_rows:
        out.append(f"（共 {len(rows)} 行，只显示前 {max_rows} 行）")
    return "\n".join(out)


def title_of(sql):
    for ln in sql.splitlines():
        m = re.match(r"--\s*(Q\d+.*)", ln.strip())
        if m:
            return m.group(1).strip()
    return os.path.basename("?")


def run_queries(files):
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    md = ["# 运行结果", "", "由 `python run.py` 自动生成，请勿手改。", ""]
    for path in files:
        sql = open(path, encoding="utf-8").read()
        title = title_of(sql)
        t0 = time.perf_counter()
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        ms = (time.perf_counter() - t0) * 1000

        print()
        print("=" * 78)
        print(f"{title}    [{os.path.basename(path)} · {len(rows)} 行 · {ms:.1f} ms]")
        print("=" * 78)
        print(render_table(cols, rows))

        md.append(f"## {title}")
        md.append("")
        md.append(f"`{os.path.basename(path)}` · {len(rows)} 行 · {ms:.1f} ms")
        md.append("")
        md.append("```")
        md.append(render_table(cols, rows))
        md.append("```")
        md.append("")
    con.close()
    return md


def bench():
    con = sqlite3.connect(DB)
    out = []
    n_rows = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    con.executescript("DROP INDEX IF EXISTS idx_orders_user; DROP INDEX IF EXISTS idx_orders_created;")

    def timeit(sql, params=(), n=200):
        t0 = time.perf_counter()
        for _ in range(n):
            con.execute(sql, params).fetchall()
        return (time.perf_counter() - t0) / n * 1000

    def plan(sql, params=()):
        return con.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()

    q_user = "SELECT order_id, amount FROM orders WHERE user_id = ?"
    q_recent = "SELECT order_id, created_at FROM orders ORDER BY created_at DESC LIMIT 100"
    q_month = "SELECT substr(created_at,1,7) ym, SUM(amount) FROM orders WHERE created_at >= ? GROUP BY 1"

    before_user = timeit(q_user, (1234,))
    before_recent = timeit(q_recent, n=50)
    before_month = timeit(q_month, ("2026-01-01",), n=50)
    plan_before_user = plan(q_user, (1234,))
    plan_before_recent = plan(q_recent)
    plan_before_month = plan(q_month, ("2026-01-01",))

    con.executescript(
        "CREATE INDEX idx_orders_user ON orders(user_id);"
        "CREATE INDEX idx_orders_created ON orders(created_at);"
    )
    con.commit()

    after_user = timeit(q_user, (1234,))
    after_recent = timeit(q_recent, n=50)
    after_month = timeit(q_month, ("2026-01-01",), n=50)
    plan_after_user = plan(q_user, (1234,))
    plan_after_recent = plan(q_recent)
    plan_after_month = plan(q_month, ("2026-01-01",))
    con.close()

    out.append(f"索引对比实验（orders 表 {n_rows:,} 行）")
    out.append("")
    out.append("| 查询 | 建索引前 | 建索引后 | 提速 |")
    out.append("|---|---|---|---|")
    out.append(f"| `WHERE user_id = 1234` | {before_user:.3f} ms | {after_user:.3f} ms | {before_user/max(after_user,0.001):.1f}× |")
    out.append(f"| `ORDER BY created_at DESC LIMIT 100` | {before_recent:.3f} ms | {after_recent:.3f} ms | {before_recent/max(after_recent,0.001):.1f}× |")
    out.append(f"| `WHERE created_at >= '2026-01-01'` + 按月聚合 | {before_month:.3f} ms | {after_month:.3f} ms | {before_month/max(after_month,0.001):.1f}× |")
    out.append("")
    out.append("执行计划（建索引前 → 建索引后）：")
    out.append("")
    out.append("```")
    out.append("-- WHERE user_id = ?")
    for r in plan_before_user:
        out.append("before: " + str(r[-1]))
    for r in plan_after_user:
        out.append("after : " + str(r[-1]))
    out.append("")
    out.append("-- ORDER BY created_at DESC LIMIT 100")
    for r in plan_before_recent:
        out.append("before: " + str(r[-1]))
    for r in plan_after_recent:
        out.append("after : " + str(r[-1]))
    out.append("")
    out.append("-- WHERE created_at >= ? + GROUP BY substr(created_at,1,7)")
    for r in plan_before_month:
        out.append("before: " + str(r[-1]))
    for r in plan_after_month:
        out.append("after : " + str(r[-1]))
    out.append("```")
    return out


def main():
    built = build_if_missing()
    if built:
        print("data.db 不存在，已自动生成。")

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = sorted(f for f in os.listdir(QDIR) if f.endswith(".sql"))
    if args:
        files = [f for f in files if any(a in f for a in args)]

    md = run_queries([os.path.join(QDIR, f) for f in files])

    if "--bench" in sys.argv:
        block = bench()
        print()
        print("\n".join(block))
        md += ["## 索引对比实验", ""] + block + [""]

    with open(RESULTS, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(md))
    print()
    print(f"结果已写入 {os.path.basename(RESULTS)}")


if __name__ == "__main__":
    main()
