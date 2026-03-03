# SQL 检查清单
> 规则编号采用 `SQL-00001` 形式递增。

## SQL-00001 禁止使用SELECT *
- 严重级别：Critical
- 描述：SELECT * 查询，字段变化导致不稳定与性能浪费
- 修复建议：显式列出所需字段

## SQL-00002 DML 缺失 WHERE 条件
- 严重级别：Critical
- 描述：UPDATE/DELETE 语句缺失 WHERE 条件，误删/误更新全表数据
- 修复建议：补充 WHERE 条件与影响评估

## SQL-00003 DML 条件完全被 `<where>` 标签包裹导致条件失效
- 严重级别：Critical
- 描述：UPDATE/DELETE 语句所有条件放在 `<where>` 动态标签内，可能会误删/误更新全表数据
- 修复建议：对于 DML 操作，需要硬编码 WHERE

## SQL-00004 SQL 注入风险（`${}` 拼接）
- 严重级别：Major
- 描述：MyBatis 中 `${}` 为字符串直接拼接
- 修复建议：所有用户可控的查询参数必须使用 `#{}`