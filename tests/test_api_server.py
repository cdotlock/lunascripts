import asyncio
import hashlib
import io
import json
from pathlib import Path
import re
import unittest
import zipfile
from unittest.mock import patch

from fastapi import HTTPException, UploadFile

import api_server


CANONICAL_SOURCE = b'''@episode main:01 "API contract" {
  @bg castle_exterior_day fade
  NARRATOR: The compiler is current.
  @gate {
    @next main:02
  }
}
'''


class ApiServerIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_ready_proves_the_canonical_bg_contract(self):
        response = await api_server.ready()
        self.assertEqual(response["status"], "ready")
        self.assertEqual(response["ls_contract_version"], "3.0.0")

        upload = UploadFile(file=io.BytesIO(CANONICAL_SOURCE), filename="canonical.ls")
        compiled_response = await api_server.compile_script(upload, assets=None)
        self.assertEqual(compiled_response.status_code, 200)
        result = json.loads(compiled_response.body)
        self.assertEqual(result["ls_contract_version"], "3.0.0")
        self.assertEqual(result["steps"][0]["name"], "castle_exterior_day")
        self.assertEqual(result["steps"][0]["transition"], "fade")

    async def test_version_exposes_contract_and_revision_fields(self):
        response = await api_server.version()
        self.assertEqual(
            set(response),
            {"service", "api_version", "ls_contract_version", "source_revision"},
        )
        self.assertEqual(response["ls_contract_version"], "3.0.0")
        self.assertEqual(
            response["source_revision"],
            json.loads(Path("build-info.json").read_text(encoding="utf-8"))["source_revision"],
        )

    async def test_spec_index_and_resources_are_revision_bound(self):
        index = await api_server.spec_index()
        names = {resource["name"] for resource in index["resources"]}
        self.assertEqual(names, {"ls-spec", "json-output"})
        self.assertEqual(names, set(api_server.SPEC_RESOURCES))
        self.assertEqual(index["source_revision"], api_server.SOURCE_REVISION)
        self.assertTrue(all(len(resource["sha256"]) == 64 for resource in index["resources"]))
        indexed = {resource["name"]: resource for resource in index["resources"]}

        for name in names:
            served = await api_server.spec_resource(name)
            self.assertEqual(
                hashlib.sha256(served.body).hexdigest(),
                indexed[name]["sha256"],
            )
            self.assertEqual(served.headers["x-source-revision"], api_server.SOURCE_REVISION)

        ls_spec = await api_server.spec_resource("ls-spec")
        self.assertIn(b"Lunascripts", ls_spec.body)
        self.assertEqual(ls_spec.headers["x-source-revision"], api_server.SOURCE_REVISION)
        self.assertTrue(ls_spec.headers["etag"].startswith('"sha256:'))

        json_output = await api_server.spec_resource("json-output")
        self.assertIn(b"LS JSON", json_output.body)

        with self.assertRaises(HTTPException) as missing:
            await api_server.spec_resource("not-allowlisted")
        self.assertEqual(missing.exception.status_code, 404)

        with self.assertRaises(HTTPException) as stale:
            await api_server.spec_resource("ls-spec", revision="stale-revision")
        self.assertEqual(stale.exception.status_code, 409)


class ApiServerBoundaryTests(unittest.TestCase):
    def test_request_body_middleware_rejects_declared_and_streamed_overflow(self):
        async def downstream(scope, receive, send):
            while True:
                message = await receive()
                if not message.get("more_body"):
                    break
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        async def run_case(headers, messages):
            sent = []
            remaining = iter(messages)

            async def receive():
                return next(remaining)

            async def send(message):
                sent.append(message)

            middleware = api_server.RequestBodyLimitMiddleware(downstream, max_bytes=4)
            await middleware(
                {"type": "http", "method": "POST", "headers": headers},
                receive,
                send,
            )
            return sent

        declared = asyncio.run(
            run_case(
                [(b"content-length", b"5")],
                [{"type": "http.request", "body": b"", "more_body": False}],
            )
        )
        self.assertEqual(declared[0]["status"], 413)

        streamed = asyncio.run(
            run_case(
                [],
                [
                    {"type": "http.request", "body": b"123", "more_body": True},
                    {"type": "http.request", "body": b"45", "more_body": False},
                ],
            )
        )
        self.assertEqual(streamed[0]["status"], 413)

    def test_compiler_queue_rejects_overload_without_starting_a_process(self):
        async def run():
            with patch.object(api_server, "_LS_SEMAPHORE", asyncio.Semaphore(0)), patch.object(
                api_server, "LS_QUEUE_TIMEOUT_SECONDS", 0.001
            ):
                await api_server._run_ls_async("compile", "never-started.ls")

        with self.assertRaises(HTTPException) as raised:
            asyncio.run(run())
        self.assertEqual(raised.exception.status_code, 503)

    def test_upload_reader_rejects_data_over_the_explicit_limit(self):
        upload = UploadFile(file=io.BytesIO(b"12345"), filename="large.ls")
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(api_server._read_upload_limited(upload, 4, "script"))
        self.assertEqual(raised.exception.status_code, 413)

    def test_zip_validator_rejects_unsafe_paths(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("../escape.ls", CANONICAL_SOURCE)
        archive.seek(0)

        with zipfile.ZipFile(archive) as uploaded:
            with self.assertRaises(HTTPException) as raised:
                api_server._validate_zip_archive(uploaded)
        self.assertEqual(raised.exception.status_code, 422)

    def test_zip_validator_caps_member_count_and_expanded_bytes(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("episode.ls", CANONICAL_SOURCE)
        archive.seek(0)

        with zipfile.ZipFile(archive) as uploaded, patch.object(api_server, "MAX_ZIP_MEMBERS", 0):
            with self.assertRaises(HTTPException) as members_error:
                api_server._validate_zip_archive(uploaded)
        self.assertEqual(members_error.exception.status_code, 413)

        archive.seek(0)
        with zipfile.ZipFile(archive) as uploaded, patch.object(
            api_server, "MAX_ZIP_UNCOMPRESSED_BYTES", 1
        ):
            with self.assertRaises(HTTPException) as size_error:
                api_server._validate_zip_archive(uploaded)
        self.assertEqual(size_error.exception.status_code, 413)

    def test_workflow_authority_maps_cover_the_api_allowlist(self):
        pattern = re.compile(r'^\s+"([a-z0-9-]+)": Path\(', re.MULTILINE)
        for workflow in (
            Path(".github/workflows/deploy-railway.yml"),
            Path(".github/workflows/compiler-remote-parity.yml"),
        ):
            names = set(pattern.findall(workflow.read_text(encoding="utf-8")))
            self.assertEqual(names, set(api_server.SPEC_RESOURCES), workflow)


if __name__ == "__main__":
    unittest.main()
