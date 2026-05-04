#!/usr/bin/env python3
"""DavyLinks: 飞书多维表格操作

将每日抓取的文章写入飞书多维表格（Bitable）。
使用飞书开放平台 API（tenant_access_token）。

用法:
    python feishu_bitable.py --test                     # 测试连接
    python feishu_bitable.py --input result.json        # 写入表格
    echo '...' | python feishu_bitable.py               # 从 stdin 读取
"""

import json
import sys
import os
import urllib.request
from datetime import datetime

# ============================================================
# 配置读取（从 secrets.yaml 或环境变量）
# ============================================================

def load_feishu_config():
    """从 secrets.yaml 加载飞书配置，fallback 到环境变量"""
    # 尝试从环境变量读取（最优先）
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL")
    bitable_token = os.environ.get("FEISHU_BITABLE_TOKEN")
    bitable_table_id = os.environ.get("FEISHU_TABLE_ID")

    if app_id and app_secret:
        # 环境变量已配置，直接返回
        return {
            "app_id": app_id,
            "app_secret": app_secret,
            "webhook_url": webhook_url or "https://open.feishu.cn/open-apis/bot/v2/hook/default",
            "bitable_token": bitable_token or "",
            "bitable_table_id": bitable_table_id or "",
        }

    # 尝试从 secrets.yaml 读取
    config_paths = [
        os.path.expanduser("~/.davylinks/secrets.yaml"),
        os.path.join(os.path.dirname(__file__), "..", "config", "secrets.yaml"),
    ]

    for config_path in config_paths:
        if os.path.exists(config_path):
            try:
                try:
                    import yaml
                    with open(config_path, "r") as f:
                        config = yaml.safe_load(f)
                except ImportError:
                    config = _parse_yaml_simple(config_path)

                feishu = config.get("feishu", {})
                return {
                    "app_id": feishu.get("app_id", ""),
                    "app_secret": feishu.get("app_secret", ""),
                    "webhook_url": feishu.get("webhook_url", ""),
                    "bitable_token": feishu.get("bitable", {}).get("app_token", ""),
                    "bitable_table_id": feishu.get("bitable", {}).get("table_id", ""),
                }
            except Exception as e:
                print(f"[WARN] 读取飞书配置失败：{e}", file=sys.stderr)

    # 默认返回（会在运行时提示错误）
    return {
        "app_id": "",
        "app_secret": "",
        "webhook_url": "",
        "bitable_token": "",
        "bitable_table_id": "",
    }


def _parse_yaml_simple(path):
    """简易 YAML 解析（不依赖 PyYAML）"""
    result = {}
    current_top = None
    current_mid = None

    with open(path, "r") as f:
        for line in f:
            stripped = line.rstrip()
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(line.lstrip())

            m = re.match(r'^(\w[^:]*):\s*$', stripped)
            if m and indent == 0:
                current_top = m.group(1).strip()
                current_mid = None
                if current_top not in result:
                    result[current_top] = {}
                continue

            m = re.match(r'^\s{2}(\w+):\s*(.+)$', stripped)
            if m and indent == 2 and current_top:
                key = m.group(1)
                val = m.group(2).strip().strip('"').strip("'")
                if isinstance(result.get(current_top), dict):
                    result[current_top][key] = val
                continue

            m = re.match(r'^\s{2}(\w[^:]*):\s*$', stripped)
            if m and indent == 2 and current_top:
                current_mid = m.group(1).strip()
                if isinstance(result.get(current_top), dict):
                    result[current_top][current_mid] = {}
                continue

            m = re.match(r'^\s{4}(\w+):\s*(.+)$', stripped)
            if m and indent == 4 and current_top and current_mid:
                key = m.group(1)
                val = m.group(2).strip().strip('"').strip("'")
                if isinstance(result.get(current_top, {}).get(current_mid), dict):
                    result[current_top][current_mid][key] = val
                continue

    return result


# 加载配置
_feishu_config = load_feishu_config()

# 飞书应用凭证（从配置加载）
FEISHU_APP_ID = _feishu_config["app_id"]
FEISHU_APP_SECRET = _feishu_config["app_secret"]
FEISHU_WEBHOOK = _feishu_config["webhook_url"]

# 多维表格（应用自动创建，自带权限）
BITABLE_APP_TOKEN = _feishu_config["bitable_token"]
BITABLE_TABLE_ID = _feishu_config["bitable_table_id"]
BITABLE_URL = f"https://my.feishu.cn/base/{BITABLE_APP_TOKEN}" if BITABLE_APP_TOKEN else ""

# Token 缓存
_token_cache = {"token": None, "expire_at": 0}


def get_tenant_token():
    """获取飞书 tenant_access_token（带缓存）"""
    now = datetime.now().timestamp()
    if _token_cache["token"] and now < _token_cache["expire_at"]:
        return _token_cache["token"]

    payload = json.dumps({
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=payload, method="POST",
    )
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") != 0:
            raise RuntimeError(f"获取 token 失败: {data}")

        _token_cache["token"] = data["tenant_access_token"]
        _token_cache["expire_at"] = now + data.get("expire", 7200) - 60
        return _token_cache["token"]


def bitable_request(method, path, body=None):
    """发送飞书 Bitable API 请求"""
    token = get_tenant_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{BITABLE_TABLE_ID}{path}"

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def add_record(fields_data):
    """添加一条记录到多维表格"""
    body = {"fields": fields_data}
    result = bitable_request("POST", "/records", body)
    if result.get("code") != 0:
        print(f"[WARN] 写入失败: {result.get('msg', result)}", file=sys.stderr)
        return False
    return True


def batch_add_records(records):
    """批量添加记录（每批最多 500 条）"""
    batch_size = 500
    total_ok = 0
    total_fail = 0

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        body = {"records": [{"fields": r} for r in batch]}
        result = bitable_request("POST", "/records/batch_create", body)

        if result.get("code") != 0:
            print(f"[WARN] 批量写入失败: {result.get('msg', result)}", file=sys.stderr)
            # 降级为逐条写入
            for r in batch:
                if add_record(r):
                    total_ok += 1
                else:
                    total_fail += 1
        else:
            total_ok += len(batch)

    return total_ok, total_fail


def article_to_fields(article, today_str=None):
    """将文章/话题对象转换为飞书表格字段"""
    if not today_str:
        today_str = datetime.now().strftime("%Y-%m-%d")

    source_count = article.get("source_count", 1)
    source_list = article.get("source_list", [article.get("source", "")])
    is_cross = source_count > 1

    # 日期转毫秒时间戳
    try:
        dt = datetime.strptime(today_str, "%Y-%m-%d")
        date_ts = int(dt.timestamp() * 1000)
    except ValueError:
        date_ts = int(datetime.now().timestamp() * 1000)

    fields = {
        "日期": date_ts,
        "标题": article.get("title", "(无标题)"),
        "来源": article.get("source", ""),
        "来源列表": "、".join(source_list),
        "来源数量": source_count,
        "分类": article.get("category", ""),
        "摘要": article.get("summary", article.get("description", "")),
        "热度评分": article.get("final_score", article.get("relevance_score", 0)),
        "是否多源交叉": is_cross,
    }

    # 链接 - 飞书超链接字段格式: {"link": url, "text": display}
    url = article.get("url", "")
    if url:
        fields["链接"] = {"link": url, "text": article.get("title", url)[:80]}

    return fields


def write_articles_to_bitable(articles, today_str=None):
    """将文章列表写入飞书多维表格"""
    if not articles:
        print("[INFO] 没有文章需要写入表格", file=sys.stderr)
        return 0, 0

    if not today_str:
        today_str = datetime.now().strftime("%Y-%m-%d")

    records = [article_to_fields(a, today_str) for a in articles]
    ok, fail = batch_add_records(records)

    print(f"[OK] 飞书表格写入: {ok} 成功, {fail} 失败", file=sys.stderr)
    return ok, fail


def test_connection():
    """测试飞书 API 连接"""
    try:
        token = get_tenant_token()
        print(f"[OK] Token 获取成功: {token[:15]}...")

        # 读取表格字段
        result = bitable_request("GET", "/fields")
        if result.get("code") == 0:
            fields = result.get("data", {}).get("items", [])
            print(f"[OK] 表格连接成功，共 {len(fields)} 个字段:")
            for f in fields:
                print(f"  - {f.get('field_name', '?')} (type={f.get('type', '?')})")
        else:
            print(f"[ERROR] 读取字段失败: {result}")

        print(f"\n表格地址: {BITABLE_URL}")

    except Exception as e:
        print(f"[ERROR] 连接失败: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DavyLinks 飞书多维表格")
    parser.add_argument("--test", action="store_true", help="测试连接")
    parser.add_argument("--input", help="从 JSON 文件读取文章")
    args = parser.parse_args()

    if args.test:
        test_connection()
        return

    # 读取文章数据
    if args.input:
        with open(args.input, "r") as f:
            data = json.load(f)
    elif not sys.stdin.isatty():
        data = json.load(sys.stdin)
    else:
        print("[ERROR] 请通过管道或 --input 提供数据", file=sys.stderr)
        sys.exit(1)

    articles = data.get("articles", data if isinstance(data, list) else [])
    today = data.get("date", datetime.now().strftime("%Y-%m-%d"))

    ok, fail = write_articles_to_bitable(articles, today)

    # 输出结果供 pipeline 使用
    print(json.dumps({"bitable_ok": ok, "bitable_fail": fail}))


if __name__ == "__main__":
    main()
