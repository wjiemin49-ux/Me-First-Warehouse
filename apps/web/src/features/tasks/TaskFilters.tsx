import type { TaskFiltersState } from "../../types";

type TaskFiltersProps = {
  value: TaskFiltersState;
  onChange: (value: TaskFiltersState) => void;
};

export function TaskFilters({ value, onChange }: TaskFiltersProps) {
  return (
    <section className="task-filters" aria-label="Task filters">
      <div>
        <label htmlFor="status-filter">Status filter</label>
        <select
          id="status-filter"
          value={value.status}
          onChange={(event) => onChange({ ...value, status: event.target.value as TaskFiltersState["status"] })}
        >
          <option value="all">All</option>
          <option value="todo">To do</option>
          <option value="in_progress">In progress</option>
          <option value="done">Done</option>
        </select>
      </div>

      <div>
        <label htmlFor="keyword-filter">Keyword</label>
        <input
          id="keyword-filter"
          value={value.keyword}
          onChange={(event) => onChange({ ...value, keyword: event.target.value })}
          placeholder="Search title or description"
        />
      </div>

      <div className="checkbox-field">
        <input
          id="overdue-filter"
          type="checkbox"
          checked={value.overdue}
          onChange={(event) => onChange({ ...value, overdue: event.target.checked })}
        />
        <label htmlFor="overdue-filter">Overdue only</label>
      </div>
    </section>
  );
}
