## ✨ 改进
- **heartbeat**: 优化心跳超时检测逻辑——未连接适配器时不再产生误报警告。只有在收到第一个心跳事件后才激活超时检测，避免在无 NapCat/SnowLuma 适配器运行时持续输出"心跳超时"警告日志。

## 🐛 修复
- **event**: 修复 QQ 请求事件 `approve()`/`reject()` 直接调用 API 方法未经子对象路由的问题 (c237badb)
- **event**: 修复 QQ 消息事件 `delete()`/`kick()`/`ban()` 直接调用 API 方法未经子对象路由的问题 (a6624c2b)
- 同步示例与技能参考 (62bac12c)
- 更新 stale example 引用 (eb6ec05d)
