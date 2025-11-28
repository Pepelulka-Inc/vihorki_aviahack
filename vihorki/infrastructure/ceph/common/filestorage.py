from abc import ABCMeta, abstractmethod
from datetime import datetime
from pathlib import PurePath
from typing import IO, Any, Iterable

from attr import attrib, dataclass


__all__ = [
    'IFileStorageAdapter',
    'IFileStorageAdapterProvider',
    'Diff',
    'get_diff',
    'UniversalNamePath',
    'IFile',
]


@dataclass
class Diff:
    new: dict[str, int] = attrib(factory=dict)
    deleted: dict[str, int] = attrib(factory=dict)
    modified: dict[str, int] = attrib(factory=dict)
    not_modified: dict[str, int] = attrib(factory=dict)

    def get_files(self) -> dict[str, int]:
        return dict(self.not_modified, **self.modified, **self.new)


@dataclass(slots=True, frozen=True)
class UniversalNamePath:
    value: str


class IFile(metaclass=ABCMeta):
    """Интерфейс для работы с файлами"""

    @abstractmethod
    def get_path(self) -> PurePath:
        """Путь к файлу"""
        pass

    @abstractmethod
    def get_last_modified(self) -> datetime:
        """Время UTC последней модификации"""
        pass

    @abstractmethod
    def open(self, mode: str = 'r', *args: Any, **kwargs: Any):
        """Открывает файл на чтение"""
        pass


class IFileStorageAdapter(metaclass=ABCMeta):
    """
    Base class for file storage adapters which provides interface for IO operations
    """

    @abstractmethod
    def open(self, filename: str, mode: str = 'r', *args: Any, **kwargs: Any) -> IO[Any]:
        """Открывает файл на чтение"""
        pass

    @abstractmethod
    def glob(self, pattern: str) -> Iterable[IFile]:
        """Возвращает пути файлов попадающие под маску"""
        pass

    @abstractmethod
    def path_exist(self, path: UniversalNamePath) -> bool:
        """Проверяет, существует ли файл по указанному пути"""
        pass

    @abstractmethod
    def refresh(self) -> Diff:
        """Обновление хранилища, возвращает список измененных путей файлов"""
        pass


def get_diff(old_files: dict[str, int], new_files: dict[str, int]) -> Diff:
    copy_old_files = old_files.copy()
    diff = Diff()

    for new_file_iter, new_modified in new_files.items():
        if new_file_iter in old_files:
            old_modified = old_files[new_file_iter]

            if new_modified == old_modified:
                diff.not_modified[new_file_iter] = new_modified
            else:
                diff.modified[new_file_iter] = new_modified

            del copy_old_files[new_file_iter]
        else:
            diff.new[new_file_iter] = new_modified

    for old_file_iter, old_modified in copy_old_files.items():
        diff.deleted[old_file_iter] = old_modified

    return diff


class IFileStorageAdapterProvider(metaclass=ABCMeta):
    @abstractmethod
    def get_adapter(self) -> IFileStorageAdapter: ...
