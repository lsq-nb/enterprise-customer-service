"""
混合检索器
基于 BM25 关键词检索 + 向量语义检索的混合召回策略
"""
import logging
from typing import Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from config.settings import settings

logger = logging.getLogger(__name__)


class HybridRetriever(BaseRetriever):
    """
    BM25 + 向量检索混合召回策略

    结合两种检索方式的优势：
    - BM25：关键词精确匹配，适合专业术语、产品型号等
    - 向量检索：语义理解，适合自然语言查询

    返回结果通过权重融合排序
    """

    # ────────────────────────────────────────────
    # 配置参数
    # ────────────────────────────────────────────
    bm25_weight: float = settings.bm25_weight
    """BM25 检索结果的权重（0.0-1.0），向量检索权重为 1 - bm25_weight"""
    top_k: int = settings.retrieval_top_k
    """返回的文档总数"""
    bm25_top_k: int = 10
    """BM25 检索返回的候选文档数"""
    vector_top_k: int = 10
    """向量检索返回的候选文档数"""

    # ────────────────────────────────────────────
    # 内部状态
    # ────────────────────────────────────────────
    _bm25_retriever: BM25Retriever | None = None
    _vector_store: Chroma | None = None
    _embeddings: OpenAIEmbeddings | None = None

    # ────────────────────────────────────────────
    # 初始化
    # ────────────────────────────────────────────
    def __init__(
        self,
        documents: list[Document],
        collection_name: str = settings.chroma_collection,
        persist_dir: str = settings.chroma_persist_dir,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.bm25_weight = kwargs.get("bm25_weight", self.bm25_weight)
        self.top_k = kwargs.get("top_k", self.top_k)
        self._embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self._vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self._embeddings,
            persist_directory=persist_dir,
        )
        # 初始化 BM25 检索器
        self._bm25_retriever = BM25Retriever.from_documents(
            documents=documents,
        )
        # 将文档写入向量库
        if documents:
            self._vector_store.add_documents(documents)
            logger.info(f"已加载 {len(documents)} 条文档到混合检索器")

    # ────────────────────────────────────────────
    # 核心检索方法
    # ────────────────────────────────────────────
    def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        """
        执行混合检索并融合结果

        检索流程：
        1. 并行执行 BM25 和向量检索
        2. 对两组结果分别计算归一化分数
        3. 按权重融合排序
        4. 返回 Top-K 文档
        """
        logger.debug(f"执行混合检索，查询内容: {query[:50]}...")

        # 并行执行两种检索
        bm25_docs: list[Document] = self._bm25_retriever.invoke(
            query,
        )
        vector_docs: list[Document] = self._vector_store.similarity_search(
            query=query,
            k=self.vector_top_k,
        )

        # 融合结果
        fused_docs = self._fuse_results(bm25_docs, vector_docs)

        # 返回 Top-K
        return fused_docs[: self.top_k]

    # ────────────────────────────────────────────
    # 结果融合策略
    # ────────────────────────────────────────────
    def _fuse_results(
        self,
        bm25_docs: list[Document],
        vector_docs: list[Document],
    ) -> list[Document]:
        """
        基于 Reciprocal Rank Fusion (RRF) 的结果融合策略

        对每组文档计算归一化分数，按权重加权融合后排序
        """
        # 去重映射：doc_content → Document
        doc_map: dict[str, tuple[float, float]] = {}

        # BM25 结果打分（基于排名倒数）
        for i, doc in enumerate(bm25_docs):
            content = doc.page_content
            # RRF 分数：1 / (rank + k)，k 通常取 60
            rrf_score = 1.0 / (i + 60)
            if content in doc_map:
                bm25_score, _ = doc_map[content]
                doc_map[content] = (bm25_score + rrf_score, _)
            else:
                doc_map[content] = (rrf_score, 0.0)

        # 向量结果打分（基于余弦相似度）
        for i, doc in enumerate(vector_docs):
            content = doc.page_content
            # 归一化相似度分数
            vector_score = 1.0 / (i + 1) if i < len(vector_docs) else 0.0
            if content in doc_map:
                _, vec_score = doc_map[content]
                _, _ = doc_map[content]
                doc_map[content] = (doc_map[content][0], vector_score)
            else:
                doc_map[content] = (0.0, vector_score)

        # 加权融合排序
        scored_docs: list[tuple[float, Document]] = []
        for content, (bm25_score, vector_score) in doc_map.items():
            # 查找对应的 Document 对象
            doc = self._find_doc(content, bm25_docs + vector_docs)
            if doc is None:
                continue
            # 融合分数 = BM25权重 × BM25分 + 向量权重 × 向量分
            fusion_score = (
                self.bm25_weight * bm25_score + (1 - self.bm25_weight) * vector_score
            )
            scored_docs.append((fusion_score, doc))

        # 按融合分数降序排列
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored_docs]

    def _find_doc(self, content: str, docs: list[Document]) -> Document | None:
        """从文档列表中查找匹配内容的 Document 对象"""
        for doc in docs:
            if doc.page_content == content:
                return doc
        return None

    # ────────────────────────────────────────────
    # 公开接口
    # ────────────────────────────────────────────
    async def aget_relevant_documents(self, query: str) -> list[Document]:
        """异步检索接口（同步行包装饰）"""
        return self._get_relevant_documents(query)

    def add_documents(self, documents: list[Document]) -> None:
        """动态添加文档到混合检索器"""
        if self._bm25_retriever:
            self._bm25_retriever.document_tuples.extend(
                [(doc.page_content, doc.metadata) for doc in documents]
            )
            self._bm25_retriever._setup_stores()
        if self._vector_store:
            self._vector_store.add_documents(documents)
        logger.info(f"已添加 {len(documents)} 条文档到混合检索器")
