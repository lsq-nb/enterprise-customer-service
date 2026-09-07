"""
重排序模块
对混合检索结果进行重排序，提升检索质量
"""
import logging
from typing import Any

from langchain_core.documents import Document
from langchain_openai import OpenAIModelName
from langchain_openai import OpenAIEmbeddings
from langchain_community.cross_encoders import CrossEncoder
from sentence_transformers import CrossEncoder as SentenceCrossEncoder

from config.settings import settings

logger = logging.getLogger(__name__)


class ResponseReranker:
    """
    检索结果重排序器

    支持两种重排序策略：
    1. 基于 CrossEncoder 的语义重排序（推荐）
    2. 基于相似度分数的融合重排序
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        top_k: int | None = None,
    ) -> None:
        """
        初始化重排序器

        Args:
            model_name: CrossEncoder 模型名称
            top_k: 重排序后保留的文档数，默认为 settings.rerank_top_k
        """
        self.model_name = model_name
        self.top_k = top_k or settings.rerank_top_k
        self._cross_encoder: Any = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """初始化 CrossEncoder 模型"""
        try:
            self._cross_encoder = SentenceCrossEncoder(self.model_name)
            logger.info(f"重排序模型加载成功: {self.model_name}")
        except ImportError:
            logger.warning(
                "sentence-transformers 未安装，使用基于分数的默认重排序策略。"
                "安装命令: pip install sentence-transformers"
            )
            self._cross_encoder = None
        except Exception as exc:
            logger.warning(f"CrossEncoder 模型加载失败: {exc}，使用默认策略")
            self._cross_encoder = None

    def rerank(
        self,
        query: str,
        documents: list[Document],
        original_scores: list[float] | None = None,
    ) -> list[Document]:
        """
        对检索结果进行重排序

        Args:
            query: 查询文本
            documents: 待重排序的文档列表
            original_scores: 原始相关度分数列表（可选）

        Returns:
            重排序后的文档列表（Top-K）
        """
        if not documents:
            return []

        if len(documents) <= self.top_k:
            # 文档数少于 top_k，直接返回
            return documents

        if self._cross_encoder is not None:
            # 使用 CrossEncoder 进行语义重排序
            return self._rerank_with_crossencoder(query, documents)
        else:
            # 使用原始分数进行重排序
            return self._rerank_with_scores(query, documents, original_scores)

    def _rerank_with_crossencoder(
        self, query: str, documents: list[Document]
    ) -> list[Document]:
        """使用 CrossEncoder 进行语义重排序"""
        try:
            # 构建查询-文档对
            pairs = [(query, doc.page_content) for doc in documents]
            # 批量计算相关度分数
            scores = self._cross_encoder.predict(pairs)

            # 将分数附加到文档并排序
            scored_docs = list(zip(scores, documents))
            scored_docs.sort(key=lambda x: x[0], reverse=True)

            reranked = [doc for _, doc in scored_docs[: self.top_k]]
            logger.debug(f"CrossEncoder 重排序完成，保留 {len(reranked)} 条文档")
            return reranked
        except Exception as exc:
            logger.error(f"CrossEncoder 重排序失败: {exc}，回退到分数排序")
            return self._rerank_with_scores(query, documents)

    def _rerank_with_scores(
        self,
        query: str,
        documents: list[Document],
        original_scores: list[float] | None = None,
    ) -> list[Document]:
        """
        基于分数进行重排序
        如果有原始分数则使用，否则按文档顺序返回
        """
        if original_scores and len(original_scores) == len(documents):
            # 按原始分数排序
            scored_docs = list(zip(original_scores, documents))
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            reranked = [doc for _, doc in scored_docs[: self.top_k]]
        else:
            # 无分数信息，返回前 top_k 条
            reranked = documents[: self.top_k]

        logger.debug(f"分数重排序完成，保留 {len(reranked)} 条文档")
        return reranked

    def rerank_batch(
        self,
        queries_docs_pairs: list[tuple[str, list[Document]]],
    ) -> list[list[Document]]:
        """
        批量重排序

        Args:
            queries_docs_pairs: [(query, documents), ...] 查询-文档对列表

        Returns:
            每个查询的重排序结果列表
        """
        results = []
        for query, docs in queries_docs_pairs:
            reranked = self.rerank(query, docs)
            results.append(reranked)
        return results
