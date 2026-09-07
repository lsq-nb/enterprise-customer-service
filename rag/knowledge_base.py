"""
三层知识库架构
实现基础知识库、专业知识库、FAQ 知识库的分层管理
"""
import json
import logging
import os
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.retriever import HybridRetriever
from config.settings import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 知识库类型定义
# ─────────────────────────────────────────────
CLASSIFICATION = {
    "basic": "基础知识库",
    "professional": "专业知识库",
    "faq": "FAQ知识库",
}


class KnowledgeBase:
    """
    三层知识库管理器

    架构说明：
    - 基础知识库：产品信息、规格参数、价格体系等静态知识
    - 专业知识库：业务流程、操作规范、政策条款等动态知识
    - FAQ知识库：常见问题及答案对，用于快速检索
    """

    def __init__(self) -> None:
        self._retrievers: dict[str, HybridRetriever] = {}
        self._collections: dict[str, dict[str, Any]] = {
            "basic": {"name": "基础知识库", "description": "产品信息与规格参数", "count": 0},
            "professional": {"name": "专业知识库", "description": "业务流程与政策条款", "count": 0},
            "faq": {"name": "FAQ知识库", "description": "常见问题与标准答案", "count": 0},
        }
        self._knowledge_dir = Path(settings.knowledge_dir)
        self._knowledge_dir.mkdir(parents=True, exist_ok=True)
        logger.info("知识库系统初始化完成")

    # ────────────────────────────────────────────
    # 文档加载与处理
    # ────────────────────────────────────────────
    def load_from_file(
        self,
        file_path: str,
        knowledge_type: str = "basic",
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        从文件加载文档到指定知识库

        Args:
            file_path: 文档文件路径
            knowledge_type: 知识库类型（basic/professional/faq）
            metadata: 额外元数据

        Returns:
            成功加载的文档块数量
        """
        if knowledge_type not in self._collections:
            raise ValueError(
                f"不支持的知识库类型: {knowledge_type}，"
                f"可选值: {list(self._collections.keys())}"
            )

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 读取文档内容
        content = self._read_document(path)
        if not content:
            logger.warning(f"文件内容为空: {file_path}")
            return 0

        # 分块处理
        chunks = self._chunk_document(content, path.name)

        # 添加元数据
        for chunk in chunks:
            chunk.metadata.update({
                "source": path.name,
                "knowledge_type": knowledge_type,
                **(metadata or {}),
            })

        # 添加到知识库
        self._add_to_collection(chunks, knowledge_type)

        logger.info(
            f"已从 {file_path} 加载 {len(chunks)} 个文档块到 {knowledge_type} 知识库"
        )
        return len(chunks)

    def load_from_text(
        self,
        text: str,
        knowledge_type: str = "basic",
        source_name: str = "manual_input",
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        从文本内容加载到指定知识库

        Args:
            text: 文档文本内容
            knowledge_type: 知识库类型
            source_name: 来源标识
            metadata: 额外元数据

        Returns:
            成功加载的文档块数量
        """
        if knowledge_type not in self._collections:
            raise ValueError(
                f"不支持的知识库类型: {knowledge_type}，"
                f"可选值: {list(self._collections.keys())}"
            )

        chunks = self._chunk_document(text, source_name)

        for chunk in chunks:
            chunk.metadata.update({
                "source": source_name,
                "knowledge_type": knowledge_type,
                **(metadata or {}),
            })

        self._add_to_collection(chunks, knowledge_type)
        logger.info(f"已加载 {len(chunks)} 个文档块到 {knowledge_type} 知识库")
        return len(chunks)

    # ────────────────────────────────────────────
    # 检索接口
    # ────────────────────────────────────────────
    def retrieve(
        self,
        query: str,
        knowledge_type: str | None = None,
        top_k: int | None = None,
    ) -> list[Document]:
        """
        执行检索

        Args:
            query: 检索查询
            knowledge_type: 限定检索的知识库类型，None 表示检索全部
            top_k: 返回文档数

        Returns:
            检索到的文档列表
        """
        if knowledge_type:
            if knowledge_type not in self._retrievers:
                logger.warning(f"知识库 {knowledge_type} 尚未初始化，返回空结果")
                return []
            retriever = self._retrievers[knowledge_type]
            docs = retriever._get_relevant_documents(query)
        else:
            # 跨所有知识库检索
            all_docs: list[Document] = []
            for kb_type, retriever in self._retrievers.items():
                docs = retriever._get_relevant_documents(query)
                all_docs.extend(docs)
            # 按知识库类型去重（保留最高相关度）
            all_docs = self._deduplicate_by_content(all_docs)
            docs = all_docs

        return docs[: (top_k or settings.retrieval_top_k)]

    def retrieve_with_score(
        self, query: str, knowledge_type: str | None = None, top_k: int | None = None
    ) -> list[tuple[Document, float]]:
        """
        返回带相关度分数的检索结果

        Returns:
            [(Document, score), ...] 列表
        """
        docs = self.retrieve(query, knowledge_type, top_k)
        return [(doc, 1.0) for doc in docs]

    # ────────────────────────────────────────────
    # 知识库管理
    # ────────────────────────────────────────────
    def get_stats(self) -> dict[str, Any]:
        """获取知识库统计信息"""
        stats = {}
        for kb_type, info in self._collections.items():
            retriever = self._retrievers.get(kb_type)
            doc_count = info["count"]
            if retriever and retriever._vector_store:
                doc_count = retriever._vector_store._collection.count()
            stats[kb_type] = {
                **info,
                "document_count": doc_count,
                "status": "active" if retriever else "inactive",
            }
        return stats

    def clear_collection(self, knowledge_type: str) -> bool:
        """清空指定知识库"""
        if knowledge_type not in self._collections:
            return False
        if knowledge_type in self._retrievers:
            del self._retrievers[knowledge_type]
        self._collections[knowledge_type]["count"] = 0
        logger.info(f"已清空 {knowledge_type} 知识库")
        return True

    def list_collections(self) -> dict[str, dict[str, Any]]:
        """列出所有知识库及其状态"""
        return self._collections.copy()

    # ────────────────────────────────────────────
    # 内部方法
    # ────────────────────────────────────────────
    def _add_to_collection(self, documents: list[Document], kb_type: str) -> None:
        """将文档添加到指定知识库集合"""
        if kb_type not in self._retrievers:
            # 首次初始化
            self._retrievers[kb_type] = HybridRetriever(documents=documents)
        else:
            # 增量更新
            self._retrievers[kb_type].add_documents(documents)
        self._collections[kb_type]["count"] += len(documents)

    @staticmethod
    def _chunk_document(content: str, source_name: str) -> list[Document]:
        """使用递归字符分割器将文档分块"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ";", ",", ".", " ", ""],
        )
        chunks = text_splitter.split_text(content)
        documents = [
            Document(page_content=chunk, metadata={"source": source_name})
            for chunk in chunks
        ]
        return documents

    @staticmethod
    def _read_document(path: Path) -> str:
        """读取文档内容，支持多种格式"""
        suffix = path.suffix.lower()
        try:
            if suffix in (".txt", ".md"):
                return path.read_text(encoding="utf-8")
            elif suffix == ".csv":
                import csv

                with open(path, encoding="utf-8") as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                # 简单拼接为文本
                return "\n".join(["\t".join(row) for row in rows])
            elif suffix == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                return json.dumps(data, ensure_ascii=False, indent=2)
            elif suffix == ".pdf":
                # PDF 解析需要额外依赖，此处记录日志
                logger.warning("PDF 解析需要安装 pymupdf 或类似库")
                return ""
            else:
                # 默认尝试 UTF-8 文本读取
                return path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error(f"读取文档失败 {path}: {exc}")
            return ""

    @staticmethod
    def _deduplicate_by_content(documents: list[Document]) -> list[Document]:
        """按文档内容去重，保留第一条（通常是最相关的）"""
        seen: set[str] = set()
        unique_docs: list[Document] = []
        for doc in documents:
            key = doc.page_content[:100]  # 用前 100 字符作为去重 key
            if key not in seen:
                seen.add(key)
                unique_docs.append(doc)
        return unique_docs


# ─────────────────────────────────────────────
# 全局知识库实例（单例模式）
# ─────────────────────────────────────────────
_knowledge_base: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    """获取全局知识库实例（单例）"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base
