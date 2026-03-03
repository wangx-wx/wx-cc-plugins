审查报告输出格式
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CodeReviewReport",
  "description": "代码审查报告",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["fileName", "ruleId", "blockLevel", "codeSnippet", "affectedScope", "suggestion"],
    "properties": {
      "fileName": {
        "type": "string",
        "description": "文件名称"
      },
      "ruleId": {
        "type": "string",
        "description": "规则编号"
      },
      "blockLevel": {
        "type": "string",
        "description": "问题级别",
        "enum": ["Blocker", "Critical", "Major", "Minor"]
      },
      "codeSnippet": {
        "type": "string",
        "description": "问题代码片段"
      },
      "affectedScope": {
        "type": "string",
        "description": "影响范围"
      },
      "suggestion": {
        "type": "string",
        "description": "修复建议"
      }
    },
    "additionalProperties": false
  }
}
```