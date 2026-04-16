import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class MockLLMHandler(BaseHTTPRequestHandler):
    server_version = "MockLLM/1.0"

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/tags":
            self._send_json({"models": [{"name": "mock-llm"}]})
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self._send_json({"error": "not found"}, status=404)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            payload = {}

        user_message = ""
        for message in payload.get("messages", []):
            if message.get("role") == "user":
                user_message = message.get("content", "")

        answer = (
            "Mock answer: This astrobiology platform processes PDF literature, "
            "indexes document chunks, and supports QA over extracted knowledge. "
            f"Question received: {user_message}"
        )

        self._send_json(
            {
                "id": "mock-chatcmpl-1",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": answer,
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 32,
                    "completion_tokens": 32,
                    "total_tokens": 64,
                },
            }
        )

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 11434), MockLLMHandler)
    server.serve_forever()
