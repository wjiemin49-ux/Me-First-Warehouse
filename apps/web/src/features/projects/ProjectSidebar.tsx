import { FormEvent, useState } from "react";
import type { Project } from "../../types";

type ProjectSidebarProps = {
  projects: Project[];
  selectedProjectId: string | null;
  pending?: boolean;
  onSelect: (projectId: string) => void;
  onCreate: (name: string) => Promise<void>;
  onRename: (projectId: string, name: string) => Promise<void>;
  onDelete: (projectId: string) => Promise<void>;
};

export function ProjectSidebar({
  projects,
  selectedProjectId,
  pending = false,
  onSelect,
  onCreate,
  onRename,
  onDelete
}: ProjectSidebarProps) {
  const [projectName, setProjectName] = useState("");
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [renamingValue, setRenamingValue] = useState("");

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = projectName.trim();
    if (!trimmed) {
      return;
    }

    await onCreate(trimmed);
    setProjectName("");
  };

  return (
    <aside className="project-sidebar" aria-label="Projects">
      <h2>Projects</h2>
      <form onSubmit={handleCreate} className="project-create-form">
        <label htmlFor="project-name">Project name</label>
        <div className="row">
          <input
            id="project-name"
            value={projectName}
            onChange={(event) => setProjectName(event.target.value)}
            placeholder="New project"
            required
          />
          <button type="submit" disabled={pending}>
            Add project
          </button>
        </div>
      </form>

      <ul className="project-list">
        {projects.map((project) => {
          const isSelected = selectedProjectId === project.id;
          const isEditing = editingProjectId === project.id;

          return (
            <li key={project.id} className={isSelected ? "selected" : undefined}>
              {isEditing ? (
                <form
                  className="row"
                  onSubmit={async (event) => {
                    event.preventDefault();
                    const nextName = renamingValue.trim();
                    if (!nextName) {
                      return;
                    }
                    await onRename(project.id, nextName);
                    setEditingProjectId(null);
                    setRenamingValue("");
                  }}
                >
                  <label className="sr-only" htmlFor={`rename-project-${project.id}`}>
                    Rename project
                  </label>
                  <input
                    id={`rename-project-${project.id}`}
                    aria-label="Rename project"
                    value={renamingValue}
                    onChange={(event) => setRenamingValue(event.target.value)}
                    required
                  />
                  <button type="submit">Save project name</button>
                </form>
              ) : (
                <>
                  <button
                    type="button"
                    className="project-select"
                    aria-current={isSelected ? "page" : undefined}
                    onClick={() => onSelect(project.id)}
                  >
                    {project.name}
                  </button>
                  <div className="row">
                    <button
                      type="button"
                      onClick={() => {
                        setEditingProjectId(project.id);
                        setRenamingValue(project.name);
                      }}
                    >
                      Rename
                    </button>
                    <button type="button" onClick={() => onDelete(project.id)}>
                      Delete
                    </button>
                  </div>
                </>
              )}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
