import asyncio
from pathlib import PurePath

from unittest.mock import Mock, patch, AsyncMock
import pytest

from vihorki.infrastructure.ceph.s3 import (
    CephStorage,
    CephAdapter,
    CephFile,
    CephIO,
    CephIOFileNotFoundException
)

def test_tmp():
    assert 1 == 1
