# Java 规范检查清单

> 规则编号采用 `JAVA-00001` 形式递增，级别枚举：`Critical` > `Major` > `Minor` > `Info`
> 规则标题格式：`规则编号 规则名称`

## JAVA-00001 不必要的工作
- 级别：Critical
- 描述：存在可避免的重复计算或重复 IO 操作。典型模式：循环内执行数据库查询（N+1 问题）、循环内发起 RPC/HTTP 调用、对同一数据源的重复查询未缓存、已有批量接口却逐条调用
- 修复建议：将循环内的远程调用提取到循环外，改为批量查询后用 Map 关联；对重复计算结果做局部变量缓存

## JAVA-00002 未利用并发
- 级别：Critical
- 描述：多个相互无依赖的 IO 操作（如多个 RPC 调用、多表查询）采用顺序执行，总耗时为各操作之和，显著拉长接口响应时间
- 判定前提：**必须确认各操作之间没有数据依赖**。如果后续操作的入参来源于前序操作的返回值（链式依赖），则属于必须顺序执行的逻辑，不应标记此规则。常见的非违规场景包括：先查主记录再根据主记录字段查关联数据、先校验再操作、先获取 ID/Code 再用其查详情等
- 典型违规场景：同一方法中对不同表/服务发起多次独立查询，且查询参数均来自方法入参而非彼此的返回值（如同时查用户信息和订单统计，两者互不依赖）
- 修复建议：使用 CompletableFuture、线程池或并行流将独立操作并发执行，总耗时降为最慢操作的耗时

## JAVA-00003 内存问题
- 级别：Critical
- 描述：可能导致内存泄漏或 OOM 的代码模式。包括：无界集合持续增长（如无上限的缓存 Map）、ThreadLocal 使用后未在 finally 中 remove、流/连接等资源未关闭、一次性加载全表数据到内存
- 修复建议：集合设置容量上限或使用 LRU 缓存；在 finally 或 try-with-resources 中清理资源；大数据量场景使用分页或流式查询

## JAVA-00004 抽象泄漏
- 级别：Critical
- 描述：模块暴露了应封装的内部实现细节，或跨层直接依赖破坏了分层架构。如 Controller 直接操作 DAO、Service 返回数据库 Entity 给前端、工具类暴露内部数据结构
- 修复建议：严格遵循 Controller → Service → Repository 分层；使用 DTO/VO 隔离层间数据传递，避免 Entity 直接暴露

## JAVA-00005 Null 风险
- 级别：Major
- 描述：可能抛出 NullPointerException 的代码路径。包括：对可能为 null 的返回值直接调用方法、集合操作前未判空、Map.get() 结果未判空直接使用、链式调用中间环节可能为 null
- 修复建议：外部输入和跨层返回值做判空校验；优先使用 Optional 包装可空返回值；集合使用 CollectionUtils.isEmpty() 判空

## JAVA-00006 明文敏感信息
- 级别：Critical
- 描述：代码中以硬编码形式出现密码、数据库连接串、API Key、Token、AK/SK 等敏感凭据，存在泄露风险
- 修复建议：敏感信息通过环境变量、配置中心或密钥管理服务（如 Vault）注入，禁止提交到代码仓库

## JAVA-00007 并发安全问题
- 级别：Major
- 描述：多线程场景下的数据竞争风险。包括：共享可变状态未加同步、在并发上下文中使用 HashMap/ArrayList/SimpleDateFormat 等非线程安全类、对共享变量的 check-then-act 非原子操作
- 修复建议：使用 ConcurrentHashMap、CopyOnWriteArrayList 等并发集合替代；共享计数器使用 AtomicInteger；复合操作使用 synchronized 或 Lock 保护

## JAVA-00008 事务使用问题
- 级别：Major
- 描述：Spring 事务可能失效或使用不当。常见场景：同类内部方法调用绕过代理导致 @Transactional 失效、private 方法上标注 @Transactional、事务方法内执行耗时 IO（如 HTTP 调用）导致长事务、未指定 rollbackFor 导致受检异常不回滚
- 修复建议：确保事务方法通过代理调用；添加 rollbackFor = Exception.class；将耗时 IO 移到事务外部

## JAVA-00009 API 设计问题
- 级别：Major
- 描述：接口设计不合理影响可维护性。包括：方法参数超过 5 个未封装为对象、Controller 中编写业务逻辑而非委托 Service、返回值直接使用 Map 而非定义明确的 DTO
- 修复建议：超过 3 个参数封装为 Request DTO；Controller 仅负责参数校验和结果返回，业务逻辑交给 Service 层
