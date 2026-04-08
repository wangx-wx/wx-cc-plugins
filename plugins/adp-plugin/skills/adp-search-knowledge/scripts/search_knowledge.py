#!/usr/bin/env python3
"""调用 ADP SearchKnowledgeRelease 接口进行知识检索（发布环境）。

重要限制：
1. 此接口只支持检索应用（App），必须传入 AppBizId，不支持直接传入共享知识库的 KnowledgeBizId。
2. 应用必须处于「运行中」状态才能被检索。
3. 文档的 EnableScope 必须包含发布域（值为 3 或 4）才能被检索到。

使用方式：
    # 基础检索
    python search_knowledge.py <AppBizId> "检索问题"

    # 检查文档 EnableScope
    python search_knowledge.py <AppBizId> --check

    # 修复 EnableScope（需用户确认）
    python search_knowledge.py <AppBizId> --fix

    # 列出所有应用（获取 AppBizId）
    python search_knowledge.py --list-apps

    # 全局搜索文档
    python search_knowledge.py --search-all 关键词

依赖：pip install requests
"""
import os
import sys
import json
import argparse
import requests


# ============================================================
# 接口地址
# 格式：https://adp.cloud.tencent.com/plugin/api/v1/{app_id}/{tool_id}
# ============================================================
APP_ID = "4270baf0-d5a6-4b9f-b29a-38cebc821753"

SEARCH_KNOWLEDGE_URL = f"https://adp.cloud.tencent.com/plugin/api/v1/{APP_ID}/05813dd1-dbf4-4314-badb-4985bb2594e6"
LIST_APP_URL = f"https://adp.cloud.tencent.com/plugin/api/v1/{APP_ID}/2506ec47-456e-430c-9904-42a30ae27f3c"
LIST_DOC_URL = f"https://adp.cloud.tencent.com/plugin/api/v1/{APP_ID}/04a95e35-b22c-41d8-be6a-0120768ec5aa"
DESCRIBE_DOC_URL = f"https://adp.cloud.tencent.com/plugin/api/v1/{APP_ID}/0b616bb2-9e21-40e2-b571-a83542a8123d"
MODIFY_DOC_URL = f"https://adp.cloud.tencent.com/plugin/api/v1/{APP_ID}/3b4b1f44-509d-4efa-988f-e16e2d36f409"
LIST_SHARED_KB_URL = f"https://adp.cloud.tencent.com/plugin/api/v1/{APP_ID}/88dce784-32d6-4689-a527-ec969d0f6228"
LIST_REFER_SHARE_KB_URL = f"https://adp.cloud.tencent.com/plugin/api/v1/{APP_ID}/6fd5da0f-5540-4ffd-a05c-805129f9857d"

ENABLE_SCOPE_DESC = {
    1: "不生效",
    2: "仅开发域生效",
    3: "仅发布域生效",
    4: "开发域和发布域均生效",
}


# ============================================================
# 密钥加载
# ============================================================
def _load_api_key():
    """多路径加载 ADP_API_KEY，优先级：环境变量 > /etc/environment > ~/.env > .env"""
    key = os.environ.get("ADP_API_KEY", "")
    if key:
        return key
    for env_file in ["/etc/environment", os.path.expanduser("~/.env"), ".env"]:
        if os.path.isfile(env_file):
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("ADP_API_KEY="):
                            val = line.split("=", 1)[1].strip().strip("'\"")
                            if val:
                                os.environ["ADP_API_KEY"] = val
                                return val
            except (IOError, PermissionError):
                continue
    return ""


# ============================================================
# 通用请求函数
# ============================================================
def _post(url, payload, api_key):
    """发送 POST 请求到 ADP 插件 API"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
    except requests.exceptions.Timeout:
        return {"success": False, "error": "请求超时，请重试"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"请求异常: {str(e)}"}

    if resp.status_code == 401:
        return {"success": False, "error": "401 Unauthorized: API Key 无效或未设置，请重新获取密钥"}
    if resp.status_code != 200:
        return {"success": False, "error": f"请求失败，状态码: {resp.status_code}, 响应: {resp.text}"}

    try:
        data = resp.json()
    except json.JSONDecodeError:
        return {"success": False, "error": f"响应解析失败: {resp.text}"}

    code = data.get("Code", -1)
    msg = data.get("Msg", "")
    if code != 0:
        if code == 3000003 or "quota" in msg.lower():
            return {"success": False, "error": f"配额不足: Code={code}, Msg={msg}\n请前往 https://buy.cloud.tencent.com/adp 购买套餐或增购包后重试。"}
        return {"success": False, "error": f"接口返回错误: Code={code}, Msg={msg}"}

    return {"success": True, "data": data.get("Data", {})}


def _parse_list_items(result, list_key="List"):
    """ADP API 返回的列表字段中每个元素可能是 JSON 字符串而非字典，需二次解析。"""
    if not result.get("success"):
        return result
    items = result.get("data", {}).get(list_key, [])
    parsed = []
    for item in items:
        if isinstance(item, str):
            try:
                parsed.append(json.loads(item))
            except (json.JSONDecodeError, TypeError):
                parsed.append(item)
        else:
            parsed.append(item)
    result["data"]["List"] = parsed
    if list_key != "List" and list_key in result["data"]:
        del result["data"][list_key]
    return result


# ============================================================
# 业务函数
# ============================================================
def search_knowledge(api_key, app_biz_id, question, custom_variables=None, visitor_biz_id=None):
    """调用 SearchKnowledgeRelease 接口

    Args:
        api_key: ADP API Key
        app_biz_id: 应用 ID（必须是运行中的应用）
        question: 检索问题
        custom_variables: 自定义变量列表，格式 [{"Name": "xxx", "Value": "xxx"}]
        visitor_biz_id: 访客 ID

    Returns:
        dict: {"success": True/False, "data": {...}} 或 {"success": False, "error": "..."}
    """
    payload = {
        "AppBizId": app_biz_id,
        "Question": question,
    }
    if custom_variables:
        payload["CustomVariables"] = custom_variables
    if visitor_biz_id:
        payload["VisitorBizId"] = visitor_biz_id

    return _post(SEARCH_KNOWLEDGE_URL, payload, api_key)


def list_app(api_key, page_number=1, page_size=50, keyword=None):
    """列出所有智能体应用"""
    payload = {
        "PageNumber": page_number,
        "PageSize": page_size,
    }
    if keyword:
        payload["Keyword"] = keyword
    return _parse_list_items(_post(LIST_APP_URL, payload, api_key))


def list_all_docs(api_key, bot_biz_id):
    """获取知识库全部文档列表（自动分页）"""
    all_docs = []
    page = 1
    while True:
        payload = {
            "BotBizId": bot_biz_id,
            "PageNumber": page,
            "PageSize": 50,
        }
        result = _post(LIST_DOC_URL, payload, api_key)
        if not result.get("success"):
            return result
        data = result["data"]
        docs = data.get("List", [])
        parsed_docs = []
        for item in docs:
            if isinstance(item, str):
                try:
                    parsed_docs.append(json.loads(item))
                except (json.JSONDecodeError, TypeError):
                    parsed_docs.append(item)
            else:
                parsed_docs.append(item)
        all_docs.extend(parsed_docs)
        total = int(data.get("Total", 0))
        if len(all_docs) >= total:
            break
        page += 1
    return {"success": True, "data": {"List": all_docs, "Total": str(len(all_docs))}}


def describe_doc(api_key, bot_biz_id, doc_biz_id):
    """调用 DescribeDoc 获取文档详细信息"""
    payload = {
        "BotBizId": bot_biz_id,
        "DocBizId": doc_biz_id,
    }
    return _post(DESCRIBE_DOC_URL, payload, api_key)


def modify_doc_enable_scope(api_key, bot_biz_id, doc_biz_id, is_refer, attr_range, enable_scope):
    """调用 ModifyDoc 修改文档的 EnableScope"""
    payload = {
        "BotBizId": bot_biz_id,
        "DocBizId": doc_biz_id,
        "IsRefer": is_refer,
        "AttrRange": attr_range,
        "EnableScope": enable_scope,
    }
    return _post(MODIFY_DOC_URL, payload, api_key)


def list_shared_knowledge(api_key, page_number=1, page_size=20, keyword=None):
    """列出所有共享知识库"""
    payload = {
        "PageNumber": page_number,
        "PageSize": page_size,
    }
    if keyword:
        payload["Keyword"] = keyword
    return _parse_list_items(_post(LIST_SHARED_KB_URL, payload, api_key), list_key="KnowledgeList")


def list_refer_share_knowledge(api_key, app_biz_id, page_number=1, page_size=20):
    """查询应用关联的共享知识库"""
    payload = {
        "AppBizId": app_biz_id,
        "PageNumber": page_number,
        "PageSize": page_size,
    }
    return _parse_list_items(_post(LIST_REFER_SHARE_KB_URL, payload, api_key))


def search_all_docs(api_key, keyword):
    """在所有应用的默认知识库和所有共享知识库中，按文件名关键词搜索文档。"""
    found = []

    # 1. 遍历所有应用的默认知识库
    r = list_app(api_key)
    if r.get("success"):
        for app in r["data"].get("List", []):
            name = app.get("Name", "?")
            app_biz_id = app.get("AppBizId", "")
            try:
                result = list_all_docs(api_key, app_biz_id)
                if isinstance(result, dict) and result.get("success"):
                    for d in result["data"].get("List", []):
                        fn = d.get("FileName", "")
                        if keyword.lower() in fn.lower():
                            found.append({
                                "source": f"应用「{name}」默认知识库",
                                "source_type": "app",
                                "bot_biz_id": app_biz_id,
                                "file_name": fn,
                                "doc_biz_id": d.get("DocBizId", ""),
                            })
            except Exception:
                pass

    # 2. 遍历所有共享知识库
    r2 = list_shared_knowledge(api_key)
    if r2.get("success"):
        for kb in r2["data"].get("List", []):
            kb_name = kb.get("KnowledgeName", "?")
            kb_id = kb.get("KnowledgeBizId", "")
            try:
                result = list_all_docs(api_key, kb_id)
                if isinstance(result, dict) and result.get("success"):
                    for d in result["data"].get("List", []):
                        fn = d.get("FileName", "")
                        if keyword.lower() in fn.lower():
                            found.append({
                                "source": f"共享知识库「{kb_name}」",
                                "source_type": "shared_kb",
                                "bot_biz_id": kb_id,
                                "file_name": fn,
                                "doc_biz_id": d.get("DocBizId", ""),
                            })
            except Exception:
                pass

    return found


# ============================================================
# 应用状态检查
# ============================================================
def check_app_status(api_key, app_biz_id):
    """检查应用是否处于「运行中」状态

    Returns:
        (is_running, app_name, status_desc): 是否运行中、应用名称、状态描述
    """
    result = list_app(api_key)
    if not result.get("success"):
        return False, "", f"获取应用列表失败: {result.get('error', '')}"

    apps = result["data"].get("List", [])
    for app in apps:
        if app.get("AppBizId") == app_biz_id:
            status_desc = app.get("AppStatusDesc", "未知")
            app_name = app.get("Name", "")
            is_running = status_desc == "运行中"
            return is_running, app_name, status_desc

    return False, "", "未找到该应用（可能传入了共享知识库 ID 而非应用 AppBizId）"


# ============================================================
# EnableScope 检查与修复
# ============================================================
def check_enable_scope(api_key, app_biz_id, max_check=10):
    """检查文档的 EnableScope，返回 (searchable, unsearchable)"""
    result = list_all_docs(api_key, app_biz_id)
    if not result.get("success"):
        print(f"获取文档列表失败: {result.get('error', '')}")
        return [], []

    docs = result["data"].get("List", [])
    if not docs:
        return [], []

    searchable = []
    unsearchable = []

    for doc in docs[:max_check]:
        doc_biz_id = doc.get("DocBizId", "")
        file_name = doc.get("FileName", "")

        detail_result = describe_doc(api_key, app_biz_id, doc_biz_id)
        if not detail_result.get("success"):
            print(f"  跳过文档 {file_name}: {detail_result.get('error', '')}")
            continue

        detail = detail_result["data"]
        scope = detail.get("EnableScope", 0)
        status = detail.get("Status", 0)
        status_desc = detail.get("StatusDesc", "")

        info = {
            "FileName": file_name,
            "DocBizId": doc_biz_id,
            "EnableScope": scope,
            "EnableScopeDesc": ENABLE_SCOPE_DESC.get(scope, f"未知({scope})"),
            "Status": status,
            "StatusDesc": status_desc,
            "IsRefer": detail.get("IsRefer", False),
            "AttrRange": detail.get("AttrRange", 1),
        }

        if scope in (3, 4):
            searchable.append(info)
        else:
            unsearchable.append(info)

    return searchable, unsearchable


def batch_modify_enable_scope(api_key, app_biz_id, docs_info, target_scope=4):
    """批量修改文档的 EnableScope

    Args:
        api_key: ADP API Key
        app_biz_id: 应用 ID
        docs_info: 文档信息列表（包含 DocBizId, IsRefer, AttrRange）
        target_scope: 目标 EnableScope 值
    """
    results = []
    for doc in docs_info:
        doc_id = doc["DocBizId"]
        is_refer = doc.get("IsRefer", False)
        attr_range = doc.get("AttrRange", 1)
        result = modify_doc_enable_scope(api_key, app_biz_id, doc_id, is_refer, attr_range, target_scope)
        results.append({
            "DocBizId": doc_id,
            "FileName": doc.get("FileName", ""),
            "success": result.get("success", False),
            "error": result.get("error", ""),
        })
    return results


# ============================================================
# 结果展示
# ============================================================
def show_search_results(result):
    """展示检索结果

    Returns:
        bool: 是否有检索结果
    """
    if not result.get("success"):
        print(f"检索失败: {result.get('error', '')}")
        # 检查是否为 token/配额不足错误
        err_msg = result.get("error", "").lower()
        quota_keywords = ["token", "quota", "limit", "exceed", "容量", "资源", "配额", "超限", "不足"]
        if any(kw in err_msg for kw in quota_keywords):
            print("=" * 50)
            print("⚠️ 该错误可能是因为检索模型剩余 token 不足，或未订阅 ADP 付费套餐 / 套餐资源已耗尽。")
            print("  解决方案：")
            print("  1. 前往 ADP 购买页订阅专业版或企业版套餐：")
            print("     https://buy.cloud.tencent.com/adp")
            print("  2. 已有套餐可增购预付费资源包（PU 资源包）")
            print("  3. 免费版不支持 PU 资源充值，需先升级为付费套餐")
            print("  购买方式详情：https://cloud.tencent.com/document/product/1759/127528")
        return False

    data = result["data"]

    # ADP 插件 API 返回格式：Data 中直接包含 KnowledgeList
    knowledge_list = data.get("KnowledgeList", []) or []

    # 处理可能的 JSON 字符串元素
    parsed_list = []
    for item in knowledge_list:
        if isinstance(item, str):
            try:
                parsed_list.append(json.loads(item))
            except (json.JSONDecodeError, TypeError):
                parsed_list.append(item)
        else:
            parsed_list.append(item)

    print(f"检索到 {len(parsed_list)} 条知识\n")

    for i, item in enumerate(parsed_list, 1):
        if isinstance(item, dict):
            k_type = item.get("KnowledgeType", "")
            title = item.get("Title", "")
            doc_name = item.get("DocName", "")
            content = item.get("Content", "")
            related_doc_id = item.get("RelatedDocId", "")
            question = item.get("Question", "")

            print(f"[{i}] 类型: {k_type}")
            if title:
                print(f"    标题: {title}")
            if question:
                print(f"    问题: {question}")
            if doc_name:
                print(f"    文档: {doc_name}")
            if related_doc_id:
                print(f"    文档ID: {related_doc_id}")
            if content:
                preview = content[:300] + "..." if len(content) > 300 else content
                print(f"    内容: {preview}")
            print()
        else:
            print(f"[{i}] {item}")

    if not parsed_list:
        print("未检索到相关知识。")
        print("\n可能原因：")
        print("  1. 应用不是「运行中」状态（只有运行中的应用才能被检索）")
        print("  2. 传入了共享知识库 ID 而非应用 AppBizId（不支持直接检索共享知识库）")
        print("  3. 文档的 EnableScope 未包含发布域（最常见原因）")
        print("  4. 文档未成功导入/解析")
        print("  5. 检索词与知识库内容匹配度不高")
        print(f"\n建议运行 EnableScope 检查：python3 search_knowledge.py <AppBizId> --check")

    return len(parsed_list) > 0


# ============================================================
# 命令行入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="ADP 知识库知识检索（SearchKnowledgeRelease）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python search_knowledge.py <AppBizId> "检索问题"     # 基础检索
  python search_knowledge.py <AppBizId> --check        # 检查 EnableScope
  python search_knowledge.py <AppBizId> --fix          # 修复 EnableScope（需确认）
  python search_knowledge.py --list-apps               # 列出所有应用
  python search_knowledge.py --search-all 关键词       # 全局搜索文档

注意：
  - 此接口只支持检索应用（App），不支持共享知识库
  - 应用必须处于「运行中」状态
  - 文档 EnableScope 须包含发布域（值 3 或 4）
        """,
    )

    parser.add_argument("app_biz_id", nargs="?", default=None,
                        help="应用 ID（AppBizId）。--list-apps / --search-all 模式时不需要")
    parser.add_argument("question", nargs="?", default=None,
                        help="检索问题")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true",
                       help="检查文档 EnableScope（是否可被检索）")
    group.add_argument("--fix", action="store_true",
                       help="修复文档 EnableScope（改为 4，需用户交互确认）")
    group.add_argument("--list-apps", action="store_true",
                       help="列出所有智能体应用（获取 AppBizId）")
    group.add_argument("--search-all",
                       help="全局搜索：在所有应用和共享知识库中按文件名关键词搜索文档")

    args = parser.parse_args()

    api_key = _load_api_key()
    if not api_key:
        print("错误: 请设置 ADP_API_KEY 环境变量或在 /etc/environment / .env 文件中配置")
        sys.exit(1)

    # --list-apps 模式
    if args.list_apps:
        print("正在获取应用列表...\n")
        result = list_app(api_key)
        if not result["success"]:
            print(f"错误: {result['error']}")
            sys.exit(1)
        apps = result["data"].get("List", [])
        if not apps:
            print("当前账号下暂无应用。")
            return
        print(f"共 {len(apps)} 个应用：\n")
        for i, app in enumerate(apps, 1):
            status_desc = app.get("AppStatusDesc", "")
            searchable = "✅" if status_desc == "运行中" else "❌"
            print(f"  {i}. {app.get('Name', '')} (状态: {status_desc} {searchable}, AppBizId: {app.get('AppBizId', '')})")
        print("\n提示：只有状态为「运行中」✅ 的应用才能用于知识检索。")
        return

    # --search-all 模式
    if args.search_all:
        keyword = args.search_all
        print(f"正在所有知识库中搜索包含「{keyword}」的文档...\n")
        found = search_all_docs(api_key, keyword)
        if not found:
            print(f"未找到包含「{keyword}」的文档。")
            sys.exit(1)
        print(f"找到 {len(found)} 个匹配文档：\n")
        for i, f in enumerate(found, 1):
            print(f"  {i}. {f['source']} -> 文档「{f['file_name']}」")
            print(f"     DocBizId: {f['doc_biz_id']}, BotBizId: {f['bot_biz_id']}")
        return

    # 以下模式需要 AppBizId
    if not args.app_biz_id:
        print("错误：请提供 AppBizId。用法：python3 search_knowledge.py <AppBizId> \"问题\"")
        print("      或使用 --list-apps 查看所有应用。")
        sys.exit(1)

    app_biz_id = args.app_biz_id

    # --check 模式：检查 EnableScope
    if args.check:
        print(f"正在检查应用 {app_biz_id} 的文档 EnableScope...\n")
        searchable, unsearchable = check_enable_scope(api_key, app_biz_id)

        if not searchable and not unsearchable:
            print("知识库中暂无文档。")
            return

        if searchable:
            print(f"✅ 可被检索的文档 ({len(searchable)} 篇):")
            for d in searchable:
                print(f"   {d['FileName']} | EnableScope={d['EnableScope']} ({d['EnableScopeDesc']})")

        if unsearchable:
            print(f"\n❌ 不可被检索的文档 ({len(unsearchable)} 篇):")
            for d in unsearchable:
                print(f"   {d['FileName']} | EnableScope={d['EnableScope']} ({d['EnableScopeDesc']}) | 状态: {d['StatusDesc']}")
            print("\n这些文档需要将 EnableScope 修改为 3 或 4 才能被 SearchKnowledgeRelease 检索。")
            print(f"如需修复，运行：python3 search_knowledge.py {app_biz_id} --fix（会逐一列出并要求确认）")
        else:
            print("\n所有文档均可被 SearchKnowledgeRelease 检索。")
        return

    # --fix 模式：修复 EnableScope（需用户确认）
    if args.fix:
        print(f"正在检查应用 {app_biz_id} 的文档 EnableScope...\n")
        _, unsearchable = check_enable_scope(api_key, app_biz_id)

        if not unsearchable:
            print("所有文档的 EnableScope 已包含发布域，无需修复。")
            return

        print(f"发现 {len(unsearchable)} 篇文档的 EnableScope 未包含发布域，无法被 SearchKnowledgeRelease 检索：\n")
        for i, d in enumerate(unsearchable, 1):
            print(f"  {i}. {d['FileName']}")
            print(f"     当前: EnableScope={d['EnableScope']} ({d['EnableScopeDesc']})")
            print(f"     修改为: EnableScope=4 (开发域+发布域均生效)")
        print()

        # 交互式确认：必须征得用户同意
        try:
            confirm = input(f"是否将以上 {len(unsearchable)} 篇文档的 EnableScope 修改为 4？(y/N): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = ""
            print()

        if confirm != "y":
            print("已取消修改。文档的 EnableScope 保持不变。")
            return

        print(f"\n正在修改 {len(unsearchable)} 篇文档的 EnableScope...")
        results = batch_modify_enable_scope(api_key, app_biz_id, unsearchable, target_scope=4)

        success_count = sum(1 for r in results if r["success"])
        fail_count = len(results) - success_count
        print(f"\n修改完成！成功: {success_count}, 失败: {fail_count}")
        if fail_count > 0:
            for r in results:
                if not r["success"]:
                    print(f"  ❌ {r['FileName']}: {r['error']}")
        else:
            print("文档现在可以被 SearchKnowledgeRelease 检索。")
        return

    # 正常检索模式
    if not args.question:
        print("错误：请提供检索问题。用法：python3 search_knowledge.py <AppBizId> \"问题\"")
        sys.exit(1)

    question = args.question

    print(f"AppBizId: {app_biz_id}")
    print(f"Question: {question}")
    print("-" * 50)

    # 检查应用状态
    is_running, app_name, status_desc = check_app_status(api_key, app_biz_id)
    if app_name:
        print(f"应用名称: {app_name}")
    print(f"应用状态: {status_desc}")

    if not is_running:
        print(f"\n⚠️ 应用不是「运行中」状态（当前: {status_desc}）")
        print("SearchKnowledgeRelease 接口只能检索运行中的应用。")
        if "未找到" in status_desc:
            print("提示：您传入的 ID 可能是共享知识库的 KnowledgeBizId，而非应用的 AppBizId。")
            print("SearchKnowledgeRelease 不支持直接传入共享知识库 ID，请找到一个关联了")
            print("该共享知识库且状态为「运行中」的应用，使用该应用的 AppBizId 进行检索。")
        else:
            print("请先将该应用发布上线：")
            print("  1. 打开 ADP 控制台 → 点击「产品体验」进入平台")
            print("  2. 进入「应用开发」→ 找到目标应用 → 点击进入")
            print("  3. 点击右上角「发布」按钮 → 确认发布")
            print("  4. 发布成功后应用状态变为「运行中」，即可检索")
            print("  📖 详细教程：https://cloud.tencent.com/document/product/1759/104209")
        print("-" * 50)
        print("仍尝试检索（可能返回空结果）...\n")

    result = search_knowledge(api_key, app_biz_id, question)
    has_results = show_search_results(result)

    # 检索无结果时自动诊断
    if not has_results and result.get("success"):
        print("\n" + "=" * 50)
        print("自动诊断：正在检查应用状态和文档 EnableScope...")
        print("=" * 50 + "\n")

        # 第一步：检查应用状态
        if not is_running:
            print(f"⚠️ 诊断结果 [应用状态]：应用不是「运行中」状态（当前: {status_desc}）")
            print("  这是检索不到内容的最可能原因。")
            if "未找到" in status_desc:
                print("  您传入的 ID 可能是共享知识库的 KnowledgeBizId，而非应用的 AppBizId。")
                print("  请找到一个关联了该共享知识库且状态为「运行中」的应用进行检索。")
            else:
                print("  请将该应用发布上线：")
                print("    1. 打开 ADP 控制台 → 点击「产品体验」进入平台")
                print("    2. 进入「应用开发」→ 找到目标应用 → 点击进入")
                print("    3. 点击右上角「发布」按钮 → 确认发布")
                print("    4. 发布成功后应用状态变为「运行中」，即可检索")
                print("    📖 详细教程：https://cloud.tencent.com/document/product/1759/104209")
            print()

        # 第二步：检查文档 EnableScope
        searchable, unsearchable = check_enable_scope(api_key, app_biz_id, max_check=5)

        if not searchable and not unsearchable:
            print("诊断结果：知识库中暂无文档，请先上传文档。")
        elif unsearchable:
            print(f"诊断结果：发现 {len(unsearchable)} 篇文档未在发布域生效：\n")
            for d in unsearchable:
                print(f"  ❌ {d['FileName']} | EnableScope={d['EnableScope']} ({d['EnableScopeDesc']}) | 状态: {d['StatusDesc']}")
            print(f"\n这是检索不到内容的最可能原因。")
            print(f"检查详情：运行 python3 search_knowledge.py {app_biz_id} --check")
            print(f"确认修复：运行 python3 search_knowledge.py {app_biz_id} --fix（会逐一列出并要求确认）")
        else:
            # 检查文档状态
            abnormal = [d for d in searchable if d["Status"] not in (3, 9, 10)]
            if abnormal:
                print(f"诊断结果：发现 {len(abnormal)} 篇文档状态异常：\n")
                for d in abnormal:
                    print(f"  ⚠️ {d['FileName']} | 状态: {d['StatusDesc']} (Status={d['Status']})")
                print("\n这些文档可能未被正确索引，建议重试解析。")
            else:
                print("诊断结果：文档的 EnableScope 和状态均正常。")
                print("可能是检索词与知识库内容匹配度不高，建议换用更具体的检索词。")


if __name__ == "__main__":
    main()
