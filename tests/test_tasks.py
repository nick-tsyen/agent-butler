from __future__ import annotations

from agent_butler.types.task import Task


class TestTaskModel:
    def test_create_task(self) -> None:
        task = Task(
            id="task-1",
            subject="Implement feature X",
            description="Add the new feature",
            status="pending",
        )
        assert task.id == "task-1"
        assert task.subject == "Implement feature X"
        assert task.status == "pending"
        assert task.blocks == []
        assert task.blocked_by == []

    def test_task_status_values(self) -> None:
        for status in ("pending", "in_progress", "completed"):
            task = Task(id="t", subject="s", description="d", status=status)
            assert task.status == status

    def test_task_with_blocks(self) -> None:
        task = Task(
            id="task-2",
            subject="Blocked task",
            description="This is blocked",
            status="pending",
            blocks=["task-3"],
            blocked_by=["task-1"],
        )
        assert "task-3" in task.blocks
        assert "task-1" in task.blocked_by

    def test_task_optional_fields(self) -> None:
        task = Task(
            id="task-4",
            subject="Simple",
            description="Simple task",
            status="pending",
            active_form="Working on it",
            owner="agent",
            metadata={"key": "value"},
        )
        assert task.active_form == "Working on it"
        assert task.owner == "agent"
        assert task.metadata == {"key": "value"}

    def test_task_serialization(self) -> None:
        task = Task(
            id="task-5",
            subject="Serialize me",
            description="Test serialization",
            status="completed",
        )
        data = task.model_dump()
        assert data["id"] == "task-5"
        assert data["status"] == "completed"

        restored = Task(**data)
        assert restored.id == task.id
        assert restored.status == task.status
