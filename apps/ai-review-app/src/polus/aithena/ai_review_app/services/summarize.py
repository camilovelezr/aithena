"""Summarize documents using LLM."""

from collections import defaultdict
from pathlib import Path
from typing import Any
import solara
from solara.lab import task
from polus.aithena.ai_review_app import config
from polus.aithena.ai_review_app.services.aithena_services_client import chat_request
from polus.aithena.ai_review_app.utils.common import current_date
from polus.aithena.common.logger import get_logger
from ..models.context import Context, Document, DocType
from polus.aithena.ai_review_app.config import SUMMARY_CUTOFF
from polus.aithena.common.utils import init_dir

logger = get_logger(__file__)

async def summarize_all(
    documents: list[Document],
    labels: list[int],
    current_llm_name: str,
    contexts: solara.Reactive[list[Context]],
    summaries: solara.Reactive[list[Context]],
    prompt_summary: solara.Reactive[str]
    ):
    """Summarize all documents by cluster using the provided LLM.
    
    ## Arguments

    * `documents`: all the documents.
    * `labels`: all the associated labels for each document.
    * `summary_prompt`: the current llm to summarize with,
    * `contexts`: all existing contexts. Each new cluster summary will create a new context.
    * `summaries`: index of all context that are generated during summarization.
    """

    logger.info("Sumarizing All")

    doc_clusters: defaultdict[int,list[Document]] = defaultdict(list) 
    for doc, label in zip(documents, labels):
        doc_clusters[label].append(doc)

    res_summaries_ = []

    for label, docs in doc_clusters.items():
        if label == -1:
            continue  # ignore unlabeled data
        docs_dict = {doc.id: doc for doc in docs}
        logger.info(f"Summarize cluster {label} with docs {(',').join(docs_dict.keys())}")
        context = Context(name=f"summary_cluster_{label}", documents=docs_dict, prompt=prompt_summary.value)
        messages = [{"role": config.LLM_ROLE, "content":context.to_markdown()} ]
        resp = chat_request(current_llm_name, messages)
        summary = Document(text=resp["message"]["content"], type=DocType.SUMMARY, title=f"Summary for cluster {str(label)}")
        context.documents[summary.id] = summary

        res_summaries_.append(context)
        contexts.value = [*contexts.value, context]
        summaries.value = [*summaries.value, context]

        if SUMMARY_CUTOFF > 0 and len(res_summaries_) >= SUMMARY_CUTOFF:
            break


def serialize_summary(summary: dict[str, Any]):
    docs = [
        f"{doc_id}: {doc_title}"
        for doc_id, doc_title in zip(summary["cluster_id"], summary["doc_titles"])
    ]
    docs_ids = (", ").join(docs)
    return f"""
    ### summary of topic {summary['cluster_id']} 
    
    ##### (docs: {docs_ids} )
     
    {summary['summary']}"""


@task
async def build_outline(
    contexts: solara.Reactive[list[Context]],
    summary_contexts: solara.Reactive[list[Context]],
    current_llm_name: str,
    outline_doc: solara.Reactive[Document],
    prompt_outline: solara.Reactive[str]
    ) -> bool:
    """Build outline."""

    logger.info(f"build_outline from {len(summary_contexts.value)} summaries...")

    summaries: dict[str,Document] = {}
    for context in summary_contexts.value:
        context_summary = {doc_id: doc for (doc_id, doc) in context.documents.items() if doc.type == DocType.SUMMARY}
        summaries = {**summaries, **context_summary}
    context = Context(name=f"outline", documents=summaries, prompt=prompt_outline.value)
    messages = [{"role":config.LLM_ROLE, "content":context.to_markdown()}]
    resp = chat_request(current_llm_name, messages)
    outline_txt = resp["message"]["content"]
    outline_doc.value = Document(text=outline_txt, type=DocType.USER_TEXT, title=f"Literature Survey Outline")
    context.documents.update({outline_doc.value.id: outline_doc.value})

    contexts.value = [*contexts.value, context]

    return outline_txt
