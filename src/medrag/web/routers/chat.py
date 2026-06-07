"""WebSocket chat — streaming LLM responses token-by-token.

Supports folder-scoped search and hereditary cross-family search.
Persists conversation history after each exchange.
"""

from __future__ import annotations

import asyncio
import json
import threading

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from medrag.pipeline import MedRAGPipeline
from medrag.web.deps import get_pipeline

router = APIRouter(tags=["chat"])


@router.websocket("/ws/chat")
async def chat(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming chat with the RAG pipeline.

    Protocol:
      Client sends: {
        "type": "query",
        "data": {
          "question": "...",
          "top_k": 5,
          "folder_id": "fld_xxx" | null,
          "cross_folders": false,
          "conv_id": "conv_xxx" | null
        }
      }
      Server sends:
        {"type": "source", "data": {"filename": "..."}}
        {"type": "token", "data": {"content": "..."}}
        {"type": "done", "data": {"model": "...", "tokens_used": N}}
        {"type": "error", "data": {"message": "..."}}
    """
    await websocket.accept()

    pipeline = get_pipeline()

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg.get("type") != "query":
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Unknown message type. Send {type: 'query'}"},
                })
                continue

            data = msg.get("data", {})
            question = data.get("question", "").strip()
            top_k = data.get("top_k", 5)
            folder_id = data.get("folder_id")  # None = search all
            cross_folders = data.get("cross_folders", False)
            conv_id = data.get("conv_id")  # conversation to persist to

            if not question:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Question cannot be empty"},
                })
                continue

            # Check LM Studio connection
            if not pipeline.synthesizer.check_connection():
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "LM Studio is not running. Start it and load a model."},
                })
                continue

            # Ensure conversation exists before saving
            if folder_id and conv_id:
                existing = pipeline.load_conversation(folder_id, conv_id)
                if not existing:
                    # Create conversation on first query
                    conv = pipeline.create_conversation(folder_id)
                    # Use the server-generated conv_id going forward
                    conv_id = conv.conv_id
                pipeline.add_message(folder_id, conv_id, "user", question)

            # Run retrieval in thread pool (blocking)
            try:
                query_vec = await asyncio.to_thread(
                    pipeline.embedder.embed, question, "retrieval.query"
                )
                search_folder = folder_id if not cross_folders else None
                results = await asyncio.to_thread(
                    pipeline.database.search, query_vec, question, top_k, search_folder
                )
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"Search failed: {e}"},
                })
                continue

            if not results:
                await websocket.send_json({
                    "type": "done",
                    "data": {"model": "", "tokens_used": 0, "message": "No documents found"},
                })
                continue

            # Build folder context
            folder_context: dict | None = None
            if folder_id:
                folder_info = pipeline.folders.get_folder(folder_id)
                if folder_info:
                    folder_context = {
                        "name": folder_info.name,
                        "relationship": folder_info.relationship,
                    }

            if cross_folders:
                all_folders = pipeline.folders.list_folders()
                folder_context = {
                    "family_members": [
                        {"name": f.name, "relationship": f.relationship}
                        for f in all_folders
                    ]
                }

            # Stream synthesis
            context_docs = [(r.filename, r.markdown, r.folder_id) for r in results]
            loop = asyncio.get_event_loop()
            queue: asyncio.Queue[dict | None] = asyncio.Queue()

            collected_answer = []
            source_filenames = []

            def run_stream() -> None:
                try:
                    for event in pipeline.synthesizer.synthesize_stream(
                        question, context_docs,
                        folder_context=folder_context,
                        cross_folders=cross_folders,
                        query_vector=query_vec if cross_folders else None,
                    ):
                        if event["type"] == "source":
                            source_filenames.append(event["data"]["filename"])
                        if event["type"] == "token":
                            collected_answer.append(event["data"]["content"])
                        loop.call_soon_threadsafe(
                            lambda e=event: asyncio.ensure_future(queue.put(e))
                        )
                except Exception as e:
                    loop.call_soon_threadsafe(
                        lambda: asyncio.ensure_future(
                            queue.put({"type": "error", "data": {"message": str(e)}})
                        )
                    )
                finally:
                    loop.call_soon_threadsafe(
                        lambda: asyncio.ensure_future(queue.put(None))
                    )

            thread = threading.Thread(target=run_stream, daemon=True)
            thread.start()

            # Forward events from queue to WebSocket
            while True:
                event = await queue.get()
                if event is None:
                    break
                await websocket.send_json(event)

            # Save assistant message to conversation
            if folder_id and conv_id:
                answer_text = "".join(collected_answer)
                pipeline.add_message(
                    folder_id, conv_id, "assistant", answer_text,
                    sources=source_filenames,
                )
                # Send the server-assigned conv_id back to client
                await websocket.send_json({
                    "type": "conv_id",
                    "data": {"conv_id": conv_id},
                })

            # Send disclaimer if hereditary search
            if cross_folders:
                from medrag.synthesis.hereditary_matcher import HEREDITARY_SEARCH_DISCLAIMER
                await websocket.send_json({
                    "type": "disclaimer",
                    "data": {"message": HEREDITARY_SEARCH_DISCLAIMER},
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "data": {"message": str(e)}})
        except Exception:
            pass