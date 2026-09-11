import asyncio
import hashlib
import os
import json
import re
import shutil
import tempfile
import subprocess
import zipfile
from pathlib import Path, PurePosixPath
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, Response

APP_DIR = Path(__file__).resolve().parent
LS_BIN = APP_DIR / "bin" / "lsc"
CONTRACT_MANIFEST = APP_DIR / "contract" / "contract.json"
BUILD_INFO = APP_DIR / "build-info.json"
API_VERSION = "1.4.0"
REQUIRE_SOURCE_REVISION = os.environ.get("REQUIRE_SOURCE_REVISION", "0") == "1"

SPEC_RESOURCES = {
    "ls-spec": {
        "path": APP_DIR / "LS-SPEC.md",
        "media_type": "text/markdown",
        "description": "Canonical Luna Script grammar and language semantics.",
    },
    "json-output": {
        "path": APP_DIR / "docs" / "JSON-OUTPUT.md",
        "media_type": "text/markdown",
        "description": "Canonical compiler JSON output field reference.",
    },
}

MAX_SCRIPT_BYTES = 1 * 1024 * 1024
MAX_ASSETS_BYTES = 2 * 1024 * 1024
MAX_ZIP_BYTES = 10 * 1024 * 1024
MAX_ZIP_MEMBERS = 100
MAX_ZIP_UNCOMPRESSED_BYTES = 25 * 1024 * 1024
MAX_REQUEST_BODY_BYTES = 13 * 1024 * 1024
LS_MAX_CONCURRENCY = max(1, int(os.environ.get("LS_MAX_CONCURRENCY", "2")))
LS_QUEUE_TIMEOUT_SECONDS = 1.0
_LS_SEMAPHORE = asyncio.Semaphore(LS_MAX_CONCURRENCY)
_READINESS_SEMAPHORE = asyncio.Semaphore(1)


def _source_revision() -> str:
    try:
        value = json.loads(BUILD_INFO.read_text(encoding="utf-8")).get("source_revision")
        return value.strip() if isinstance(value, str) and value.strip() else "unknown"
    except (OSError, json.JSONDecodeError):
        return "unknown"


SOURCE_REVISION = _source_revision()


class RequestBodyTooLarge(Exception):
    pass


class RequestBodyLimitMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    if int(value) > self.max_bytes:
                        response = JSONResponse(status_code=413, content={"detail": "request body too large"})
                        await response(scope, receive, send)
                        return
                except ValueError:
                    pass

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            response = JSONResponse(status_code=413, content={"detail": "request body too large"})
            await response(scope, receive, send)

app = FastAPI(
    title="Lunascripts API",
    description="Compile, decompile, validate, and fix Lunascripts (LS) files via HTTP.",
    version=API_VERSION,
)
app.add_middleware(RequestBodyLimitMiddleware, max_bytes=MAX_REQUEST_BODY_BYTES)


def _run_ls(*args: str, workdir: Optional[str] = None, timeout: int = 30) -> subprocess.CompletedProcess:
    cmd = [str(LS_BIN), *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=workdir,
        timeout=timeout,
    )


async def _run_ls_async(
    *args: str, workdir: Optional[str] = None, timeout: int = 30
) -> subprocess.CompletedProcess:
    try:
        await asyncio.wait_for(_LS_SEMAPHORE.acquire(), timeout=LS_QUEUE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="compiler is busy")
    try:
        return await asyncio.to_thread(_run_ls, *args, workdir=workdir, timeout=timeout)
    finally:
        _LS_SEMAPHORE.release()


async def _run_readiness_probe_async(*args: str, timeout: int) -> subprocess.CompletedProcess:
    try:
        await asyncio.wait_for(_READINESS_SEMAPHORE.acquire(), timeout=LS_QUEUE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="readiness probe is busy")
    try:
        return await asyncio.to_thread(_run_ls, *args, timeout=timeout)
    finally:
        _READINESS_SEMAPHORE.release()


def _contract_version() -> str:
    try:
        manifest = json.loads(CONTRACT_MANIFEST.read_text(encoding="utf-8"))
        version = manifest.get("contract_version")
        return version if isinstance(version, str) and version else "unknown"
    except (OSError, json.JSONDecodeError):
        return "unknown"


def _version_payload() -> dict[str, str]:
    return {
        "service": "Lunascripts API",
        "api_version": API_VERSION,
        "ls_contract_version": _contract_version(),
        "source_revision": SOURCE_REVISION,
    }


def _spec_metadata(name: str, resource: dict[str, object], data: bytes) -> dict[str, object]:
    return {
        "name": name,
        "url": f"/spec/{name}?revision={SOURCE_REVISION}",
        "media_type": resource["media_type"],
        "description": resource["description"],
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def _spec_headers(data: bytes) -> dict[str, str]:
    digest = hashlib.sha256(data).hexdigest()
    return {
        "ETag": f'"sha256:{digest}"',
        "Cache-Control": "public, max-age=300",
        "X-LS-Contract-Version": _contract_version(),
        "X-Source-Revision": SOURCE_REVISION,
    }


def _missing_or_invalid_spec_resources() -> list[str]:
    invalid = []
    for name, resource in SPEC_RESOURCES.items():
        try:
            data = resource["path"].read_bytes()
            if resource["media_type"] == "application/json":
                json.loads(data)
        except (OSError, json.JSONDecodeError):
            invalid.append(name)
    return invalid


async def _read_upload_limited(upload: UploadFile, limit: int, label: str) -> bytes:
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail=f"{label} exceeds {limit} bytes")
    return data


def _validate_zip_archive(zf: zipfile.ZipFile) -> None:
    members = zf.infolist()
    if len(members) > MAX_ZIP_MEMBERS:
        raise HTTPException(
            status_code=413,
            detail=f"zip archive exceeds {MAX_ZIP_MEMBERS} members",
        )

    total_size = 0
    for member in members:
        path = PurePosixPath(member.filename)
        if path.is_absolute() or ".." in path.parts:
            raise HTTPException(status_code=422, detail="zip archive contains an unsafe path")
        if member.flag_bits & 0x1:
            raise HTTPException(status_code=422, detail="encrypted zip archives are not supported")
        total_size += member.file_size
        if total_size > MAX_ZIP_UNCOMPRESSED_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"zip archive expands beyond {MAX_ZIP_UNCOMPRESSED_BYTES} bytes",
            )


# ── /compile (single file) ──────────────────────────────────────────────

@app.post("/compile")
async def compile_script(
    script: UploadFile = File(..., description="LS script file (.ls or .ls.md)"),
    assets: Optional[UploadFile] = File(default=None, description="Optional assets mapping JSON file"),
):
    """
    Compile a single LS script (.ls or .ls.md) into structured JSON.

    Returns the compiled episode JSON. If an assets mapping is provided,
    asset semantic names are resolved to full URLs.
    """
    tmpdir = tempfile.mkdtemp(prefix="ls_compile_")
    try:
        script_bytes = await _read_upload_limited(script, MAX_SCRIPT_BYTES, "script")
        script_text = script_bytes.decode("utf-8")
        script_path = os.path.join(tmpdir, "script.ls.md")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_text)

        args = ["compile", script_path, "-o", os.path.join(tmpdir, "output.json")]

        if assets is not None:
            assets_bytes = await _read_upload_limited(assets, MAX_ASSETS_BYTES, "assets")
            assets_text = assets_bytes.decode("utf-8")
            assets_path = os.path.join(tmpdir, "assets.json")
            with open(assets_path, "w", encoding="utf-8") as f:
                f.write(assets_text)
            args.insert(2, "--assets")
            args.insert(3, assets_path)

        proc = await _run_ls_async(*args, timeout=30)

        if proc.returncode != 0:
            raise HTTPException(status_code=422, detail={"error": proc.stderr.strip()})

        output_path = os.path.join(tmpdir, "output.json")
        with open(output_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        return JSONResponse(content=result)

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Compilation timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── /compile-dir (directory via zip) ────────────────────────────────────

@app.post("/compile-dir")
async def compile_directory(
    zipfile_upload: UploadFile = File(..., alias="zipfile", description="Zip archive of an LS episode directory"),
    assets: Optional[UploadFile] = File(default=None, description="Optional assets mapping JSON file"),
):
    """
    Compile an entire episode directory (uploaded as a zip) into structured JSON.

    The zip should contain one or more `.ls` / `.ls.md` files (e.g. 01.ls.md, 02.ls.md, …).
    Directory structure inside the zip is flattened — all `.ls` / `.ls.md` / `.episode.ls` / `.episode.ls.md` files are
    discovered recursively and compiled together.

    Returns the compiled novel JSON (keyed by episode_id).
    """
    tmpdir = tempfile.mkdtemp(prefix="ls_compiledir_")
    try:
        zip_bytes = await _read_upload_limited(zipfile_upload, MAX_ZIP_BYTES, "zip archive")
        zip_path = os.path.join(tmpdir, "input.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_bytes)

        episode_dir = os.path.join(tmpdir, "episodes")
        os.makedirs(episode_dir)
        with zipfile.ZipFile(zip_path, "r") as zf:
            _validate_zip_archive(zf)
            zf.extractall(episode_dir)

        args = ["compile", episode_dir, "-o", os.path.join(tmpdir, "output.json")]

        if assets is not None:
            assets_bytes = await _read_upload_limited(assets, MAX_ASSETS_BYTES, "assets")
            assets_text = assets_bytes.decode("utf-8")
            assets_path = os.path.join(tmpdir, "assets.json")
            with open(assets_path, "w", encoding="utf-8") as f:
                f.write(assets_text)
            args.insert(2, "--assets")
            args.insert(3, assets_path)

        proc = await _run_ls_async(*args, timeout=60)

        if proc.returncode != 0:
            raise HTTPException(status_code=422, detail={"error": proc.stderr.strip()})

        output_path = os.path.join(tmpdir, "output.json")
        with open(output_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        return JSONResponse(content=result)

    except zipfile.BadZipFile:
        raise HTTPException(status_code=422, detail="invalid zip archive")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Directory compilation timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── /decompile ──────────────────────────────────────────────────────────

@app.post("/decompile")
async def decompile_json(
    compiled: UploadFile = File(..., description="Compiled LS JSON file"),
):
    """
    Decompile compiled LS JSON back into LS script and asset mapping.

    Returns the reconstructed LS source (.ls.md) and the recovered asset mapping.
    """
    tmpdir = tempfile.mkdtemp(prefix="ls_decompile_")
    try:
        compiled_bytes = await _read_upload_limited(compiled, MAX_SCRIPT_BYTES, "compiled JSON")
        compiled_text = compiled_bytes.decode("utf-8")
        input_path = os.path.join(tmpdir, "input.json")
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(compiled_text)

        output_dir = os.path.join(tmpdir, "decompiled")

        proc = await _run_ls_async("decompile", input_path, "-o", output_dir, timeout=30)

        warnings = []
        if proc.stderr.strip():
            for line in proc.stderr.strip().split("\n"):
                line = line.strip()
                if line.startswith("warning:"):
                    warnings.append(line.removeprefix("warning:").strip())
                elif line.startswith("wrote"):
                    pass
                elif line:
                    warnings.append(line)

        if not os.path.isdir(output_dir):
            raise HTTPException(
                status_code=422,
                detail={"error": proc.stderr.strip() or "Decompilation produced no output"},
            )

        ls_files = {}
        mapping = None
        for fname in os.listdir(output_dir):
            fpath = os.path.join(output_dir, fname)
            if (
                fname.endswith(".ls")
                or fname.endswith(".ls.md")
                or fname.endswith(".episode.ls")
                or fname.endswith(".episode.ls.md")
            ):
                with open(fpath, "r", encoding="utf-8") as f:
                    ls_files[fname] = f.read()
            elif fname.endswith(".json"):
                with open(fpath, "r", encoding="utf-8") as f:
                    mapping = json.load(f)

        return JSONResponse(
            content={
                "episodes": ls_files,
                "asset_mapping": mapping,
                "warnings": warnings,
            }
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Decompilation timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── /validate ───────────────────────────────────────────────────────────

@app.post("/validate")
async def validate_script(
    script: UploadFile = File(..., description="LS script file (.ls or .ls.md) to validate"),
    assets: Optional[UploadFile] = File(default=None, description="Optional assets mapping JSON file"),
):
    """
    Validate an LS script for syntax errors without compiling.

    Returns a validation report: valid (true/false) and any error messages.
    """
    tmpdir = tempfile.mkdtemp(prefix="ls_validate_")
    try:
        script_bytes = await _read_upload_limited(script, MAX_SCRIPT_BYTES, "script")
        script_text = script_bytes.decode("utf-8")
        script_path = os.path.join(tmpdir, "script.ls.md")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_text)

        args = ["validate", script_path]

        if assets is not None:
            assets_bytes = await _read_upload_limited(assets, MAX_ASSETS_BYTES, "assets")
            assets_text = assets_bytes.decode("utf-8")
            assets_path = os.path.join(tmpdir, "assets.json")
            with open(assets_path, "w", encoding="utf-8") as f:
                f.write(assets_text)
            args.append("--assets")
            args.append(assets_path)

        proc = await _run_ls_async(*args, timeout=30)

        return JSONResponse(
            content={
                "valid": proc.returncode == 0,
                "errors": proc.stderr.strip() if proc.returncode != 0 else None,
                "stdout": proc.stdout.strip() or None,
            }
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Validation timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── /fix ────────────────────────────────────────────────────────────────

@app.post("/fix")
async def fix_script(
    script: UploadFile = File(..., description="LS script file (.ls or .ls.md) to fix"),
    check: bool = Query(default=False, description="Dry-run: report issues without writing changes"),
):
    """
    Auto-fix common issues in an LS script.

    In fix mode (default): returns the fixed script text and a list of
    fixes applied.

    In check mode (?check=true): returns a list of issues found without
    modifying the script (like `lsc fix --check`).
    """
    tmpdir = tempfile.mkdtemp(prefix="ls_fix_")
    try:
        script_bytes = await _read_upload_limited(script, MAX_SCRIPT_BYTES, "script")
        script_text = script_bytes.decode("utf-8")
        script_path = os.path.join(tmpdir, "script.ls.md")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_text)

        if check:
            proc = await _run_ls_async("fix", script_path, "--check", timeout=30)
            return JSONResponse(
                content={
                    "check": True,
                    "issues_found": proc.returncode != 0,
                    "report": proc.stderr.strip() or proc.stdout.strip() or None,
                }
            )
        else:
            output_path = os.path.join(tmpdir, "fixed.ls.md")
            proc = await _run_ls_async("fix", script_path, "-o", output_path, timeout=30)

            if proc.returncode != 0 and not os.path.exists(output_path):
                raise HTTPException(status_code=422, detail={"error": proc.stderr.strip()})

            if os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8") as f:
                    fixed_text = f.read()
            else:
                fixed_text = script_text  # unchanged

            return JSONResponse(
                content={
                    "check": False,
                    "fixed": fixed_text,
                    "changed": fixed_text != script_text,
                    "stderr": proc.stderr.strip() or None,
                }
            )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Fix timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── / ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Root redirect to docs."""
    return JSONResponse(
        content={
            "service": "Lunascripts API",
            "version": API_VERSION,
            "ls_contract_version": _contract_version(),
            "source_revision": SOURCE_REVISION,
            "endpoints": {
                "health": "GET /health",
                "ready": "GET /ready",
                "version": "GET /version",
                "spec": "GET /spec",
                "compile": "POST /compile",
                "compile-dir": "POST /compile-dir",
                "decompile": "POST /decompile",
                "validate": "POST /validate",
                "fix": "POST /fix",
            },
            "docs": "/docs",
        }
    )


# ── /health ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint."""
    if not LS_BIN.exists():
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "reason": "lsc binary not found"},
        )
    return {"status": "ok", **_version_payload()}


@app.get("/version")
async def version():
    """Return the deployed API, contract, and source revision."""
    return _version_payload()


@app.get("/spec")
async def spec_index():
    """Return a discoverable, revision-bound index of agent-readable authority."""
    resources = []
    missing = []
    for name, resource in SPEC_RESOURCES.items():
        path = resource["path"]
        try:
            data = path.read_bytes()
        except OSError:
            missing.append(name)
            continue
        resources.append(_spec_metadata(name, resource, data))

    if missing:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "missing_resources": missing, **_version_payload()},
        )

    return {
        "authority": "Canonical Lunaverse Luna Script rules mirrored from repository main.",
        "sync_invariant": "source_revision must equal the canonical repository main HEAD.",
        **_version_payload(),
        "resources": resources,
    }


@app.get("/spec/{resource_name}")
async def spec_resource(resource_name: str, revision: Optional[str] = None):
    """Return one allowlisted authority resource with revision and digest headers."""
    if revision is not None and revision != SOURCE_REVISION:
        raise HTTPException(status_code=409, detail="requested source revision is not deployed")

    resource = SPEC_RESOURCES.get(resource_name)
    if resource is None:
        raise HTTPException(status_code=404, detail="unknown spec resource")

    path = resource["path"]
    try:
        data = path.read_bytes()
    except OSError:
        raise HTTPException(status_code=503, detail="spec resource unavailable")

    headers = _spec_headers(data)
    if resource["media_type"] == "application/json":
        try:
            json.loads(data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=503, detail="spec resource is invalid JSON")
        return Response(content=data, media_type="application/json", headers=headers)

    return PlainTextResponse(
        content=data.decode("utf-8"),
        media_type=str(resource["media_type"]),
        headers=headers,
    )


@app.get("/ready")
async def ready():
    """Compile a canonical probe so readiness proves LS contract semantics."""
    if REQUIRE_SOURCE_REVISION and not re.fullmatch(r"[0-9a-f]{40}", SOURCE_REVISION):
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "source revision unavailable"},
        )

    expected_contract = _contract_version()
    if expected_contract == "unknown":
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "contract manifest unavailable"},
        )

    invalid_resources = _missing_or_invalid_spec_resources()
    if invalid_resources:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "reason": "spec authority resources unavailable",
                "resources": invalid_resources,
            },
        )

    with tempfile.TemporaryDirectory(prefix="ls_ready_") as tmpdir:
        script_path = Path(tmpdir) / "ready.ls"
        script_path.write_text(
            '@episode main:01 "Readiness" {\n'
            "  @bg readiness_background fade\n"
            "  INNER_THOUGHT: Compiler readiness probe.\n"
            "  @gate {\n"
            "    @next main:02\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        try:
            proc = await _run_readiness_probe_async("compile", str(script_path), timeout=5)
            result = json.loads(proc.stdout) if proc.returncode == 0 else None
        except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": f"compiler probe failed: {exc}"},
            )

    steps = result.get("steps") if isinstance(result, dict) else None
    first_step = steps[0] if isinstance(steps, list) and steps else {}
    thought_step = steps[1] if isinstance(steps, list) and len(steps) > 1 else {}
    if (
        not isinstance(result, dict)
        or result.get("ls_contract_version") != expected_contract
        or first_step.get("name") != "readiness_background"
        or first_step.get("transition") != "fade"
        or thought_step.get("type") != "inner_thought"
        or thought_step.get("id") != "0002_you"
    ):
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "compiler contract probe mismatch"},
        )

    return {"status": "ready", **_version_payload()}
