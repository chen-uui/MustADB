优化RAG检索融合多样性与覆盖：
  - 在HybridSearchService._merge_and_rerank输出阶段引入MMR（最大边际相关性）去冗余算法，并强制设置per-doc限制与文档覆盖下限。
  - 参数设定：最终选取的limit个结果，保证覆盖至少3篇不同论文，每篇最多2段，优先内容多样+top分。
  - 选取方式：
    1. 首轮从每篇文档top1填满min_doc数。
    2. 后续逐步以MMR原则迭代选取（优先选择与已选结果最不相似且分数较高者），直到k/topk。
    3. 且最终每文档不超过quota篇、总数k。
  - 自动调用已有embedding_service做MMR余弦相似度计算。无embedding时fallback为0。
结果：语义冗余碎片减少，跨论文综述和复杂问答时多元性/覆盖面显著提升，用户入口无感知，处理流程完全兼容原接口。