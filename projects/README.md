# projects/ 目录说明

每个项目在这里有独立的归档目录：`<项目名称>_<创建日期>/`，由
`python scripts/init_project.py --name "..." --chain distribution|rd|both` 创建。

目录结构见 `docs/PRD.md` 第 5.1 节；每个项目目录下的子目录含义见该项目自己的
`README.md`（由 `init_project.py` 自动生成）。

## 关于保密

项目目录里存放的是真实/待处理的商业机密材料（L1-L3 各层级都有），**默认不进 git**
（见根目录 `.gitignore`）。只有这份说明文件本身会被提交。如果确实需要把某个项目的
产出物纳入版本控制（比如做样例、写文档配图），单独用 `git add -f` 显式添加，
并在提交前确认里面不含真实项目的敏感信息。
