## 项目知识库

该目录用于给现有 AI 助手补充项目知识，不改变前后端 AI 接口协议。

当前分层：

- `01_indicator_dictionary/`
  - 稳定知识层，主要来自 `data/数据单位.docx`
  - 供 tooltip、问答助手、总结助手解释指标含义、单位、政策背景
- `02_page_guidance/`
  - 页面解读规则层，主要来自 `绿色金融项目知识库 Markdown 实施稿.docx`
  - 供问答助手、总结助手区分绿色金融页、碳排放页、预测页的字段口径、单位换算、政策背景和模型回答边界
- `04_result_cards/`
  - 结果解释层，主要来自 `data/模型log.doc`
  - 供 AI 生成“方向 + 显著性 + 谨慎表述”的结果解释
- `05_prompt_templates/`
  - 各类 AI 能力的补充 prompt 模板
- `raw_logs_archive/`
  - 原始追溯层，记录原始文档来源，不直接作为高频 tooltip 知识源

后续扩展方式：

1. 继续往指标字典、页面规则和结果卡片 JSON 补条目
2. 如需新规则，优先改 `ai_knowledge.py`
3. 保持 `source` 字段指向原始业务文档，方便追溯
