import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../../api/client';

/**
 * Create/edit share one form; passing `project` switches it to edit mode and
 * PATCHes instead of POSTing, so the two flows can't drift apart visually.
 */
function ProjectFormModal({ project, onClose, onSaved }) {
  const isEdit = Boolean(project);
  const [name, setName] = useState(project?.name ?? '');
  const [description, setDescription] = useState(project?.description ?? '');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const body = { name, description: description || null };
      const { data } = isEdit
        ? await apiClient.patch(`/projects/${project.id}`, body)
        : await apiClient.post('/projects', body);
      onSaved(data);
    } catch (err) {
      setError(err.response?.data?.detail || `Could not ${isEdit ? 'update' : 'create'} project.`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{isEdit ? 'Edit Project' : 'New Project'}</h2>
        {error && <div className="error-banner">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="project-name">Name</label>
            <input
              id="project-name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="form-field">
            <label htmlFor="project-description">Description</label>
            <textarea
              id="project-description"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Saving...' : isEdit ? 'Save Changes' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/**
 * Deleting a project cascades to its sites and their metrics, so the count is
 * spelled out in the prompt rather than asking for a bare yes/no.
 */
function ConfirmDeleteModal({ projects, onCancel, onConfirm, deleting, error }) {
  const many = projects.length > 1;
  const siteTotal = projects.reduce((sum, p) => sum + (p.site_count ?? 0), 0);

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Delete {many ? `${projects.length} projects` : 'project'}?</h2>
        {error && <div className="error-banner">{error}</div>}
        <p>
          {many ? (
            <>
              You&apos;re about to delete <strong>{projects.length} projects</strong>.
            </>
          ) : (
            <>
              You&apos;re about to delete <strong>{projects[0]?.name}</strong>.
            </>
          )}{' '}
          {siteTotal > 0 && (
            <>
              This also permanently removes <strong>{siteTotal}</strong> site
              {siteTotal === 1 ? '' : 's'} and all of their recorded metrics.
            </>
          )}{' '}
          This cannot be undone.
        </p>
        {many && (
          <ul className="confirm-list">
            {projects.map((p) => (
              <li key={p.id}>{p.name}</li>
            ))}
          </ul>
        )}
        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="btn btn-danger" onClick={onConfirm} disabled={deleting}>
            {deleting
              ? 'Deleting...'
              : `Delete ${many ? `${projects.length} projects` : 'project'}`}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ProjectDashboard() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const [selectedIds, setSelectedIds] = useState([]);

  const loadProjects = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await apiClient.get('/projects');
      setProjects(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load projects.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreated = (project) => {
    setShowCreate(false);
    setProjects((prev) => [project, ...prev]);
  };

  const handleUpdated = (updated) => {
    setEditing(null);
    setProjects((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  };

  const toggleSelected = (id) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const allSelected = projects.length > 0 && selectedIds.length === projects.length;
  const toggleSelectAll = () => {
    setSelectedIds(allSelected ? [] : projects.map((p) => p.id));
  };

  const selectedProjects = projects.filter((p) => selectedIds.includes(p.id));

  const confirmDelete = async () => {
    setDeleting(true);
    setDeleteError('');
    const targets = pendingDelete;
    const ids = targets.map((p) => p.id);
    try {
      if (ids.length === 1) {
        await apiClient.delete(`/projects/${ids[0]}`);
      } else {
        await apiClient.post('/projects/bulk-delete', { ids });
      }
      setProjects((prev) => prev.filter((p) => !ids.includes(p.id)));
      setSelectedIds((prev) => prev.filter((id) => !ids.includes(id)));
      setPendingDelete(null);
    } catch (err) {
      setDeleteError(err.response?.data?.detail || 'Could not delete. Please try again.');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Projects</h1>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          + New Project
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {!loading && projects.length > 0 && (
        <div className="selection-bar">
          <label className="select-all">
            <input
              type="checkbox"
              checked={allSelected}
              onChange={toggleSelectAll}
              aria-label="Select all projects"
            />
            <span>
              {selectedIds.length > 0
                ? `${selectedIds.length} selected`
                : `Select all (${projects.length})`}
            </span>
          </label>
          {selectedIds.length > 0 && (
            <div className="selection-actions">
              <button className="btn btn-secondary" onClick={() => setSelectedIds([])}>
                Clear
              </button>
              <button className="btn btn-danger" onClick={() => setPendingDelete(selectedProjects)}>
                Delete selected ({selectedIds.length})
              </button>
            </div>
          )}
        </div>
      )}

      {loading ? (
        <p>Loading projects...</p>
      ) : projects.length === 0 ? (
        <div className="empty-state">
          <p>No projects yet. Create your first project to start mapping sites.</p>
        </div>
      ) : (
        <div className="card-grid">
          {projects.map((project) => {
            const siteCount = project.site_count ?? project.sites?.length ?? 0;
            const isSelected = selectedIds.includes(project.id);
            return (
              <div key={project.id} className={`project-card${isSelected ? ' is-selected' : ''}`}>
                <input
                  type="checkbox"
                  className="card-select"
                  checked={isSelected}
                  onChange={() => toggleSelected(project.id)}
                  aria-label={`Select ${project.name}`}
                />
                <Link to={`/projects/${project.id}`} className="card-body">
                  <h3>{project.name}</h3>
                  {project.description && <p>{project.description}</p>}
                  <span className="meta">
                    {siteCount} site{siteCount === 1 ? '' : 's'}
                  </span>
                </Link>
                <div className="card-actions">
                  <button
                    className="btn btn-link"
                    onClick={() => setEditing(project)}
                    aria-label={`Edit ${project.name}`}
                  >
                    Edit
                  </button>
                  <button
                    className="btn btn-link btn-link-danger"
                    onClick={() => setPendingDelete([project])}
                    aria-label={`Delete ${project.name}`}
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showCreate && (
        <ProjectFormModal onClose={() => setShowCreate(false)} onSaved={handleCreated} />
      )}

      {editing && (
        <ProjectFormModal
          project={editing}
          onClose={() => setEditing(null)}
          onSaved={handleUpdated}
        />
      )}

      {pendingDelete && (
        <ConfirmDeleteModal
          projects={pendingDelete}
          deleting={deleting}
          error={deleteError}
          onCancel={() => {
            setPendingDelete(null);
            setDeleteError('');
          }}
          onConfirm={confirmDelete}
        />
      )}
    </div>
  );
}
