# S4 顶层计数说明

S4 按任务卡移动了历史包、编号笔记和 superseded 文件，另删除了两个缓存目录。S1 之后又新增了 `INDEX.md`、`PATH_MIGRATION_20261018.csv`、`_archive/` 和 `devlog/`。因此顶层净减少数不会等于移动条目数；差额由新增索引/归档入口和缓存目录删除造成。文件本身的完整性以 `PATH_MIGRATION_20261018.csv` 中逐文件 SHA-256 与 `s4_verification.json` 核验为准。
