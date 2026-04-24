# FutureLedger v0 Dividend Report Implementation Plan

这份计划已拆分为多文件，方便分批执行和独立提交。

主入口：
- [README](./2026-04-24-v0-dividend-report-implementation/README.md)

分任务文件：
- [01-domain-models](./2026-04-24-v0-dividend-report-implementation/01-domain-models.md)
- [02-cli-and-pipeline-bootstrap](./2026-04-24-v0-dividend-report-implementation/02-cli-and-pipeline-bootstrap.md)
- [03-cache](./2026-04-24-v0-dividend-report-implementation/03-cache.md)
- [04-universe-and-akshare-client](./2026-04-24-v0-dividend-report-implementation/04-universe-and-akshare-client.md)
- [05-dividend-normalization](./2026-04-24-v0-dividend-report-implementation/05-dividend-normalization.md)
- [06-prices-and-dividend-yield](./2026-04-24-v0-dividend-report-implementation/06-prices-and-dividend-yield.md)
- [07-trailing-one-year-return](./2026-04-24-v0-dividend-report-implementation/07-trailing-one-year-return.md)
- [08-report-rows](./2026-04-24-v0-dividend-report-implementation/08-report-rows.md)
- [09-workbook-writer](./2026-04-24-v0-dividend-report-implementation/09-workbook-writer.md)
- [10-pipeline-orchestration](./2026-04-24-v0-dividend-report-implementation/10-pipeline-orchestration.md)
- [11-final-integration-and-regressions](./2026-04-24-v0-dividend-report-implementation/11-final-integration-and-regressions.md)

建议执行顺序：
1. `01`-`04` 打基础
2. `05`-`07` 完成数据与指标
3. `08`-`11` 完成报表、集成和收口
