"""Content-addressed custody for trajectories and artifacts.

Receipts are the hot path for every projection, so they carry digests and not
payloads. That only means something if the digest can be resolved back to bytes
and those bytes re-hash to it -- otherwise custody is a claim about a file that
may since have changed, or never existed.

Deliberately a directory of files named by their own digest. No index, no
database, no compaction. A store whose integrity depends on its own bookkeeping
is a store that can lose the argument; here, the filename *is* the checksum, so
a later reader can verify the whole store with ``sha256sum``.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import re
import shutil

__all__ = ["BlobError", "BlobStore"]

_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class BlobError(ValueError):
    """A custody operation that cannot be trusted."""


class BlobStore:
    """Write-once storage addressed by SHA-256 of the content."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, digest: str) -> Path:
        # Two-level fan-out: a flat directory of tens of thousands of entries is
        # slow to list on every filesystem that matters.
        return self.root / digest[:2] / digest[2:4] / digest

    def put_bytes(self, data: bytes) -> str:
        """Store bytes, return the digest. Re-storing identical bytes is a no-op."""
        digest = hashlib.sha256(data).hexdigest()
        target = self._path(digest)
        if target.exists():
            return digest
        target.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temporary name and rename, so a killed process cannot leave
        # a truncated file sitting under a digest that promises the whole thing.
        staging = target.with_suffix(".partial")
        staging.write_bytes(data)
        staging.replace(target)
        return digest

    def put_file(self, path: str | Path) -> str:
        source = Path(path)
        if not source.is_file():
            raise BlobError(f"{path} is not a file")
        return self.put_bytes(source.read_bytes())

    def put_tree(self, path: str | Path) -> str:
        """Store a directory as one blob, via a deterministic archive.

        Trial trajectories arrive as directories. ``tar`` with sorted member
        names and no timestamps would be ideal; ``shutil.make_archive`` is not
        deterministic, so this builds the archive itself.

        **The archive format is part of every digest that addresses a tree.**
        Changing it -- adding compression, changing the member ordering, letting
        a timestamp back in -- changes the digest of unchanged content, and
        every receipt already citing that content becomes unverifiable. It is
        free to change today because no real trial exists; it is not free
        afterwards. Uncompressed tar is chosen for exactly that reason: it is
        the format most likely to still be readable and reproducible in a
        decade, and the padding it costs (10 KB per archive, minimum) is
        irrelevant beside a receipt log that must outlive the tooling.
        """
        source = Path(path)
        if not source.is_dir():
            raise BlobError(f"{path} is not a directory")
        import io
        import tarfile

        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as archive:
            for member in sorted(source.rglob("*")):
                if not member.is_file():
                    continue
                info = tarfile.TarInfo(str(member.relative_to(source)))
                data = member.read_bytes()
                info.size = len(data)
                # Zeroed so the same tree hashes the same on two machines.
                info.mtime = 0
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(data))
        return self.put_bytes(buffer.getvalue())

    def get(self, digest: str) -> bytes:
        if not _DIGEST.match(digest or ""):
            raise BlobError(f"not a content address: {digest!r}")
        target = self._path(digest)
        if not target.exists():
            raise BlobError(f"no blob for {digest}")
        data = target.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != digest:
            raise BlobError(
                f"blob {digest} hashes to {actual}; the store has been corrupted "
                "or edited, and every receipt citing it is now unverifiable"
            )
        return data

    def has(self, digest: str) -> bool:
        return bool(_DIGEST.match(digest or "")) and self._path(digest).exists()

    def verify_all(self) -> list[str]:
        """Every stored blob whose bytes no longer match its name."""
        broken = []
        for path in self.root.rglob("*"):
            if not path.is_file() or not _DIGEST.match(path.name):
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != path.name:
                broken.append(path.name)
        return sorted(broken)

    def size_bytes(self) -> int:
        return sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())

    def drop(self) -> None:
        """Delete the whole store. Only ever for a rehearsal or a test."""
        if self.root.exists():
            shutil.rmtree(self.root)
