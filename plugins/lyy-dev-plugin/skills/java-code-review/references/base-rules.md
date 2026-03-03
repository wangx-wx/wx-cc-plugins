# 基础规范检查清单

> 规则编号采用 `BASE-00001` 形式递增

## BASE-00001 不必要的工作
- 级别：Critical
- 描述：冗余的计算，重复数据库查询，重复RPC/API 调用，N+1 查询模式，循环内执行远程请求
- 建议：方法抽象或者使用多线程调用
## BASE-00002 未利用并发
- 级别：Critical
- 描述：独立操作顺序执行，阻塞等待
- 建议：逻辑进行并发执行
## BASE-00003 内存问题
- 级别：Critical
- 描述：无界数据结构、缺少清理、事件监听泄漏
- 建议：集合设置容量上限，finally / try-with-resources 中清理 ThreadLocal
## BASE-00004 抽象泄漏
- 级别：Critical
- 描述：暴露应封装的内部细节，或破坏既有抽象边界
- 建议：严格分层（Controller / Service / Repository），DTO 与 Entity 隔离
## BASE-00005 大型函数
- 级别：Major
- 描述：单个函数最大行数不宜超过50行
- 建议：拆分成更小、更专注的函数
## BASE-00006 大型文件
- 级别：Major
- 描述：单个文件最大行数不宜超过800行
- 建议：按职责提取模块
## BASE-00007 死代码
- 级别：Major
- 描述：被注释掉的代码、未使用的导入语句、无法访问的分支
- 建议：删除无用的代码
## BASE-00008 Null风险
- 级别：Major
- 描述：未判空直接调用方法或访问字段；方法返回 null 而调用方未处理；集合操作前未校验是否为空
- 建议：参数校验，Optional
## BASE-00009 明文敏感信息
- 级别：Critical
- 描述：出现明文密码/密钥/Token/AK/SK
- 建议：改为环境变量或密钥管理服务
## BASE-00010 并发安全问题
- 级别：Major
- 描述：多线程共享可变状态未加同步；使用非线程安全集合（HashMap、ArrayList）在并发场景
- 建议：使用 ConcurrentHashMap、CopyOnWriteArrayList 等并发集合
## BASE-00011 事务使用问题
- 级别：Major
- 描述：需要避免事务失效
- 建议：显式指定；事务方法内不做耗时 IO
## BASE-00012 API 设计问题
- 级别：Major
- 描述：接口参数过多（超过 5 个）未封装为对象，Controller层编写业务逻辑
- 建议：超过 3 个参数封装为 Request DTO，业务逻辑应交于 Service 层处理，Controller 仅负责参数校验与结果返回