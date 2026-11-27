"""Test setup: cloud emulators by default, live cloud via PANPATH_LIVE=1.

By default the cloud test modules run against local emulators:

- S3    -> moto server (``moto[server]``)
- GCS   -> gcp-storage-emulator (``STORAGE_EMULATOR_HOST``)
- Azure -> Azurite (``npx azurite``)

Set ``PANPATH_LIVE=1`` to run against the real services instead, using the
credentials from ``.env`` / the environment.
"""

import fcntl
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import warnings

import pytest
from dotenv import load_dotenv

load_dotenv()

LIVE = os.environ.get("PANPATH_LIVE") == "1"

S3_BUCKET = "panpath-test2"
GCS_BUCKET = "panpath-test"
AZURE_CONTAINER = "panpath-test"
SEED_BLOB = "readonly.txt"
SEED_CONTENT = b"123"

AZURITE_KEY = (
    "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/"
    "K1SZFPTOtr/KBHBeksoGMGw=="
)

# backend -> reason it could not be started (empty when healthy)
_emulator_errors: dict[str, str] = {}
_emulator_stoppers = []


def _free_port() -> int:
    """Ask the OS for a free port."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _worker_index() -> int:
    """Index of this xdist worker (0 when not running under xdist)."""
    return int(os.environ.get("PYTEST_XDIST_WORKER", "gw0")[2:] or 0)


def _ports(count: int, base: int) -> list:
    """``count`` distinct ports starting at ``base``.

    ``_free_port`` hands the same port to two xdist workers that ask at
    slightly different times; the slower emulator then fails to bind and its
    client talks to the other worker's server. Ports derived from the worker
    index cannot collide with a sibling worker's.
    """
    ports: list[int] = []
    for offset in range(count):
        port = base + offset
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                port = _free_port()
        while port in ports:
            port = _free_port()
        ports.append(port)
    return ports


def _start_verified(start, verify, attempts: int = 3):
    """Run ``start``/``verify`` pairs until the server is provably ours.

    Two xdist workers can be handed the same ephemeral port, in which case one
    worker's client ends up talking to the other worker's emulator. ``verify``
    round-trips a unique marker through the server we started; a mismatch means
    the port was taken by someone else, so retry on a new one.
    """
    last_error: Exception | None = None
    for _ in range(attempts):
        stopper = None
        try:
            stopper = start()
            verify()
            return stopper
        except Exception as exc:  # noqa: BLE001 - retried below
            last_error = exc
            if stopper is not None:
                stopper()
    raise RuntimeError(f"emulator did not come up as ours: {last_error}")


def _wait_for_http(url: str, tries: int = 300) -> None:
    import urllib.error
    import urllib.request

    for _ in range(tries):
        try:
            urllib.request.urlopen(url, timeout=0.3)
            return
        except urllib.error.HTTPError:
            return  # listening; 4xx is fine
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"emulator never came up: {url}")


_COMPUTED_FIELDS = ("crc32c", "md5Hash", "etag", "size", "generation", "metageneration")


def _patch_gcs_compose() -> None:
    """Make the GCS emulator accept the compose requests real GCS accepts.

    Two gaps: gcloud-aio omits ``destination`` when no content type is given
    (the emulator indexes it blindly), and clients echo the destination's
    previous checksum/size properties, which real GCS recomputes but the
    emulator validates against the new content and rejects.
    """
    import gcp_storage_emulator.handlers.objects as objects
    import gcp_storage_emulator.server as server

    original_compose = objects.compose

    def compose(request, response, storage, *args, **kwargs):
        data = request.data
        if isinstance(data, dict):
            destination = {
                k: v for k, v in data.get("destination", {}).items()
                if k not in _COMPUTED_FIELDS
            }
            request._data = {**data, "destination": destination}
        return original_compose(request, response, storage, *args, **kwargs)

    # A ``dir/`` marker uploaded with an empty body arrives as ``None``.
    original_media = objects._media_upload

    def media_upload(request, response, storage):
        if request.data is None:
            request._data = b""
        return original_media(request, response, storage)

    objects.compose = compose
    objects._media_upload = media_upload

    # The routing table captured the original functions; re-point it.
    replacements = {original_compose: compose, original_media: media_upload}
    server.HANDLERS = tuple(
        (
            regex,
            {method: replacements.get(handler, handler) for method, handler in handlers.items()},
        )
        for regex, handlers in server.HANDLERS
    )


def _start_s3() -> None:
    import boto3
    from moto.server import ThreadedMotoServer

    marker_bucket = f"panpath-marker-{os.getpid()}"

    def start():
        server = ThreadedMotoServer(port=0)
        server.start()
        host, port = server.get_host_and_port()
        os.environ.update(
            AWS_ACCESS_KEY_ID="test",
            AWS_SECRET_ACCESS_KEY="test",
            AWS_DEFAULT_REGION="us-east-1",
            AWS_ENDPOINT_URL=f"http://{host}:{port}",
        )
        return server.stop

    def verify():
        client = boto3.client("s3")
        client.create_bucket(Bucket=marker_bucket)
        # A fresh server has no other buckets; if one is present we landed on
        # another worker's emulator, which would also be killed by our stop().
        names = [b["Name"] for b in client.list_buckets()["Buckets"]]
        assert names == [marker_bucket], names
        client.create_bucket(Bucket=S3_BUCKET)
        client.put_object(Bucket=S3_BUCKET, Key=SEED_BLOB, Body=SEED_CONTENT)

    _emulator_stoppers.append(_start_verified(start, verify))


def _patch_gcs_trailing_slash() -> None:
    """Serve ``/b/<bucket>/`` where the emulator only routes ``/b/<bucket>``.

    gcloud-aio requests bucket resources with a trailing slash.
    """
    import gcp_storage_emulator.server as server

    original = server._json_api_routes

    def routes(prefix: str):
        extended = []
        for regex, handlers in original(prefix):
            extended.append((regex, handlers))
            if regex.endswith(r"[-.\w]+)$"):
                extended.append((regex[:-1] + "/$", handlers))
        return tuple(extended)

    server.HANDLERS = (
        *routes(server.settings.API_ENDPOINT),
        *routes(""),
        *server.HANDLERS[2 * len(original(server.settings.API_ENDPOINT)):],
    )


def _start_gcs() -> None:
    if sys.version_info < (3, 10):
        # Older emulator releases cannot store ``dir/`` marker objects.
        raise RuntimeError("gcp-storage-emulator requires Python >= 3.10")
    warnings.filterwarnings("ignore", message=".*pkg_resources.*")
    _patch_gcs_compose()
    _patch_gcs_trailing_slash()
    from gcp_storage_emulator.server import create_server

    def start():
        [port] = _ports(1, 22500 + _worker_index())
        server = create_server(
            "127.0.0.1", port, in_memory=True, default_bucket=GCS_BUCKET
        )
        threading.Thread(target=server.start, daemon=True).start()
        url = f"http://127.0.0.1:{port}"
        os.environ["STORAGE_EMULATOR_HOST"] = url
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        _wait_for_http(url)
        return server.stop

    def verify():
        from google.cloud import storage

        marker = f"panpath-marker-{os.getpid()}"
        bucket = storage.Client().bucket(GCS_BUCKET)
        bucket.blob(marker).upload_from_string(SEED_CONTENT)
        # A fresh emulator holds only this worker's marker; anything else means
        # we are talking to a sibling worker's server, which will be shut down
        # (and its port eventually recycled) while we still use it.
        names = [blob.name for blob in bucket.list_blobs()]
        assert names == [marker], names
        bucket.blob(SEED_BLOB).upload_from_string(SEED_CONTENT)

    _emulator_stoppers.append(_start_verified(start, verify))


def _azurite_command() -> list:
    """Return the command that runs Azurite, installing it once if needed.

    ``npx --yes`` downloads on first use, and several xdist workers doing that
    at once races, so install into a shared prefix under a lock.
    """
    installed = shutil.which("azurite")
    if installed:
        return [installed]
    prefix = os.path.join(tempfile.gettempdir(), "panpath-azurite")
    binary = os.path.join(prefix, "node_modules", ".bin", "azurite")
    lock_path = prefix + ".lock"
    with open(lock_path, "a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            if not os.path.exists(binary):
                subprocess.run(
                    ["npm", "install", "--silent", "--prefix", prefix, "azurite"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
    return [binary]


def _spawn_azurite():
    """Start Azurite on a free port; returns (stop, port)."""
    command = _azurite_command()
    blob_port, queue_port, table_port = _ports(3, 11000 + _worker_index() * 10)
    proc = subprocess.Popen(
        [
            *command,
            "--blobHost", "127.0.0.1", "--blobPort", str(blob_port),
            "--queueHost", "127.0.0.1", "--queuePort", str(queue_port),
            "--tableHost", "127.0.0.1", "--tablePort", str(table_port),
            "--inMemoryPersistence",
            # Each xdist worker runs its own server; without a cap every
            # one reserves 50% of RAM and they starve each other.
            "--extentMemoryLimit", "64",
            "--skipApiVersionCheck", "--silent",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        # Own process group so stop() can kill the node child npx spawns.
        start_new_session=True,
    )
    try:
        _wait_for_http(f"http://127.0.0.1:{blob_port}/devstoreaccount1", tries=150)
    except Exception:
        # Nothing owns this process yet; start() would raise without a stopper.
        _terminate(proc)
        raise
    return (lambda: _terminate(proc)), blob_port


def _terminate(proc) -> None:
    """Terminate a process and any children it spawned."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:  # pragma: no cover
        os.killpg(proc.pid, signal.SIGKILL)


def _start_azure() -> None:
    def start():
        stop, port = _spawn_azurite()
        conn = (
            "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
            f"AccountKey={AZURITE_KEY};"
            f"BlobEndpoint=http://127.0.0.1:{port}/devstoreaccount1;"
        )
        os.environ["AZURE_STORAGE_CONNECTION_STRING"] = conn
        return stop

    def verify():
        from azure.storage.blob import BlobServiceClient

        marker = f"panpath-marker-{os.getpid()}"
        service = BlobServiceClient.from_connection_string(
            os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        )
        service.create_container(AZURE_CONTAINER)
        service.get_blob_client(AZURE_CONTAINER, marker).upload_blob(
            SEED_CONTENT, overwrite=True
        )
        # See _start_gcs: only this worker's marker proves the server is ours.
        names = [
            blob.name
            for blob in service.get_container_client(AZURE_CONTAINER).list_blobs()
        ]
        assert names == [marker], names
        service.get_blob_client(AZURE_CONTAINER, SEED_BLOB).upload_blob(
            SEED_CONTENT, overwrite=True
        )
        service.get_blob_client(AZURE_CONTAINER, marker).delete_blob()
        service.get_blob_client(AZURE_CONTAINER, SEED_BLOB).upload_blob(
            SEED_CONTENT, overwrite=True
        )

    _emulator_stoppers.append(_start_verified(start, verify))


_STARTERS = {"s3": _start_s3, "gs": _start_gcs, "azure": _start_azure}


def pytest_configure(config):
    """Start emulators before collection so failures turn into skips."""
    if LIVE:
        return
    for backend, start in _STARTERS.items():
        try:
            start()
        except Exception as exc:  # noqa: BLE001 - an unavailable emulator is a skip
            _emulator_errors[backend] = f"{type(exc).__name__}: {exc}"


def pytest_unconfigure(config):
    while _emulator_stoppers:
        _emulator_stoppers.pop()()


def emulator_error(backend: str):
    """Return why an emulator is unavailable (None when it started fine)."""
    if LIVE:
        return None
    return _emulator_errors.get(backend)


def _module_backend(module_name: str):
    if "s3" in module_name:
        return "s3"
    if "_gs" in module_name or "gcs" in module_name:
        return "gs"
    if "azure" in module_name:
        return "azure"
    return None


def pytest_collection_modifyitems(config, items):
    """Skip cloud test modules whose emulator is unavailable."""
    if LIVE:
        return
    for item in items:
        backend = _module_backend(item.module.__name__)
        if backend in _emulator_errors:
            item.add_marker(
                pytest.mark.skip(
                    reason=f"{backend} emulator unavailable: {_emulator_errors[backend]}"
                )
            )
