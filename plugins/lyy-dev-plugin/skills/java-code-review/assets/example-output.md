## 审查范围
**Base:** 1a2b3c4d
**Head:** 5e6f7a8b

```bash
git diff --stat 1a2b3c4d..5e6f7a8b
git diff 1a2b3c4d..5e6f7a8b
```

## 优势
- 变更聚焦在单一模块，修改范围可控

## 问题

### Blocker
无

### Critical
1. **SQL 更新缺少 WHERE 条件**
   - 规则：JCR-00010 DML 无 WHERE 条件
   - 位置：db/migration/V20260101__update_user.sql:12
   - 证据：
     ```
     UPDATE user_profile SET status = 'INACTIVE';
     ```
   - 影响：可能更新全表数据，造成不可逆的业务影响
   - 修复建议：补充 WHERE 条件并评估影响范围

### Major
1. **查询SQL中存在SELECT \***
   - 规则：JCR-00011 SELECT *
   - 位置：mapper/history.xml:45
   - 证据：
     ```
     SELECT * FROM history
     ```
   - 影响：字段变化导致不稳定与性能浪费
   - 修复建议：显式列出所需字段

### Minor
无

## 清单覆盖情况/未评估项
- 代码质量：已覆盖（检查命名与异常处理）
- 架构：不适用（本次变更未涉及模块边界）
- 测试：未评估/上下文不足（diff 无测试变更）
- 需求：已覆盖（变更与描述一致）
- 生产就绪性：已覆盖（配置变更可回滚）

## 建议
- 建议为关键 SQL 变更补充回滚脚本

## 评估
**是否可合并：** 需修复

**理由：** 
1. 存在 Critical 级问题（SQL 无 WHERE），需修复后再合并以避免数据风险。
