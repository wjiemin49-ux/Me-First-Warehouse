import { FormEvent, useState } from "react";

type TaskFormPayload = {
  title: string;
  description: string;
  dueDate: string | null;
};

type TaskFormProps = {
  disabled?: boolean;
  onSubmit: (payload: TaskFormPayload) => Promise<void>;
};

export function TaskForm({ disabled = false, onSubmit }: TaskFormProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      return;
    }

    await onSubmit({
      title: trimmedTitle,
      description: description.trim(),
      dueDate: dueDate || null
    });
    setTitle("");
    setDescription("");
    setDueDate("");
  };

  return (
    <form className="task-form" onSubmit={handleSubmit}>
      <label htmlFor="task-title">Task title</label>
      <input
        id="task-title"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        required
        placeholder="What needs to be done?"
      />

      <label htmlFor="task-description">Description</label>
      <textarea
        id="task-description"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        rows={2}
      />

      <label htmlFor="task-due-date">Due date</label>
      <input
        id="task-due-date"
        type="date"
        value={dueDate}
        onChange={(event) => setDueDate(event.target.value)}
      />

      <button type="submit" disabled={disabled}>
        Add task
      </button>
    </form>
  );
}
