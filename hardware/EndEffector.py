from abc import ABC, abstractmethod
from typing import Any


class EndEffectorException(Exception):
    pass


class EndEffector(ABC):
    """
    An abstract class defining the interface with an end effector.
    """

    @abstractmethod
    def __init__(self, port: str):
        """
        Parameters
        ----------
        port: str
            Serial port to connect to
        """

    @property
    @abstractmethod
    def valueRange(self) -> tuple[Any, Any]:
        """
        The range of values that the end effector can output.
        """

    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection with device

        Raises
        ------
        EndEffectorExcpetion
            If connection fails
        """

    @abstractmethod
    def disconect(self) -> None:
        """
        Disconnect from device

        Raises
        ------
        EndEffectorExcpetion
            If disconnection fails
        """

    @abstractmethod
    def enable(self) -> None:
        """
        Enable device

        Raises
        ------
        EndEffectorExcpetion
            If enabling fails
        """

    @abstractmethod
    def disable(self) -> None:
        """
        Disable device

        Raises
        ------
        EndEffectorExcpetion
            If disabling fails
        """

    @abstractmethod
    def move(self, target: Any) -> None:
        """
        Set target state

        Parameters
        ----------
        target: Any
            Target state

        Raises
        ------
        EndEffectorExcpetion
            If setting fails
        """
