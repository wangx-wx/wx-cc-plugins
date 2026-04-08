# SearchKnowledgeRelease 接口文档

## 基本信息

- **接口名称**：SearchKnowledgeRelease
- **接口描述**：知识检索（发布环境）
- **请求方式**：POST
- **接口地址**：`https://adp.cloud.tencent.com/plugin/api/v1/4270baf0-d5a6-4b9f-b29a-38cebc821753/05813dd1-dbf4-4314-badb-4985bb2594e6`
- **认证方式**：`Authorization: Bearer {ADP_API_KEY}`
- **请求频率限制**：20 次/秒

> **重要**：
> 1. 此接口**只支持检索应用（App）**，必须传入应用的 `AppBizId`，**不支持直接传入共享知识库的 `KnowledgeBizId`**。如需检索共享知识库的内容，需找到一个关联了该共享知识库且状态为「运行中」的应用，使用该应用的 `AppBizId` 进行检索。
> 2. **应用必须处于「运行中」状态**才能被检索。未上线、已停用等非运行状态的应用无法返回检索结果。如需发布应用，参见 [应用发布文档](https://cloud.tencent.com/document/product/1759/104209)。
> 3. 此接口只能检索**发布域**的知识。文档的 `EnableScope` 必须包含发布域（值为 3 或 4）才能被检索到。`EnableScope` 为 1（不生效）或 2（仅开发域）的文档无法被此接口检索。

---

## SearchKnowledgeRelease 请求参数

| 参数名称 | 类型 | 必选 | 说明 |
|:---|:---|:---|:---|
| AppBizId | String | 是 | 应用 ID（必须是应用的 AppBizId，不支持共享知识库的 KnowledgeBizId）。应用必须处于「运行中」状态。示例值：`1984553302330703872` |
| Question | String | 是 | 检索的问题。示例值：`怎么启动汽车` |
| VisitorBizId | String | 否 | 访客 ID（外部输入，建议唯一，标识当前接入会话的用户）。示例值：`admin` |
| CustomVariables | Array of CustomVariable | 否 | 自定义参数，用于设置知识库检索范围（见下方说明） |

### CustomVariable 结构

| 名称 | 类型 | 必选 | 描述 |
|:---|:---|:---|:---|
| Name | String | 否 | 参数名称。示例值：`name` |
| Value | String | 否 | 参数的值。示例值：`张三` |

**CustomVariables 用法**：

1. **按标签检索**：需要先在 ADP 控制台设置 API 参数与标签的映射关系，Name 为 API 参数，Value 为标签值。多个值用竖线 `|` 分隔
2. **按文档范围检索**：Name 固定为 `ADP_DOC_BIZ_ID`，Value 为竖线 `|` 分隔的文档 ID

## 响应格式

ADP 插件 API 统一响应格式：

```json
{
    "Code": 0,
    "Msg": "ok",
    "Data": {
        "KnowledgeList": [...],
        "RequestId": "xxx"
    }
}
```

- `Code`：0 表示成功，非 0 表示失败
- `Msg`：错误消息
- `Data`：业务数据

### KnowledgeList 中的 SearchKnowledgeItem 结构

| 名称 | 类型 | 描述 |
|:---|:---|:---|
| KnowledgeType | String | 知识类型：`QA`=问答对，`DOC`=文档片段 |
| KnowledgeId | String | 知识 ID（QA 为问答对 ID，DOC 为文档片段 ID） |
| Question | String | 检索到的问题（仅 QA 类型有效） |
| Content | String | 内容（QA 为答案，DOC 为文档片段） |
| Title | String | 文档标题（仅 DOC 类型有效） |
| RelatedDocId | String | 关联文档 ID（仅 DOC 类型有效） |
| KnowledgeBaseId | String | 知识所属知识库 ID |
| DocName | String | 文档名称（仅 DOC 类型有效） |

## 请求示例

```bash
curl -X POST 'https://adp.cloud.tencent.com/plugin/api/v1/4270baf0-d5a6-4b9f-b29a-38cebc821753/05813dd1-dbf4-4314-badb-4985bb2594e6' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -d '{
    "AppBizId": "1727231073371148288",
    "Question": "怎么报销",
    "CustomVariables": [
        {
            "Name": "department",
            "Value": "行政部|人力资源部"
        },
        {
            "Name": "ADP_DOC_BIZ_ID",
            "Value": "1990797994659710208|1990976644805854464"
        }
    ]
}'
```

## 响应示例

```json
{
    "Code": 0,
    "Msg": "ok",
    "Data": {
        "KnowledgeList": [
            {
                "KnowledgeType": "DOC",
                "KnowledgeId": "1729099536210460672",
                "Content": "办理方式：网上办理：你可以通过"广东政务服务网"进行预申请...",
                "Title": "医保报销",
                "RelatedDocId": "1990797994659710208",
                "KnowledgeBaseId": "1727231073371148288",
                "DocName": "报销流程.doc"
            }
        ],
        "RequestId": "5526c65b-308d-4e84-b6b3-6b21d5c106b2"
    }
}
```

---

# EnableScope 说明（文档生效范围）

`SearchKnowledgeRelease` 接口只能检索发布域的知识。文档的 `EnableScope` 属性决定了其在哪些环境下生效：

| EnableScope 值 | 含义 | SearchKnowledgeRelease 是否可检索 |
|:---|:---|:---|
| 1 | 不生效 | ❌ 不可检索 |
| 2 | 仅开发域生效 | ❌ 不可检索 |
| 3 | 仅发布域生效 | ✅ 可检索 |
| 4 | 开发域和发布域均生效 | ✅ 可检索 |

如需修改文档的 EnableScope，使用 `ModifyDoc` 接口：

```python
import requests

APP_ID = "4270baf0-d5a6-4b9f-b29a-38cebc821753"
MODIFY_DOC_URL = f"https://adp.cloud.tencent.com/plugin/api/v1/{APP_ID}/3b4b1f44-509d-4efa-988f-e16e2d36f409"

headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
payload = {
    "BotBizId": app_biz_id,
    "DocBizId": doc_biz_id,
    "IsRefer": False,     # 必填：回填当前值
    "AttrRange": 1,       # 必填：回填当前值
    "EnableScope": 4,     # 目标生效域
}
resp = requests.post(MODIFY_DOC_URL, headers=headers, json=payload, timeout=60)
```

> **重要**：`ModifyDoc` 的 `IsRefer` 和 `AttrRange` 为必填参数，未传会报错。修改前需先通过 `DescribeDoc` 获取当前值并回填。

---

# ListApp（获取企业下应用列表）

用于查询当前账号下所有智能体应用，获取 AppBizId，避免用户手动在控制台查找。

- **接口地址**：`https://adp.cloud.tencent.com/plugin/api/v1/4270baf0-d5a6-4b9f-b29a-38cebc821753/2506ec47-456e-430c-9904-42a30ae27f3c`
- **官方文档**：https://cloud.tencent.com/document/api/1759/105066

### 请求参数

| 参数名称 | 必选 | 类型 | 描述 |
|:---|:---|:---|:---|
| AppType | 否 | String | 应用类型，如 `knowledge_qa`（知识问答） |
| PageSize | 否 | Integer | 每页数目，默认 10，最大 50 |
| PageNumber | 否 | Integer | 页码，从 1 开始 |
| Keyword | 否 | String | 搜索关键词 |

### 响应参数

| 参数名称 | 类型 | 描述 |
|:---|:---|:---|
| Total | String | 应用总数 |
| List | Array of AppInfo（JSON 字符串数组） | 应用列表 |

### AppInfo 结构

| 字段 | 类型 | 描述 |
|:---|:---|:---|
| AppBizId | String | 应用业务 ID |
| Name | String | 应用名称 |
| AppTypeDesc | String | 应用类型描述 |
| AppStatus | Integer | 应用状态 |
| AppStatusDesc | String | 应用状态描述（如"运行中"、"未上线"） |

> ⚠️ **注意**：List 中的每项元素可能是 JSON 字符串而非字典，需用 `json.loads()` 二次解析。

---

# ListDoc 接口文档（获取文档列表）

- **接口地址**：`https://adp.cloud.tencent.com/plugin/api/v1/4270baf0-d5a6-4b9f-b29a-38cebc821753/04a95e35-b22c-41d8-be6a-0120768ec5aa`
- **官方文档**：https://cloud.tencent.com/document/api/1759/105068

## 请求参数

| 参数名称 | 类型 | 必选 | 说明 |
|:---|:---|:---|:---|
| BotBizId | String | 是 | 应用 ID |
| PageNumber | Integer | 是 | 页码，从 1 开始 |
| PageSize | Integer | 是 | 每页数量，最大 50 |

## 响应参数

| 参数名称 | 类型 | 说明 |
|:---|:---|:---|
| Total | String | 文档总数 |
| List | Array of ListDocItem | 文档列表 |

---

# DescribeDoc 接口文档（查看文档详情）

- **接口地址**：`https://adp.cloud.tencent.com/plugin/api/v1/4270baf0-d5a6-4b9f-b29a-38cebc821753/0b616bb2-9e21-40e2-b571-a83542a8123d`
- **官方文档**：https://cloud.tencent.com/document/api/1759/105071

## 请求参数

| 参数名称 | 类型 | 必选 | 说明 |
|:---|:---|:---|:---|
| BotBizId | String | 是 | 应用 ID |
| DocBizId | String | 是 | 文档 ID |

## 关键响应字段

| 参数名称 | 类型 | 说明 |
|:---|:---|:---|
| EnableScope | Integer | 文档生效域：1=不生效，2=仅开发域，3=仅发布域，4=全部 |
| Status | Integer | 文档状态 |
| StatusDesc | String | 文档状态描述 |
| IsRefer | Boolean | 是否引用链接（ModifyDoc 的必填参数） |
| AttrRange | Integer | 标签适用范围（ModifyDoc 的必填参数） |

---

# ModifyDoc 接口文档（修改文档属性）

- **接口地址**：`https://adp.cloud.tencent.com/plugin/api/v1/4270baf0-d5a6-4b9f-b29a-38cebc821753/3b4b1f44-509d-4efa-988f-e16e2d36f409`
- **官方文档**：https://cloud.tencent.com/document/api/1759/105070

## 关键请求参数

| 参数名称 | 类型 | 必选 | 说明 |
|:---|:---|:---|:---|
| BotBizId | String | 是 | 应用 ID |
| DocBizId | String | 是 | 文档 ID |
| IsRefer | Boolean | 是 | 是否引用链接（**必填**，需先通过 DescribeDoc 获取当前值回填） |
| AttrRange | Integer | 是 | 标签适用范围（**必填**，1=全部, 2=按条件，需回填当前值） |
| EnableScope | Integer | 否 | 文档生效域：1=不生效，2=仅开发域，3=仅发布域，4=全部 |

---

## 错误码

| 错误场景 | 描述 | 解决方案 |
|:---|:---|:---|
| 401 Unauthorized | API Key 无效或未设置 | 检查 ADP_API_KEY 环境变量，重新获取密钥 |
| Code=3000003 / 配额不足 | 套餐资源已耗尽 | 前往 [ADP 购买页](https://buy.cloud.tencent.com/adp) 购买或增购套餐 |
| 检索返回空结果 | 应用不是「运行中」状态 | 在 ADP 控制台将应用发布上线。📖 [应用发布文档](https://cloud.tencent.com/document/product/1759/104209) |
| 检索返回空结果 | 传入了共享知识库的 KnowledgeBizId | SearchKnowledgeRelease 不支持直接传入共享知识库 ID，需找到关联该共享知识库且运行中的应用 |
| 检索返回空结果 | 文档 EnableScope 未包含发布域 | 使用 --check / --fix 检查和修复 |
| 检索模型 token 不足 | 未订阅 ADP 付费套餐或 PU 资源耗尽 | 前往 [ADP 购买页](https://buy.cloud.tencent.com/adp) 订阅专业版或企业版；已有套餐可增购预付费资源包。详见 [购买方式文档](https://cloud.tencent.com/document/product/1759/127528) |

---

## 附录：共享知识库相关接口

> 以下两个接口用于知识库目标定位流程中确定共享知识库的信息。
>
> ⚠️ **重要**：`SearchKnowledgeRelease` 不支持直接传入共享知识库的 `KnowledgeBizId`。如需检索共享知识库的内容，需通过以下接口找到关联该共享知识库的应用，然后使用该应用的 `AppBizId`（且应用必须处于「运行中」状态）。操作共享知识库中的**文档**（如 ListDoc、ModifyDoc 等）时，仍可使用 `KnowledgeBizId` 作为 `BotBizId`。

### ListSharedKnowledge（列举共享知识库）

- **接口地址**：`https://adp.cloud.tencent.com/plugin/api/v1/4270baf0-d5a6-4b9f-b29a-38cebc821753/88dce784-32d6-4689-a527-ec969d0f6228`
- **官方文档**：https://cloud.tencent.com/document/product/1759/119405

#### 请求参数

| 参数名称 | 必选 | 类型 | 描述 |
|:---|:---|:---|:---|
| PageNumber | 是 | Integer | 页码，从 1 开始 |
| PageSize | 是 | Integer | 每页数目，最大 20 |
| Keyword | 否 | String | 搜索关键词，可按知识库名称模糊搜索 |

#### 响应参数

| 参数名称 | 类型 | 描述 |
|:---|:---|:---|
| Total | String | 共享知识库总数（字符串类型） |
| KnowledgeList | Array | 共享知识库列表（注意字段名为 KnowledgeList，非 List） |

#### KnowledgeInfo 结构

| 字段 | 类型 | 描述 |
|:---|:---|:---|
| KnowledgeBizId | String | 共享知识库业务 ID，操作文档时用作 `BotBizId` |
| KnowledgeName | String | 共享知识库名称 |
| KnowledgeDescription | String | 共享知识库描述 |
| AppList | Array of KnowledgeAppInfo | 关联的应用列表 |

#### KnowledgeAppInfo 结构

| 字段 | 类型 | 描述 |
|:---|:---|:---|
| AppBizId | String | 关联应用的业务 ID |
| Name | String | 关联应用名称 |

#### 调用示例

```python
import requests

APP_ID = "4270baf0-d5a6-4b9f-b29a-38cebc821753"
LIST_SHARED_KB_URL = f"https://adp.cloud.tencent.com/plugin/api/v1/{APP_ID}/88dce784-32d6-4689-a527-ec969d0f6228"

headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
payload = {"PageNumber": 1, "PageSize": 20}

resp = requests.post(LIST_SHARED_KB_URL, headers=headers, json=payload, timeout=60)
data = resp.json()
# ⚠️ 注意：KnowledgeList 中每项可能是 JSON 字符串
# ⚠️ 检索时不能直接用 KnowledgeBizId，需通过 AppList 找到关联的「运行中」应用
# 文档操作（ListDoc/ModifyDoc 等）可使用 KnowledgeBizId 作为 BotBizId
```

---

### ListReferShareKnowledge（查询应用关联的共享知识库）

- **接口地址**：`https://adp.cloud.tencent.com/plugin/api/v1/4270baf0-d5a6-4b9f-b29a-38cebc821753/6fd5da0f-5540-4ffd-a05c-805129f9857d`
- **官方文档**：https://cloud.tencent.com/document/product/1759/119406

#### 请求参数

| 参数名称 | 必选 | 类型 | 描述 |
|:---|:---|:---|:---|
| AppBizId | 是 | String | 应用业务 ID |
| PageNumber | 是 | Integer | 页码，从 1 开始 |
| PageSize | 是 | Integer | 每页数目，最大 20 |

#### 响应参数

| 参数名称 | 类型 | 描述 |
|:---|:---|:---|
| Total | String | 该应用关联的共享知识库总数（字符串类型） |
| List | Array of KnowledgeInfo | 共享知识库列表（结构同 ListSharedKnowledge） |

#### 调用示例

```python
import requests

APP_ID = "4270baf0-d5a6-4b9f-b29a-38cebc821753"
LIST_REFER_SHARE_KB_URL = f"https://adp.cloud.tencent.com/plugin/api/v1/{APP_ID}/6fd5da0f-5540-4ffd-a05c-805129f9857d"

headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
payload = {"AppBizId": "应用的AppBizId", "PageNumber": 1, "PageSize": 20}

resp = requests.post(LIST_REFER_SHARE_KB_URL, headers=headers, json=payload, timeout=60)
data = resp.json()
# 如果 Data.Total > 0，说明该应用关联了共享知识库
# ⚠️ 检索共享知识库内容时，使用当前应用的 AppBizId（不能直接用 KnowledgeBizId）
```
