from collections import defaultdict
from collections.abc import AsyncIterable
from datetime import datetime
from typing import Any
from uuid import uuid4

from agentflow.core.exceptions.media_exceptions import UnsupportedMediaInputError
from agentflow.core.graph import CompiledGraph
from agentflow.core.state import AgentState, Message, StreamChunk, StreamEvent
from agentflow.storage.checkpointer import BaseCheckpointer
from agentflow.utils.thread_info import ThreadInfo
from fastapi import HTTPException
from injectq import InjectQ, inject, singleton
from pydantic import BaseModel

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.core.config.graph_config import GraphConfig
from agentflow_cli.src.app.core.utils.log_sanitizer import sanitize_for_logging
from agentflow_cli.src.app.routers.graph.schemas.graph_schemas import (
    GraphInputSchema,
    GraphInvokeOutputSchema,
    GraphSchema,
    GraphSetupSchema,
    GraphToolsSchema,
    ObsEventSchema,
    ObsRunSchema,
    ObsSpanSchema,
    ObsTokenUsageSchema,
    ObservabilitySchema,
    ToolNodeSchema,
    ToolSchema,
)
from agentflow_cli.src.app.routers.graph.services.multimodal_preprocessor import (
    preprocess_multimodal_messages,
)
from agentflow_cli.src.app.utils import DummyThreadNameGenerator, ThreadNameGenerator
from agentflow_cli.src.app.utils.telemetry_store import TelemetryStore


@singleton
class GraphService:
    """
    Service class for graph-related operations.

    This class acts as an intermediary between the controllers and the
    CompiledGraph, facilitating graph execution operations.
    """

    @inject
    def __init__(
        self,
        graph: CompiledGraph,
        checkpointer: BaseCheckpointer,
        config: GraphConfig,
        thread_name_generator: ThreadNameGenerator | None = None,
    ):
        """
        Initializes the GraphService with a CompiledGraph instance.

        Args:
            graph (CompiledGraph): An instance of CompiledGraph for
                                   graph execution operations.
        """
        self._graph = graph
        self.config = config
        self.checkpointer = checkpointer
        self.thread_name_generator = thread_name_generator

        # Telemetry store is optional (bound in the loader). Resolve lazily so unit
        # tests that construct GraphService directly don't require the binding.
        self._telemetry: TelemetryStore | None = None

        # Lazy import to avoid circular dependency
        self._media_service = None

    @property
    def is_live_agent(self) -> bool:
        """Whether the configured graph is a realtime (live) agent.

        A live graph must be driven over the ``/v1/graph/live`` realtime WebSocket; a
        non-live (turn-based) graph must use ``/v1/graph/ws``. The WebSocket handlers use
        this to reject the wrong agent type up front.

        Prefers the public ``CompiledGraph.is_realtime()`` (newer core releases) and falls
        back to the internal ``_find_live_nodes()`` probe on releases that predate it.
        """
        is_realtime = getattr(self._graph, "is_realtime", None)
        if callable(is_realtime):
            return bool(is_realtime())
        find_live_nodes = getattr(self._graph, "_find_live_nodes", None)
        if callable(find_live_nodes):
            return bool(find_live_nodes())
        return False

    @property
    def media_service(self):
        if self._media_service is None:
            try:
                container = InjectQ.get_instance()
                from agentflow_cli.src.app.routers.media import MediaService

                self._media_service = container.try_get(MediaService)
            except Exception:
                self._media_service = None
        return self._media_service

    async def _save_thread_name(
        self,
        config: dict[str, Any],
        thread_id: int,
        messages: list[str],
    ) -> str:
        """
        Save the generated thread name to the database.
        """
        if not self.thread_name_generator:
            thread_name = await DummyThreadNameGenerator().generate_name([])
            logger.debug("No thread name generator configured, using dummy thread name generator.")
            return thread_name

        thread_name = await self.thread_name_generator.generate_name(messages)

        res = await self.checkpointer.aput_thread(
            config,
            ThreadInfo(thread_id=thread_id, thread_name=thread_name),
        )
        if res:
            logger.info(f"Generated thread name: {thread_name} for thread_id: {thread_id}")

        return thread_name

    async def _save_thread(self, config: dict[str, Any], thread_id: str):
        """
        Save the generated thread name to the database.
        """
        return await self.checkpointer.aput_thread(
            config,
            ThreadInfo(thread_id=thread_id),
        )

    def _extract_context_info(
        self, raw_state, result: dict[str, Any]
    ) -> tuple[list[Message] | None, str | None]:
        """Extract context and context_summary from result or state."""
        context: list[Message] | None = result.get("context")
        context_summary: str | None = result.get("context_summary")

        # If not found, try reading from state (supports both dict and model)
        if not context_summary and raw_state is not None:
            try:
                if isinstance(raw_state, dict):
                    context_summary = raw_state.get("context_summary")
                else:
                    context_summary = getattr(raw_state, "context_summary", None)
            except Exception:
                context_summary = None

        if not context and raw_state is not None:
            try:
                if isinstance(raw_state, dict):
                    context = raw_state.get("context")
                else:
                    context = getattr(raw_state, "context", None)
            except Exception:
                context = None

        return context, context_summary

    @property
    def telemetry(self) -> TelemetryStore | None:
        """The bound TelemetryStore, if any (resolved lazily, cached)."""
        if self._telemetry is None:
            try:
                self._telemetry = InjectQ.get_instance().try_get(TelemetryStore)
            except Exception:
                self._telemetry = None
        return self._telemetry

    @staticmethod
    def _telemetry_record(chunk: Any) -> dict[str, Any]:
        """Flatten a StreamChunk into a compact record for the telemetry store."""
        md = getattr(chunk, "metadata", None) or {}
        node = md.get("node") or md.get("current_node") or getattr(chunk, "node_name", "") or ""

        usages = None
        message = getattr(chunk, "message", None)
        if message is not None:
            u = getattr(message, "usages", None)
            if u is not None:
                try:
                    usages = u.model_dump() if hasattr(u, "model_dump") else dict(u)
                except Exception:
                    usages = None

        # Tool call / tool result hints for span reconstruction.
        content_kinds: list[str] = []
        tool_names: list[str] = []
        if message is not None:
            content = getattr(message, "content", None)
            if isinstance(content, list):
                for block in content:
                    btype = getattr(block, "type", None) or (
                        block.get("type") if isinstance(block, dict) else None
                    )
                    if btype:
                        content_kinds.append(btype)
                    if btype in ("tool_call", "tool_result"):
                        bname = getattr(block, "name", None) or (
                            block.get("name") if isinstance(block, dict) else None
                        )
                        if bname:
                            tool_names.append(bname)

        event = getattr(chunk, "event", None)
        return {
            "event": str(event.value) if hasattr(event, "value") else str(event or ""),
            "node": node,
            "timestamp": getattr(chunk, "timestamp", None),
            "is_delta": bool(getattr(message, "delta", False)) if message else False,
            "role": getattr(message, "role", None) if message else None,
            "usages": usages,
            "content_kinds": content_kinds,
            "tool_names": tool_names,
            "is_error": bool(getattr(chunk, "is_error", False)),
        }

    def _record_chunk(self, thread_id: str, run_id: str, chunk: Any) -> None:
        store = self.telemetry
        if not store:
            return
        try:
            store.record(thread_id, run_id, self._telemetry_record(chunk))
        except Exception as e:  # noqa: BLE001 - telemetry must never break a run
            logger.debug("Telemetry record failed: %s", e)

    async def stop_graph(
        self,
        thread_id: str,
        user: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Stop the graph execution for a specific thread.

        Args:
            thread_id (str): The thread ID to stop
            user (dict): User information for context
            config (dict, optional): Additional configuration for the stop operation

        Returns:
            dict: Stop result with status information

        Raises:
            HTTPException: If stop operation fails or user doesn't have permission.
        """
        try:
            logger.info(f"Stopping graph execution for thread: {thread_id}")
            logger.debug(f"User info: {sanitize_for_logging(user)}")

            # Prepare config with thread_id and user info
            stop_config = {
                "thread_id": thread_id,
                "user": user,
            }

            # Merge additional config if provided
            if config:
                stop_config.update(config)

            # Call the graph's astop method
            result = await self._graph.astop(stop_config)

            logger.info(f"Graph stop completed for thread {thread_id}: {result}")
            return result

        except ValueError as e:
            logger.warning(f"Graph stop input validation failed for thread {thread_id}: {e}")
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            logger.error(f"Graph stop failed for thread {thread_id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Graph stop failed for thread {thread_id}: {e!s}"
            )

    async def _prepare_input(
        self,
        graph_input: GraphInputSchema,
    ):
        is_new_thread = False
        config = graph_input.config or {}
        if config.get("thread_id") and str(config["thread_id"]).strip():
            thread_id = str(config["thread_id"]).strip()
        else:
            thread_id = await InjectQ.get_instance().atry_get("generated_id") or str(uuid4())
            is_new_thread = True

        # update thread id
        config["thread_id"] = str(thread_id)

        # check recursion limit set or not
        config["recursion_limit"] = graph_input.recursion_limit or 25

        # Prepare the input for the graph
        # Preprocess multimodal messages (resolve file_id → cached text, etc.)
        preprocessed = await preprocess_multimodal_messages(
            graph_input.messages,
            self.media_service,
        )
        input_data: dict = {
            "messages": preprocessed,
        }
        if graph_input.initial_state:
            input_data["state"] = graph_input.initial_state

        return (
            input_data,
            config,
            {
                "is_new_thread": is_new_thread,
                "thread_id": str(thread_id),
            },
        )

    async def invoke_graph(
        self,
        graph_input: GraphInputSchema,
        user: dict[str, Any],
    ) -> GraphInvokeOutputSchema:
        """
        Invokes the graph with the provided input and returns the final result.

        Args:
            graph_input (GraphInputSchema): The input data for graph execution.

        Returns:
            GraphInvokeOutputSchema: The final result from graph execution.

        Raises:
            HTTPException: If graph execution fails.
        """
        try:
            logger.debug(f"Invoking graph with input: {graph_input.messages}")

            # Prepare the input
            input_data, config, meta = await self._prepare_input(graph_input)
            # add user inside config
            config["user"] = user
            config["user_id"] = user.get("user_id", "anonymous")

            # Try to save thread info in the db even for existing threads
            # this will help in updating last accessed time
            # and get is thread newly created or not, this way it's consistent
            is_new_thread = await self._save_thread(config, config["thread_id"])
            if is_new_thread and type(is_new_thread) is bool:
                meta["is_new_thread"] = True

            # Telemetry run (invoke has no chunk stream; we record from the final
            # messages so cost/usage still shows on the observability page).
            inv_thread_id = str(config["thread_id"])
            inv_run_id = str(config.get("run_id") or uuid4())
            config.setdefault("run_id", inv_run_id)
            inv_started = datetime.now().timestamp()
            if self.telemetry:
                self.telemetry.start_run(inv_thread_id, inv_run_id, inv_started)

            # Execute the graph
            result = await self._graph.ainvoke(
                input_data,
                config=config,
                response_granularity=graph_input.response_granularity,
            )

            logger.info("Graph execution completed successfully")

            # Extract messages and state from result
            messages: list[Message] = result.get("messages", [])

            # Record final messages into telemetry, then close the run.
            if self.telemetry:
                for msg in messages:
                    self._record_chunk(
                        inv_thread_id,
                        inv_run_id,
                        StreamChunk(
                            event=StreamEvent.MESSAGE,
                            message=msg,
                            metadata={"node": getattr(msg, "node", "") or ""},
                            timestamp=datetime.now().timestamp(),
                        ),
                    )
                self.telemetry.finish_run(
                    inv_thread_id, inv_run_id, datetime.now().timestamp(), "done"
                )
            raw_state: AgentState | None = result.get("state", None)

            # Extract context information using helper method
            context, context_summary = self._extract_context_info(raw_state, result)

            if meta["is_new_thread"] and self.config.thread_name_generator_path:
                messages_str = [msg.text() for msg in messages]
                thread_name = await self._save_thread_name(
                    config, config["thread_id"], messages_str
                )
                meta["thread_name"] = thread_name

            return GraphInvokeOutputSchema(
                messages=messages,
                state=raw_state.model_dump(serialize_as_any=True) if raw_state else None,
                context=context,
                summary=context_summary,
                meta=meta,
            )

        except UnsupportedMediaInputError as e:
            logger.warning("Unsupported media input: %s", e.message)
            raise HTTPException(status_code=422, detail=e.message)
        except ValueError as e:
            logger.warning(f"Graph input validation failed: {e}")
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            logger.error(f"Graph execution failed: {e}")
            raise HTTPException(status_code=500, detail=f"Graph execution failed: {e!s}")

    async def stream_graph(
        self,
        graph_input: GraphInputSchema,
        user: dict[str, Any],
    ) -> AsyncIterable[str]:
        """
        Streams the graph execution with the provided input.

        Args:
            graph_input (GraphInputSchema): The input data for graph execution.
            stream_mode (str): The stream mode ("values", "updates", "messages", etc.).

        Yields:
            str: Individual JSON chunks from graph execution with newline delimiters.
        """
        # Initialize meta here so it is available in the except blocks even if
        # _prepare_input raises before assigning it.
        meta: dict[str, Any] = {}
        thread_id: str | None = None
        run_id: str | None = None
        try:
            logger.debug(f"Streaming graph with input: {graph_input.messages}")

            # Prepare the config
            input_data, config, meta = await self._prepare_input(graph_input)
            # add user inside config
            config["user"] = user
            config["user_id"] = user.get("user_id", "anonymous")

            # Try to save thread info in the db even for existing threads
            # this will help in updating last accessed time
            # and get is thread newly created or not, this way it's consistent
            is_new_thread = await self._save_thread(config, config["thread_id"])
            if is_new_thread and type(is_new_thread) is bool:
                meta["is_new_thread"] = True

            messages_str = []

            # Begin a telemetry run so the observability endpoint can rebuild the trace.
            thread_id = str(config["thread_id"])
            run_id = str(config.get("run_id") or uuid4())
            config.setdefault("run_id", run_id)
            started_at = datetime.now().timestamp()
            if self.telemetry:
                self.telemetry.start_run(thread_id, run_id, started_at)
            run_status = "done"

            # Stream the graph execution
            async for chunk in self._graph.astream(
                input_data,
                config=config,
                response_granularity=graph_input.response_granularity,
            ):
                mt = chunk.metadata or {}
                mt.update(meta)
                chunk.metadata = mt
                self._record_chunk(thread_id, run_id, chunk)
                if getattr(chunk, "is_error", False) or getattr(chunk, "event", None) in (
                    "error",
                    StreamEvent.ERROR,
                ):
                    run_status = "error"
                yield chunk.model_dump_json(serialize_as_any=True) + "\n"
                if (
                    self.config.thread_name_generator_path
                    and meta["is_new_thread"]
                    and chunk.event == StreamEvent.MESSAGE
                    and chunk.message
                    and not chunk.message.delta
                ):
                    messages_str.append(chunk.message.text())

            logger.info("Graph streaming completed successfully")

            if self.telemetry:
                self.telemetry.finish_run(
                    thread_id, run_id, datetime.now().timestamp(), run_status
                )

            if meta["is_new_thread"] and self.config.thread_name_generator_path:
                thread_name = await self._save_thread_name(
                    config, config["thread_id"], messages_str
                )
                meta["thread_name"] = thread_name

                yield (
                    StreamChunk(
                        event=StreamEvent.UPDATES,
                        data={"status": "completed"},
                        metadata=meta,
                    ).model_dump_json(serialize_as_any=True)
                    + "\n"
                )

        except Exception as e:
            # Never raise HTTPException from inside an async generator that is
            # consumed by StreamingResponse.  By the time any exception is raised
            # from within the generator body, Starlette has already committed to a
            # 200 OK response and cannot replace it with a 4xx/5xx.  Raising here
            # would cause: RuntimeError("Caught handled exception, but response
            # already started.")  Instead, we yield a structured error chunk so
            # the client can detect and display the failure.
            logger.error(f"Graph streaming failed: {e}")
            try:
                if self.telemetry and thread_id and run_id:
                    self.telemetry.finish_run(
                        thread_id, run_id, datetime.now().timestamp(), "error"
                    )
            except Exception:
                pass
            yield (
                StreamChunk(
                    event=StreamEvent.ERROR,
                    data={"reason": str(e)},
                    metadata=meta,
                ).model_dump_json(serialize_as_any=True)
                + "\n"
            )

    async def realtime_graph(
        self,
        input_queue: Any,
        init: dict[str, Any],
        user: dict[str, Any],
    ):
        """Bridge a realtime (audio) session over the compiled graph.

        Thin wrapper over ``CompiledGraph.arealtime``: builds the per-session config from
        the init control frame + authenticated user, persists thread info, and yields the
        normalized RealtimeEvents. The compiled graph must be rooted at a LiveAgent (e.g.
        an ``AudioAgent``); otherwise ``arealtime`` raises.
        """
        thread_id = init.get("thread_id") or str(uuid4())
        config: dict[str, Any] = {
            "thread_id": thread_id,
            "user": user,
            "user_id": user.get("user_id", "anonymous"),
        }
        # Map the client init frame onto RealtimeConfig field names so the live agent can
        # apply per-session overrides (model/voice/modalities/vad/...). Only present keys
        # are forwarded; absent ones fall back to the agent's build-time config.
        realtime = self._realtime_overrides(init)
        if realtime:
            config["realtime"] = realtime
        await self._save_thread(config, thread_id)
        logger.info("Realtime graph session starting: thread_id=%s", thread_id)

        async for event in self._graph.arealtime(input_queue, config):
            yield event

        logger.info("Realtime graph session completed: thread_id=%s", thread_id)

    @staticmethod
    def _realtime_overrides(init: dict[str, Any]) -> dict[str, Any]:
        """Translate the client init frame into RealtimeConfig field overrides."""
        # init key -> RealtimeConfig field name
        mapping = {
            "model": "model",
            "voice": "voice",
            "modalities": "response_modalities",
            "vad": "vad",
            "system_prompt": "system_instruction",
            "tools_tags": "tools_tags",
        }
        overrides: dict[str, Any] = {}
        for init_key, field in mapping.items():
            value = init.get(init_key)
            if value is not None:
                overrides[field] = value
        # Clients commonly send a single modality as a bare string ("AUDIO"); RealtimeConfig
        # expects a list. Coerce so the shorthand doesn't trip the one-modality validator.
        if isinstance(overrides.get("response_modalities"), str):
            overrides["response_modalities"] = [overrides["response_modalities"]]
        return overrides

    async def graph_details(self) -> GraphSchema:
        try:
            logger.info("Getting graph details")
            res = self._graph.generate_graph()
            return GraphSchema(**res)
        except ValueError as e:
            logger.warning(f"Graph details validation failed: {e}")
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to get graph details: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get graph details: {e!s}")

    async def get_tools(self) -> GraphToolsSchema:
        """Collect the tools exposed by every ToolNode in the graph.

        Walks the compiled graph's nodes, and for each ``ToolNode`` calls
        ``all_tools()`` (which resolves local functions, MCP tools from any
        connected server, and remote/client-registered tools). Each tool is
        tagged with its ``source`` so the UI can group them.

        A failing MCP server on one node does not break the endpoint: that node's
        tools are collected best-effort and the error is logged.
        """
        # Local import to avoid a hard dependency at module import time.
        from agentflow.core.graph import ToolNode

        state_graph = getattr(self._graph, "_state_graph", None)
        nodes = getattr(state_graph, "nodes", {}) if state_graph else {}

        node_schemas: list[ToolNodeSchema] = []
        total_tools = 0

        for node_name, node in nodes.items():
            tool_node = getattr(node, "func", None)
            if not isinstance(tool_node, ToolNode):
                continue

            try:
                raw_tools = await tool_node.all_tools()
            except Exception as e:  # noqa: BLE001 - one bad MCP server shouldn't 500 the page
                logger.warning("Failed to list tools for node '%s': %s", node_name, e)
                raw_tools = []

            # After all_tools(), these hold the names by origin.
            local_names = set(getattr(tool_node, "_funcs", {}).keys())
            mcp_names = set(getattr(tool_node, "mcp_tools", []) or [])
            remote_names = set(getattr(tool_node, "remote_tool_names", []) or [])

            tools: list[ToolSchema] = []
            for entry in raw_tools:
                fn = entry.get("function", {}) if isinstance(entry, dict) else {}
                name = fn.get("name", "")
                if name in mcp_names:
                    source = "mcp"
                elif name in remote_names:
                    source = "remote"
                elif name in local_names:
                    source = "local"
                else:
                    # Unknown origin — default to local (a plain function schema).
                    source = "local"

                tools.append(
                    ToolSchema(
                        name=name,
                        description=fn.get("description", "") or "",
                        source=source,
                        parameters=fn.get("parameters", {}) or {},
                    )
                )

            total_tools += len(tools)
            node_schemas.append(
                ToolNodeSchema(
                    node_name=node_name,
                    tool_count=len(tools),
                    tools=tools,
                )
            )

        return GraphToolsSchema(
            node_count=len(node_schemas),
            tool_count=total_tools,
            nodes=node_schemas,
        )

    async def get_observability(
        self,
        thread_id: str,
        run_id: str | None = None,
    ) -> "ObservabilitySchema":
        """Reconstruct an observability trace for a thread from captured run events.

        Rebuilds spans (root → node → llm/tool), an event list, and aggregated
        token usage from the telemetry records a run emitted. Returns the latest
        run by default, or the requested ``run_id``.
        """
        store = self.telemetry
        if not store:
            return ObservabilitySchema(thread_id=str(thread_id), run_count=0)

        runs = store.get_runs(thread_id)
        run_ids = [r.run_id for r in runs]

        trace = None
        if run_id:
            trace = store.get_run(thread_id, run_id)
        elif runs:
            trace = runs[-1]

        if trace is None:
            return ObservabilitySchema(
                thread_id=str(thread_id),
                run_count=len(runs),
                run_ids=run_ids,
                run=None,
            )

        run_schema = self._reconstruct_run(trace)
        return ObservabilitySchema(
            thread_id=str(thread_id),
            run_count=len(runs),
            run_ids=run_ids,
            run=run_schema,
        )

    def _reconstruct_run(self, trace: Any) -> "ObsRunSchema":
        """Turn a captured RunTrace into spans + events + usage."""
        records = list(trace.records)
        started = trace.started_at
        # Fall back to the first record's timestamp if start wasn't stamped.
        first_ts = next((r.get("timestamp") for r in records if r.get("timestamp")), started)
        base = started or first_ts or 0.0
        last_ts = max(
            [r.get("timestamp") or base for r in records] + [trace.finished_at or base]
        )
        total_ms = max(0.0, (last_ts - base) * 1000.0)

        def off_ms(ts: float | None) -> float:
            return max(0.0, ((ts or base) - base) * 1000.0)

        usage = ObsTokenUsageSchema()
        events: list[ObsEventSchema] = []
        spans: list[ObsSpanSchema] = []

        # Root span spans the whole run.
        root_name = getattr(self._graph, "__class__", type(self._graph)).__name__
        spans.append(
            ObsSpanSchema(
                id="root",
                name="graph",
                kind="root",
                parent=None,
                start_ms=0.0,
                duration_ms=total_ms,
            )
        )

        # Walk records to build node spans (by node transitions) + llm/tool spans.
        node_spans: dict[str, ObsSpanSchema] = {}
        node_order: list[str] = []
        llm_calls = 0
        tool_calls = 0
        span_seq = 0

        def new_span_id() -> str:
            nonlocal span_seq
            span_seq += 1
            return f"s{span_seq}"

        for idx, rec in enumerate(records):
            node = rec.get("node") or "—"
            ts = rec.get("timestamp")
            ev_type = rec.get("event") or "message"

            # Node span: open on first sight of a node, extend its end as records arrive.
            if node and node != "—":
                span = node_spans.get(node)
                if span is None:
                    span = ObsSpanSchema(
                        id=new_span_id(),
                        name=f"node: {node}",
                        kind="node",
                        parent="root",
                        start_ms=off_ms(ts),
                        duration_ms=0.0,
                    )
                    node_spans[node] = span
                    node_order.append(node)
                    spans.append(span)
                else:
                    span.duration_ms = max(span.duration_ms, off_ms(ts) - span.start_ms)

            # LLM span: a non-delta assistant message with usages under this node.
            u = rec.get("usages")
            if u:
                usage.prompt_tokens += int(u.get("prompt_tokens", 0) or 0)
                usage.completion_tokens += int(u.get("completion_tokens", 0) or 0)
                usage.reasoning_tokens += int(u.get("reasoning_tokens", 0) or 0)
                usage.total_tokens += int(
                    u.get("total_tokens", 0)
                    or (u.get("prompt_tokens", 0) or 0) + (u.get("completion_tokens", 0) or 0)
                )
                llm_calls += 1
                parent = node_spans.get(node)
                spans.append(
                    ObsSpanSchema(
                        id=new_span_id(),
                        name="llm.generate",
                        kind="llm",
                        parent=parent.id if parent else "root",
                        start_ms=off_ms(ts),
                        duration_ms=0.0,
                        model=(rec.get("model") or None),
                        input_tokens=int(u.get("prompt_tokens", 0) or 0),
                        output_tokens=int(u.get("completion_tokens", 0) or 0),
                    )
                )

            # Tool spans: from tool_call / tool_result content blocks.
            for tname in rec.get("tool_names", []) or []:
                if "tool_call" in (rec.get("content_kinds") or []):
                    tool_calls += 1
                    parent = node_spans.get(node)
                    spans.append(
                        ObsSpanSchema(
                            id=new_span_id(),
                            name=f"tool: {tname}",
                            kind="tool",
                            parent=parent.id if parent else "root",
                            start_ms=off_ms(ts),
                            duration_ms=0.0,
                        )
                    )

            # Event row.
            events.append(
                ObsEventSchema(
                    id=f"e{idx}",
                    type=ev_type,
                    node=node if node != "—" else "",
                    offset_ms=off_ms(ts),
                    summary=self._event_summary(rec),
                )
            )

        # Newest-first events for the pane.
        events.reverse()

        return ObsRunSchema(
            run_id=trace.run_id,
            thread_id=trace.thread_id,
            status=trace.status,
            started_at=trace.started_at,
            finished_at=trace.finished_at,
            duration_ms=total_ms,
            spans=spans,
            events=events,
            usage=usage,
            llm_calls=llm_calls,
            tool_calls=tool_calls,
            iterations=len(node_order),
        )

    @staticmethod
    def _event_summary(rec: dict[str, Any]) -> str:
        kinds = rec.get("content_kinds") or []
        tools = rec.get("tool_names") or []
        if rec.get("is_error"):
            return "error"
        if tools and "tool_call" in kinds:
            return f"tool_call {', '.join(tools)}"
        if tools and "tool_result" in kinds:
            return f"tool_result {', '.join(tools)}"
        if rec.get("usages"):
            u = rec["usages"]
            return f"llm.generate · {u.get('total_tokens', 0)} tokens"
        if rec.get("is_delta"):
            return "delta"
        if kinds:
            return f"{rec.get('role') or 'message'}: {', '.join(kinds)}"
        return rec.get("event") or "chunk"

    async def get_state_schema(self) -> dict:
        try:
            logger.info("Getting state schema")
            res: BaseModel = self._graph._state
            return res.model_json_schema()
        except ValueError as e:
            logger.warning(f"State schema validation failed: {e}")
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to get state schema: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get state schema: {e!s}")

    def _has_empty_tool_call(self, msg: Message) -> bool:
        """Return True if any tool call on the message has empty content.

        A tool call is considered empty if its ``content`` attribute/key is ``None`` or
        an empty string. Tool calls may be dict-like or objects with a ``content`` attribute.
        """
        tool_calls = getattr(msg, "tools_calls", None)
        if not tool_calls:
            return False
        for tool_call in tool_calls:
            content = (
                tool_call.get("content")
                if isinstance(tool_call, dict)
                else getattr(tool_call, "content", None)
            )
            if content in (None, ""):
                return True
        return False

    async def fix_graph(
        self,
        thread_id: str,
        user: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Fix graph state by removing messages with empty tool call content.

        This method retrieves the current state from the checkpointer, identifies messages
        with tool calls that have empty content, removes those messages, and updates the
        state.

        Args:
            thread_id (str): The thread ID to fix the graph state for
            user (dict): User information for context
            config (dict, optional): Additional configuration for the operation

        Returns:
            dict: Result dictionary containing:
                - success (bool): Whether the operation was successful
                - message (str): Status message
                - removed_count (int): Number of messages removed
                - state (dict): Updated state after fixing

        Raises:
            HTTPException: If the operation fails
        """
        try:
            logger.info(f"Starting fix graph operation for thread: {thread_id}")
            logger.debug(f"User info: {sanitize_for_logging(user)}")

            fix_config = {"thread_id": thread_id, "user": user}
            fix_config["user_id"] = user.get("user_id", "anonymous")
            if config:
                fix_config.update(config)

            logger.debug("Fetching current state from checkpointer")
            state: AgentState | None = await self.checkpointer.aget_state(fix_config)
            if not state:
                logger.warning(f"No state found for thread: {thread_id}")
                return {
                    "success": False,
                    "message": f"No state found for thread: {thread_id}",
                    "removed_count": 0,
                    "state": None,
                }

            messages: list[Message] = list(state.context or [])
            logger.debug(f"Found {len(messages)} messages in state")
            if not messages:
                return {
                    "success": True,
                    "message": "No messages found in state",
                    "removed_count": 0,
                    "state": state.model_dump_json(serialize_as_any=True),
                }

            filtered = [m for m in messages if not self._has_empty_tool_call(m)]
            removed_count = len(messages) - len(filtered)

            if removed_count:
                state.context = filtered
                await self.checkpointer.aput_state(fix_config, state)
                message = f"Successfully removed {removed_count} message(s)"
            else:
                message = "No messages with empty tool calls found"

            return {
                "success": True,
                "message": message,
                "removed_count": removed_count,
                "state": state.model_dump_json(serialize_as_any=True),
            }
        except ValueError as e:
            logger.warning(f"Fix graph input validation failed: {e}")
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            logger.error(f"Fix graph operation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Fix graph operation failed: {e!s}")

    async def setup(self, data: GraphSetupSchema) -> dict:
        # lets create tools
        remote_tools = defaultdict(list)
        for tool in data.tools:
            remote_tools[tool.node_name].append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )

        # Now call setup on graph
        for node_name, tool in remote_tools.items():
            self._graph.attach_remote_tools(tool, node_name)

        return {
            "status": "success",
            "details": f"Added tools to nodes: {list(remote_tools.keys())}",
        }
