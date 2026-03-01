# P3C 规则速查表

P3C（阿里巴巴 Java 开发手册）PMD 规则集及其优先级。

## 目录

- [命名规约 (ali-naming)](#命名规约)
- [常量定义 (ali-constant)](#常量定义)
- [OOP 规约 (ali-oop)](#oop-规约)
- [集合处理 (ali-set)](#集合处理)
- [并发处理 (ali-concurrent)](#并发处理)
- [流程控制 (ali-flowcontrol)](#流程控制)
- [注释规约 (ali-comment)](#注释规约)
- [异常处理 (ali-exception)](#异常处理)
- [ORM 规约 (ali-orm)](#orm-规约)
- [其他 (ali-other)](#其他)

## 命名规约

| 规则 | 优先级 | 说明 |
|------|--------|------|
| ClassNamingShouldBeCamelRule | P1 | 类名使用 UpperCamelCase |
| AbstractClassShouldStartWithAbstractNamingRule | P2 | 抽象类以 Abstract/Base 开头 |
| ConstantFieldShouldBeUpperCaseRule | P1 | 常量全大写，下划线分隔 |
| LowerCamelCaseVariableNamingRule | P1 | 变量/方法名使用 lowerCamelCase |
| AvoidStartWithDollarAndUnderLineNamingRule | P1 | 命名不以 `$` 或 `_` 开头/结尾 |
| PackageNamingRule | P1 | 包名全小写，点分隔 |
| ArrayNamingShouldBeBracketRule | P1 | 数组类型紧跟 `[]`，如 `int[] arr` |
| BooleanPropertyShouldNotStartWithIsRule | P1 | Boolean 属性不以 `is` 前缀 |
| TestClassShouldEndWithTestNamingRule | P3 | 测试类以 Test 结尾 |

## 常量定义

| 规则 | 优先级 | 说明 |
|------|--------|------|
| UpperEllRule | P1 | 长整型用大写 `L`，不用小写 `l` |
| UndefineMagicConstantRule | P2 | 不允许魔法值（未定义常量直接出现） |

## OOP 规约

| 规则 | 优先级 | 说明 |
|------|--------|------|
| EqualsAvoidNullRule | P1 | 常量放在 equals 左侧 |
| WrapperTypeEqualityRule | P1 | 包装类型比较使用 equals |
| StringConcatRule | P2 | 循环中使用 StringBuilder |
| PojoMustOverrideToStringRule | P2 | POJO 类重写 toString |
| PojoNoDefaultValueRule | P2 | POJO 属性不设默认值 |
| PojoMustUsePrimitiveFieldRule | P1 | POJO 属性使用包装数据类型 |

## 集合处理

| 规则 | 优先级 | 说明 |
|------|--------|------|
| ClassCastExceptionWithSubListToArrayListRule | P1 | subList 不可强转 ArrayList |
| ClassCastExceptionWithToArrayRule | P1 | toArray 传入类型一致的数组 |
| ConcurrentExceptionWithModifyOriginSubListRule | P1 | 修改原集合后 subList 不可用 |
| DontModifyInForeachCircleRule | P1 | foreach 中不修改集合 |
| UnsupportedExceptionWithModifyAsListRule | P1 | asList 返回不可修改 |
| CollectionInitShouldAssignCapacityRule | P2 | 集合初始化指定容量 |

## 并发处理

| 规则 | 优先级 | 说明 |
|------|--------|------|
| ThreadPoolCreationRule | P1 | 不使用 Executors 创建线程池 |
| ThreadLocalShouldRemoveRule | P1 | ThreadLocal 使用后 remove |
| AvoidCallStaticSimpleDateFormatRule | P1 | SimpleDateFormat 非线程安全 |
| LockShouldWithTryFinallyRule | P1 | Lock 配合 try-finally |
| AvoidManuallyCreateThreadRule | P2 | 不手动创建线程 |
| CountDownShouldInFinallyRule | P2 | countDown 放在 finally 块 |
| ThreadShouldSetSubGroupRule | P2 | 线程应设置组 |

## 流程控制

| 规则 | 优先级 | 说明 |
|------|--------|------|
| SwitchStatementRule | P1 | switch 必须有 default |
| NeedBraceRule | P1 | if/else/for/while/do 必须加大括号 |
| AvoidComplexConditionRule | P2 | 避免过于复杂的条件表达式 |
| AvoidNegationOperatorRule | P3 | 避免取反逻辑运算符 |

## 注释规约

| 规则 | 优先级 | 说明 |
|------|--------|------|
| ClassMustHaveAuthorRule | P2 | 类必须有 @author 标注 |
| EnumConstantsMustHaveCommentRule | P2 | 枚举值必须有注释 |
| AvoidCommentBehindStatementRule | P3 | 注释在上方，不在语句后 |
| RemoveCommentedCodeRule | P3 | 删除注释掉的代码 |

## 异常处理

| 规则 | 优先级 | 说明 |
|------|--------|------|
| MethodReturnWrapperTypeRule | P1 | 方法返回包装类型防 NPE |
| TransactionMustHaveRollbackRule | P1 | 事务必须处理回滚 |
| AvoidReturnInFinallyRule | P2 | finally 中不使用 return |

## ORM 规约

| 规则 | 优先级 | 说明 |
|------|--------|------|
| IbatisMethodQueryForListRule | P1 | iBatis 查询返回 List |
| MybatisMapperMethodParamCheck | P1 | MyBatis Mapper 参数检查 |

## 其他

| 规则 | 优先级 | 说明 |
|------|--------|------|
| AvoidPatternCompileInMethodRule | P2 | Pattern.compile 预编译放类变量 |
| AvoidApacheBeanUtilsCopyRule | P2 | 避免 Apache BeanUtils.copy |
| AvoidMissUseOfMathRandomRule | P2 | Math.random 使用注意 |
