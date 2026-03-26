import { FormEvent, useMemo, useState } from "react";
import type { Task, TaskStatus } from "../../types";

type TaskBoardProps = {
  tasks: Task[];
  onStatusChange: (taskId: string, status: TaskStatus) => Promise<void>;
  onDeleteTask: (taskId: string) => Promise<void>;
  onUpdateTask: (
    taskId: string,
    payload: Partial<{ title: string; description: string; dueDate: string | null }>
  ) => Promise<void>;
};

const STATUS_LABELS: Record<TaskStatus, string> = {
  todo: "To Do",
  in_progress: "In Progress",
  done: "Done"
};

function getNextStatus(status: TaskStatus): { label: string; next: TaskStatus } {
  if (status === "todo") {
    return { label: "Start", next: "in_progress" };
  }
  if (status === "in_progress") {
    return { label: "Mark done", next: "done" };
  }
  return { label: "Reopen", next: "todo" };
}

function dueDateLabel(dueDate: string | null) {
  if (!dueDate) {
    return "No due date";
  }
  const date = new Date(dueDate);
  if (Number.isNaN(date.getTime())) {
    return "Invalid due date";
  }
  return `Due ${date.toISOString().slice(0, 10)}`;
}

type EditState = {
  taskId: string;
  title: string;
  description: string;
  dueDate: string;
};

export function TaskBoard({ tasks, onStatusChange, onDeleteTask, onUpdateTask }: TaskBoardProps) {
  const [editing, setEditing] = useState<EditState | null>(null);

  const columns = useMemo(() => {
    return {
      todo: tasks.filter((task) => task.status === "todo"),
      in_progress: tasks.filter((task) => task.status === "in_progress"),
      done: tasks.filter((task) => task.status === "done")
    };
  }, [tasks]);

  const renderCard = (task: Task) => {
    if (editing?.taskId === task.id) {
      return (
        <form
          className="task-edit-form"
          onSubmit={async (event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const title = editing.title.trim();
            if (!title) {
              return;
            }
            await onUpdateTask(task.id, {
              title,
              description: editing.description.trim(),
              dueDate: editing.dueDate || null
            });
            setEditing(null);
          }}
        >
          <label htmlFor={`edit-title-${task.id}`}>Edit title for {task.title}</label>
          <input
            id={`edit-title-${task.id}`}
            value={editing.title}
            onChange={(event) => setEditing({ ...editing, title: event.target.value })}
          />

          <label htmlFor={`edit-description-${task.id}`}>Edit description</label>
          <textarea
            id={`edit-description-${task.id}`}
            value={editing.description}
            onChange={(event) => setEditing({ ...editing, description: event.target.value })}
            rows={2}
          />

          <label htmlFor={`edit-due-${task.id}`}>Edit due date</label>
          <input
            id={`edit-due-${task.id}`}
            type="date"
            value={editing.dueDate}
            onChange={(event) => setEditing({ ...editing, dueDate: event.target.value })}
          />

          <div className="row">
            <button type="submit">Save task</button>
            <button type="button" onClick={() => setEditing(null)}>
              Cancel
            </button>
          </div>
        </form>
      );
    }

    const transition = getNextStatus(task.status);
    return (
      <>
        <h4>{task.title}</h4>
        {task.description ? <p>{task.description}</p> : null}
        <p className="task-due">{dueDateLabel(task.dueDate)}</p>
        <div className="row">
          <button type="button" onClick={() => onStatusChange(task.id, transition.next)}>
            {transition.label}
          </button>
          <button
            type="button"
            onClick={() =>
              setEditing({
                taskId: task.id,
                title: task.title,
                description: task.description ?? "",
                dueDate: task.dueDate ? task.dueDate.slice(0, 10) : ""
              })
            }
          >
            Edit
          </button>
          <button type="button" onClick={() => onDeleteTask(task.id)}>
            Delete
          </button>
        </div>
      </>
    );
  };

  return (
    <section className="task-board" aria-label="Task board">
      {(Object.keys(STATUS_LABELS) as TaskStatus[]).map((status) => (
        <article className="board-column" key={status} data-testid={`column-${status}`}>
          <h3>{STATUS_LABELS[status]}</h3>
          <ul>
            {columns[status].map((task) => (
              <li key={task.id}>
                <article className="task-card">{renderCard(task)}</article>
              </li>
            ))}
          </ul>
        </article>
      ))}
    </section>
  );
}
