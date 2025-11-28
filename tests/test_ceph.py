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


@pytest.fixture
def mock_client():
    """Фикстура для создания mock клиента S3"""
    return Mock()


@pytest.fixture
def ceph_storage(mock_client):
    """Фикстура для создания экземпляра CephStorage"""
    return CephStorage(bucket_name="test-bucket", client=mock_client)


@pytest.fixture
def ceph_adapter(mock_client):
    """Фикстура для создания экземпляра CephAdapter"""
    return CephAdapter(client=mock_client, bucket="test-bucket")


class TestCephFileOperations:
    """Тесты для операций с файлами в Ceph"""

    @pytest.mark.asyncio
    async def test_write_and_read_file(self, ceph_storage):
        """Тест загрузки и получения файла"""
        filename = "test_file.txt"
        content = "Hello, Ceph!"
        
        with patch.object(asyncio, 'get_event_loop') as mock_loop:
            executor_mock = AsyncMock()
            mock_loop.return_value.run_in_executor = executor_mock
            await ceph_storage.write_file(filename, content)
            executor_mock.assert_called()
            call_args = executor_mock.call_args_list
            put_object_called = False
            for call in call_args:
                args, kwargs = call
                if args and hasattr(args[1], 'func') and args[1].func.__name__ == 'put_object':
                    put_object_called = True
                    assert args[1].keywords['Bucket'] == "test-bucket"
                    assert args[1].keywords['Key'] == filename
                    assert args[1].keywords['Body'] == content.encode('utf-8')
                    break
            
            assert put_object_called, "put_object не был вызван"
            
            mock_response = {'Body': Mock()}
            mock_response['Body'].read.return_value = content.encode('utf-8')
            executor_mock.return_value = mock_response
            
            result = await ceph_storage.read_file(filename)
            
            assert result == content

    def test_file_open_context_manager(self, mock_client):
        """Тест получения файла через контекстный менеджер"""
        bucket = "test-bucket"
        filename = "test_file.txt"
        file_content = b"Test content for file"
        
        mock_response = {'Body': Mock()}
        mock_response['Body'].read.return_value = file_content
        mock_client.get_object.return_value = mock_response
        
        ceph_io = CephIO(client=mock_client, bucket=bucket, filename=filename, mode='rb')
        
        with ceph_io as file_obj:
            content = file_obj.read()
            assert content == file_content.decode('utf-8')
        mock_client.get_object.assert_called_once_with(Bucket=bucket, Key=filename)

    def test_file_not_found_exception(self, mock_client):
        """Тест исключения при отсутствии файла"""
        bucket = "test-bucket"
        filename = "nonexistent_file.txt"
        
        mock_client.get_object.side_effect = Mock(
            side_effect=Exception("ClientError")
        )
        mock_client.get_object.side_effect.__cause__ = Mock()
        mock_client.get_object.side_effect.__cause__.response = {
            'Error': {'Code': 'NoSuchKey'}
        }

        ceph_io = CephIO(client=mock_client, bucket=bucket, filename=filename, mode='r')
        
        with pytest.raises(CephIOFileNotFoundException):
            with ceph_io:
                pass 

    @pytest.mark.asyncio
    async def test_file_exists_check(self, ceph_storage):
        """Тест проверки существования файла"""
        filename = "existent_file.txt"
        
        with patch.object(asyncio, 'get_event_loop') as mock_loop:
            executor_mock = AsyncMock()
            mock_loop.return_value.run_in_executor = executor_mock
            
            result = await ceph_storage.exists(filename)
            
            executor_mock.assert_called()
            assert result is False 

    @pytest.mark.asyncio
    async def test_file_operations_integration(self, ceph_storage):
        """Интеграционный тест загрузки и получения файла"""
        filename = "integration_test.txt"
        original_content = "This is integration test content"
        
        with patch.object(asyncio, 'get_event_loop') as mock_loop:
            executor_mock = AsyncMock()
            mock_loop.return_value.run_in_executor = executor_mock

            def side_effect(executor, func_partial):
                if func_partial.func.__name__ == 'put_object':
                    return None  
                elif func_partial.func.__name__ == 'get_object':
                    mock_response = {'Body': Mock()}
                    mock_response['Body'].read.return_value = original_content.encode('utf-8')
                    return mock_response
                elif func_partial.func.__name__ == 'head_object':
                    return None
                return None
            
            executor_mock.side_effect = side_effect

            await ceph_storage.write_file(filename, original_content)

            retrieved_content = await ceph_storage.read_file(filename)
            
            assert retrieved_content == original_content

    def test_ceph_file_open_method(self, mock_client):
        """Тест метода открытия файла в CephFile"""
        filename = "test_ceph_file.txt"
        obj_data = {
            'Bucket': 'test-bucket',
            'Key': filename,
            'LastModified': Mock()
        }
        
        ceph_file = CephFile(
            _path=PurePath(filename),
            _obj=obj_data,
            _client=mock_client
        )
        
        ceph_io = ceph_file.open(mode='r')

        assert isinstance(ceph_io, CephIO)
        assert ceph_io.bucket == 'test-bucket'
        assert ceph_io.filename == filename
        assert ceph_io._mode == 'r'
