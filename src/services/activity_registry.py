"""Activity registry for Temporal workers.

Registers built-in primitives and activity operations loaded from the database.
"""

import importlib
from typing import Dict, List, Callable, Any, Optional
from temporalio import activity


class ActivityRegistry:
    """Registry for Temporal activities from activity operations."""

    def __init__(self):
        self.activities: Dict[str, Callable] = {}
        self._register_built_in_activities()

    def _register_built_in_activities(self):
        """Register built-in primitive activities."""

        @activity.defn(name="net.http.request")
        async def http_request(config: Dict[str, Any]) -> Dict[str, Any]:
            """Execute HTTP request."""
            import httpx

            method = config.get("method", "GET")
            url = config.get("url")
            headers = config.get("headers", {})
            body = config.get("body")

            if not url:
                return {"error": "No URL provided"}

            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method, url=url, headers=headers, content=body
                )
                return {
                    "status_code": response.status_code,
                    "body": response.text,
                    "headers": dict(response.headers),
                }

        @activity.defn(name="files.read")
        async def files_read(config: Dict[str, Any]) -> Dict[str, Any]:
            """Read file."""
            path = config.get("path")
            if not path:
                return {"error": "No path provided"}

            try:
                with open(path, "r") as f:
                    content = f.read()
                return {"content": content, "path": path}
            except Exception as e:
                return {"error": str(e)}

        @activity.defn(name="files.write")
        async def files_write(config: Dict[str, Any]) -> Dict[str, Any]:
            """Write file."""
            path = config.get("path")
            content = config.get("content")

            if not path:
                return {"error": "No path provided"}

            try:
                with open(path, "w") as f:
                    f.write(content or "")
                return {"success": True, "path": path}
            except Exception as e:
                return {"error": str(e)}

        self.activities["net.http.request"] = http_request
        self.activities["files.read"] = files_read
        self.activities["files.write"] = files_write

    def register_activity_operation(
        self,
        operation_name: str,
        code_symbol: str,
        implementation: Optional[Callable[..., Any]] = None,
    ) -> None:
        """
        Register an activity operation as a Temporal activity.

        Args:
            operation_name: Unique name for the activity
            code_symbol: Python import path (e.g., "activities.email.filter_important")
            implementation: Optional actual implementation function
        """

        if implementation is not None:
            # Use provided implementation
            activity_func = activity.defn(name=code_symbol)(implementation)
            self.activities[code_symbol] = activity_func
        else:
            # Create a dynamic stub that imports the actual code
            @activity.defn(name=code_symbol)
            async def dynamic_activity(config: Dict[str, Any]) -> Dict[str, Any]:
                """Dynamically imported activity."""
                try:
                    # Import the module and function
                    module_path, func_name = code_symbol.rsplit(".", 1)
                    if not module_path.startswith("workspace."):
                        return {"error": "Invalid module path: only workspace modules are allowed"}
                    module = importlib.import_module(module_path)
                    func = getattr(module, func_name)

                    # Call the function
                    if callable(func):
                        result = func(config)
                        # Handle async functions
                        if hasattr(result, "__await__"):
                            result = await result
                        return result
                    else:
                        return {"error": f"{code_symbol} is not callable"}

                except ImportError as e:
                    return {"error": f"Failed to import {code_symbol}: {str(e)}"}
                except Exception as e:
                    return {"error": f"Failed to execute {code_symbol}: {str(e)}"}

            self.activities[code_symbol] = dynamic_activity

    def get_all_activities(self) -> List[Callable]:
        """Get all registered activities for the worker."""
        return list(self.activities.values())

    def load_activity_operations_from_db(
        self,
        activity_operations: List[Dict[str, Any]],
        known_symbols: Optional[set] = None,
    ):
        """
        Load activity operations from database and register as Temporal activities.

        Args:
            activity_operations: List of activity operation dicts with code_symbol, name, etc.
            known_symbols: Optional set of activity names already registered with the
                worker. Operations matching these names are skipped to avoid duplicates.
        """
        known = known_symbols or set()
        for op in activity_operations:
            code_symbol = op.get("code_symbol")
            name = op.get("name")
            if code_symbol and code_symbol not in self.activities and code_symbol not in known:
                self.register_activity_operation(
                    operation_name=name or code_symbol, code_symbol=code_symbol
                )
