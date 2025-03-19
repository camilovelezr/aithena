"""Endpoints to test individual agents."""

from fastapi import APIRouter

from polus.aithena.ask_aithena.agents.context_retriever import retrieve_context
from polus.aithena.ask_aithena.agents.semantic_extractor import run_semantic_agent

router = APIRouter(prefix="/test")


@router.get("/")
async def root():
    return {"message": "I'm Ask Aithena, who are you?"}


@router.post("/semantic-agent")
async def semantic_agent(query: str = None, body: dict = None):
    if body and "query" in body:
        query_text = body["query"]
    else:
        query_text = query

    return await run_semantic_agent(query_text)


@router.post("/context-retriever")
async def context_retriever(query: str = None, body: dict = None):
    if body and "query" in body:
        query_text = body["query"]
    else:
        query_text = query
    return await retrieve_context(query_text).model_dump()
