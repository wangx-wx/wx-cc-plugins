# ADP API Key 获取指南

## 一、什么是 ADP API Key

ADP API Key 是调用 ADP 平台插件 API 时用于身份验证的密钥。使用 HTTP 请求头 `Authorization: Bearer {ADP_API_KEY}` 进行认证，无需复杂的签名计算。

## 二、获取步骤

### 主流程：通过密钥管理页面

1. 访问 [ADP 密钥管理页面](https://adp.cloud.tencent.com/adp?spaceId=default_space#/key-manage?spaceId=default_space)
2. 点击「**新建密钥**」
3. **立即保存**密钥（密钥仅创建时显示一次，之后无法查询）

> ⚠️ **注意**：密钥最多只能创建 **2 个**。如果提示已达上限，需要先删除旧的密钥再新建。

> 🔒 **权限说明**：如果无法访问密钥管理页面，说明当前账号权限不够，请联系管理员开通权限。

### 兜底流程（主流程链接未正常跳转时）

如果上述链接没有正常跳转到密钥管理页面，按以下步骤操作：

1. 访问 [ADP 控制台](https://adp.cloud.tencent.com/)
2. 点击「**产品体验**」按钮
3. 使用主账号登录
4. 点击右上角**头像** → 「**企业管理**」 → 「**密钥管理**」
5. 点击「**新建密钥**」

## 三、密钥存储

获取密钥后，推荐通过环境变量存储：

### 主方案：写入 /etc/environment（推荐，全局生效）

```bash
echo 'ADP_API_KEY=你的密钥' | sudo tee -a /etc/environment > /dev/null
source /etc/environment
```

### 兜底方案：写入 .env 文件（无 sudo 权限时）

```bash
echo 'ADP_API_KEY=你的密钥' >> .env
```

> ⚠️ **变量名必须为 `ADP_API_KEY`**，完全一致，不可更改。

## 四、如何获取 AppBizId

AppBizId 是 ADP 中智能体应用的唯一标识，调用 SearchKnowledgeRelease 时必须提供。

> **重要**：SearchKnowledgeRelease 只能检索**应用**（App），不支持直接传入共享知识库的 KnowledgeBizId。应用必须处于「运行中」状态。

### 方式一：调用 ListApp 接口查询（推荐）

调用 `ListApp` 接口可列出当前账号下所有智能体应用，每个应用的 `AppBizId` 即为所需 ID。

```python
import requests, json

APP_ID = "4270baf0-d5a6-4b9f-b29a-38cebc821753"
LIST_APP_URL = f"https://adp.cloud.tencent.com/plugin/api/v1/{APP_ID}/2506ec47-456e-430c-9904-42a30ae27f3c"

headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
payload = {"PageNumber": 1, "PageSize": 50}

resp = requests.post(LIST_APP_URL, headers=headers, json=payload, timeout=60)
data = resp.json()
# ⚠️ 注意：List 中每项是 JSON 字符串，需 json.loads 解析为字典
for item in data["Data"]["List"]:
    app = json.loads(item) if isinstance(item, str) else item
    status = app.get("AppStatusDesc", "")
    searchable = "✅" if status == "运行中" else "❌"
    print(f"名称: {app['Name']}, 状态: {status} {searchable}, AppBizId: {app['AppBizId']}")
```

也可直接使用 CLI 命令：`python scripts/search_knowledge.py --list-apps`

### 方式二：在控制台 URL 中查找（备选）

1. 打开 [Tencent Cloud ADP 控制台](https://adp.cloud.tencent.com/) → **点击「产品体验」进入平台**
2. 进入"应用开发"页面
3. 点击想要检索知识的目标智能体应用
4. 在跳转后的页面 URL 中找到 `appid=` 参数，该参数值即为 AppBizId

例如，页面 URL 为 `https://adp.cloud.tencent.com/adp/#/app/knowledge/app-config?appid=1234567890&spaceId=default_space`，则 AppBizId 为 `1234567890`。

## 五、安全注意事项

1. **密钥仅创建时显示一次**：创建后无法再查询，丢失只能删除重建
2. **不要将密钥写入代码**：不要硬编码到源文件中，不要提交到代码仓库
3. **不要在聊天中明文传递**：密钥可能被记录在对话历史中
4. **用完即删**：临时使用的密钥在完成后应及时删除
5. **环境变量**：通过环境变量传递密钥，而非硬编码

## 六、相关链接

- ADP 密钥管理：https://adp.cloud.tencent.com/adp?spaceId=default_space#/key-manage?spaceId=default_space
- ADP 控制台：https://adp.cloud.tencent.com/
- ADP 官方文档：https://cloud.tencent.com/document/product/1759
