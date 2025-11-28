import asyncio
from asyncio import AbstractEventLoop
from functools import partial
import io
import os
import fnmatch
from datetime import datetime, UTC
from logging import getLogger
from pathlib import PurePath
from typing import Iterable, Any, IO, AnyStr, Iterator

import urllib3
from attr import dataclass
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from vihorki.infrastructure.ceph.common.filestorage import (
    IFile,
    IFileStorageAdapter,
    Diff,
    UniversalNamePath,
    get_diff,
    IFileStorageAdapterProvider,
)


__all__ = [
    'plugin_init',
    'CephIOFileNotFoundException',
    'CephAdapter',
    'CephAdapterProvider',
    'CephStorage',
    'CephStorageProvider',
    'BucketSnapshot',
]

_logger = getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _modified(key: dict) -> int:
    """Возвращает timestamp последней модификации файла"""
    return int(key['LastModified'].timestamp() * 1e6)


def get_last_modified_to_datetime(last_modified: datetime) -> datetime:
    return last_modified.replace(tzinfo=UTC)


def _get_files(objects: list[dict]) -> dict[str, int]:
    files = {}
    for obj in objects:
        modified = _modified(obj)
        files[obj['Key']] = modified
    return files


class CephIOFileNotFoundException(FileNotFoundError):
    pass


class CephIO(IO[AnyStr]):
    def __init__(self, client: Any, bucket: str, filename: str, mode: str):
        self.client = client
        self.bucket = bucket
        self.filename = filename
        self._mode = mode
        self.buffer = io.BytesIO() if 'b' in mode else io.StringIO()

    def __enter__(self) -> Any:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self.filename)
            data = response['Body'].read()
            if 'b' in self._mode:
                self.buffer.write(data)
            else:
                self.buffer.write(data.decode('utf-8'))
            self.buffer.seek(0)
            return self.buffer
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise CephIOFileNotFoundException(f'{self.filename} does not exist in {self.bucket}')

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        self.buffer.close()

    def close(self) -> None:
        pass

    def fileno(self) -> int:
        pass

    def flush(self) -> None:
        pass

    def isatty(self) -> bool:
        pass

    def read(self, n: int = ...) -> AnyStr:
        pass

    def readable(self) -> bool:
        pass

    def readline(self, limit: int = ...) -> AnyStr:
        pass

    def readlines(self, hint: int = ...) -> list[AnyStr]:
        pass

    def seek(self, offset: int, whence: int = ...) -> int:
        pass

    def seekable(self) -> bool:
        pass

    def tell(self) -> int:
        pass

    def truncate(self, size: int | None = ...) -> int:
        pass

    def writable(self) -> bool:
        pass

    def write(self, s: AnyStr) -> int:
        pass

    def writelines(self, lines: Iterable[AnyStr]) -> None:
        pass

    def __iter__(self) -> Iterator[AnyStr]:
        pass

    def __next__(self) -> AnyStr:
        pass


@dataclass(slots=True, frozen=True, eq=True, hash=True)
class CephFile(IFile):
    _path: PurePath
    _obj: dict
    _client: Any

    def get_path(self) -> PurePath:
        return self._path

    def get_last_modified(self) -> datetime:
        return get_last_modified_to_datetime(self._obj['LastModified'])

    def open(self, mode: str = 'r', *args, **kwargs) -> None:
        return CephIO(
            client=self._client,
            bucket=self._obj['Bucket'],
            filename=str(self._path),
            mode=mode,
        )

    def get_universal_name_path(self) -> UniversalNamePath:
        return UniversalNamePath(value=str(self._path))


class CephAdapter(IFileStorageAdapter):
    def __init__(self, client: Any, bucket: str, prefix: str = ''):
        self.client = client
        self.bucket = bucket
        self.prefix = prefix
        self._diff: Diff = Diff(not_modified=self._list_files())

    def _list_files(self) -> dict[str, int]:
        paginator = self.client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=self.bucket, Prefix=self.prefix)
        objects = []
        for page in page_iterator:
            objects.extend(page.get('Contents', []))
        return _get_files(objects)

    def open(self, filename: str, mode: str = 'r', *args, **kwargs) -> CephIO[Any]:
        return CephIO(client=self.client, bucket=self.bucket, filename=filename, mode=mode)

    def glob(self, pattern: str):
        paginator = self.client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=self.bucket, Prefix=self.prefix)
        for page in page_iterator:
            for obj in page.get('Contents', []):
                if fnmatch.fnmatch(obj['Key'], pattern):
                    yield CephFile(path=PurePath(obj['Key']), _obj=obj, _client=self.client)

    def path_exist(self, path: UniversalNamePath) -> bool:
        _path = os.path.join(self.prefix, path.value)
        try:
            self.client.head_object(Bucket=self.bucket, Key=_path)
            return True
        except ClientError:
            return False

    def refresh(self) -> Diff:
        old_files = self._diff.get_files()
        new_files = self._list_files()
        new_diff = get_diff(old_files=old_files, new_files=new_files)
        self._diff = new_diff
        return new_diff


class CephAdapterProvider(IFileStorageAdapterProvider):
    class Meta:
        name = 'ceph'

    def __init__(self, client: Any, bucket_name: str, prefix: str = ''):
        self.client = client
        self.bucket_name = bucket_name
        self.prefix = prefix

    def get_adapter(self) -> CephAdapter:
        return CephAdapter(client=self.client, bucket=self.bucket_name, prefix=self.prefix)


@dataclass(slots=True)
class BucketSnapshotDiff:
    new: set[str]
    removed: set[str]
    modified: set[str]


@dataclass(slots=True)
class BucketSnapshot:
    _snapshot: dict[str, str]

    def keys(self) -> set[str]:
        return set(self._snapshot.keys())

    def __str__(self) -> str:
        return f'BucketSnapshot({", ".join(self.keys())})'

    def __getitem__(self, key: str) -> str:
        return self._snapshot[key]

    def __sub__(self, other: 'BucketSnapshot') -> BucketSnapshotDiff:
        new = other.keys() - self.keys()
        removed = self.keys() - other.keys()
        modified = {key for key in self.keys() & other.keys() if other[key] != self[key]}
        return BucketSnapshotDiff(new=new, modified=modified, removed=removed)


def create_snapshot(client: Any, bucket: str, prefix: str = '') -> BucketSnapshot:
    paginator = client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
    snapshot = {}
    for page in page_iterator:
        for obj in page.get('Contents', []):
            snapshot[obj['Key']] = obj['ETag']
    return BucketSnapshot(snapshot)


async def create_snapshot_with_debounce(
    client: Any, bucket: str, prefix: str = '', refresh_debounce_period_seconds: float = 2.0
) -> BucketSnapshot:
    current_snapshot = create_snapshot(client, bucket, prefix)
    await asyncio.sleep(refresh_debounce_period_seconds)
    new_snapshot = create_snapshot(client, bucket, prefix)
    if _diff := current_snapshot - new_snapshot:
        current_snapshot = new_snapshot
    return new_snapshot


def get_or_create_bucket(client: Any, bucket_name: str) -> None:
    try:
        client.head_bucket(Bucket=bucket_name)
        _logger.info(f'Бакет {bucket_name} уже существует')
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            try:
                client.create_bucket(Bucket=bucket_name)
                _logger.info(f'Бакет {bucket_name} создан')
            except ClientError as create_error:
                raise RuntimeError(f'Ошибка создания бакета: {create_error}')
        else:
            raise


@dataclass(slots=True)
class CephStorage:
    bucket_name: str
    client: Any
    create_snapshot_with_debounce: float = 2.0
    _loop: AbstractEventLoop | None = None

    def __attrs_post_init__(self) -> None:
        get_or_create_bucket(self.client, self.bucket_name)

    @staticmethod
    async def _get_loop() -> AbstractEventLoop:
        return asyncio.get_event_loop()

    async def exists(self, filename: str) -> bool:
        loop = await self._get_loop()
        try:
            await loop.run_in_executor(
                None,
                partial(self.client.head_object, Bucket=self.bucket_name, Key=filename),
            )
            return True
        except ClientError:
            return False

    async def write_file(self, filename: str, content: AnyStr) -> None:
        loop = await self._get_loop()
        if isinstance(content, str):
            content = content.encode('utf-8')
        await loop.run_in_executor(
            None,
            partial(
                self.client.put_object,
                Bucket=self.bucket_name,
                Key=filename,
                Body=content,
            ),
        )

    async def remove_files_by_pattern(self, pattern: str) -> None:
        loop = await self._get_loop()
        paginator = self.client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=self.bucket_name)

        keys_to_remove = []
        for page in page_iterator:
            for obj in page.get('Contents', []):
                if fnmatch.fnmatch(obj['Key'], pattern):
                    keys_to_remove.append({'Key': obj['Key']})

        if keys_to_remove:
            await loop.run_in_executor(
                None,
                partial(
                    self.client.delete_objects,
                    Bucket=self.bucket_name,
                    Keys=keys_to_remove,
                ),
            )

    async def remove_file(self, filename: str) -> None:
        loop = await self._get_loop()
        await loop.run_in_executor(
            None,
            partial(self.client.delete_object, Bucket=self.bucket_name, Key=filename),
        )

    async def read_file(self, filename: str) -> str | None:
        loop = await self._get_loop()
        try:
            response = await loop.run_in_executor(
                None,
                partial(self.client.get_object, Bucket=self.bucket_name, Key=filename),
            )
            content = await self._loop.run_in_executor(None, response['Body'].read)
            return content.decode('utf-8')
        except ClientError:
            return None

    async def get_snapshot(self) -> BucketSnapshot:
        return await create_snapshot_with_debounce(
            self.client,
            self.bucket_name,
            refresh_debounce_period_seconds=self.create_snapshot_with_debounce,
        )

    async def list_all_filenames(self) -> list[str]:
        paginator = self.client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=self.bucket_name)
        filenames = []
        for page in page_iterator:
            for obj in page.get('Contents', []):
                filenames.append(obj['Key'])
        return filenames

    async def get_all_keys(self) -> list[dict]:
        paginator = self.client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=self.bucket_name)
        keys = []
        for page in page_iterator:
            keys.extend(page.get('Contents', []))
        return keys


class CephStorageProvider:
    def __init__(self, client: Any, bucket_name: str) -> None:
        self.client = client
        self.bucket_name = bucket_name

    def get_storage(self) -> CephStorage:
        return CephStorage(bucket_name=self.bucket_name, client=self.client)


def plugin_init(
    endpoint_url: str,
    is_secure: bool = False,
    access_key: str | None = None,
    secret_key: str | None = None,
) -> Any:
    cleaned_url = endpoint_url.strip().rstrip('/')
    try:
        client = boto3.client(
            's3',
            endpoint_url=cleaned_url,
            verify=False,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='ru-7',
            config=Config(s3={'addressing_style': 'path'}, retries={'max_attempts': 3}),
        )
        yield client
        yield type[CephAdapterProvider]
        yield type[CephStorageProvider]
    except Exception as e:
        raise RuntimeError(f'Ошибка инициализации клиента: {e}')
