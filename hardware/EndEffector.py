from abc import ABC, abstractmethod
from typing import Any


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
        """

    @abstractmethod
    def disconect(self) -> None:
        """
        Disconnect from device
        """

    @abstractmethod
    def enable(self) -> bool:
        """
        Enable device

        Returns
        -------
        bool
            Confirmation
        """

    @abstractmethod
    def disable(self) -> bool:
        """
        Disable device

        Returns
        -------
        bool
            Confirmation
        """

    @abstractmethod
    def move(self, target: Any) -> bool:
        """
        Set target state

        Parameters
        ----------
        target: Any
            Target state

        Returns
        -------
        bool
            Confirmation
        """
